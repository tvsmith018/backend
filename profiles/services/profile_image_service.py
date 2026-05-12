from __future__ import annotations

import cloudinary.uploader
from django.db import transaction

from profiles.models import ProfileImage, UserProfileStats
from users.models import Users


class ProfileImageService:
    @staticmethod
    def _ordered_user_images(user_id: int) -> list[ProfileImage]:
        return list(
            ProfileImage.objects.filter(user_id=user_id).order_by("-is_featured", "sort_order", "created_at")
        )

    @staticmethod
    def _sync_uploaded_count(user_id: int) -> int:
        uploaded_count = ProfileImage.objects.filter(user_id=user_id).count()
        UserProfileStats.objects.update_or_create(
            user_id=user_id,
            defaults={"uploaded_images_count": uploaded_count},
        )
        return uploaded_count

    @staticmethod
    def _promote_image_to_avatar(image: ProfileImage) -> str | None:
        if not image.image:
            return None

        avatar_public_id = getattr(image.image, "public_id", None) or str(image.image)
        if not avatar_public_id:
            return None

        user = Users.objects.select_for_update().get(pk=image.user_id)
        user.avatar = avatar_public_id
        user.save(update_fields=["avatar"])
        return image.image.url

    @staticmethod
    def _reorder_after_featured(user_id: int, featured_image_id: int | None) -> list[ProfileImage]:
        images = ProfileImageService._ordered_user_images(user_id)
        featured: ProfileImage | None = None
        others: list[ProfileImage] = []
        for image in images:
            if featured_image_id is not None and image.id == featured_image_id:
                featured = image
                continue
            image.is_featured = False
            others.append(image)

        if featured is None and others:
            featured = others.pop(0)
        if featured is not None:
            featured.is_featured = True
            featured.visibility = ProfileImage.Visibility.PUBLIC

        # Keep non-featured images in creation order (newest first).
        others.sort(key=lambda image: (image.created_at, image.id), reverse=True)

        ordered: list[ProfileImage] = []
        if featured is not None:
            featured.sort_order = 0
            ordered.append(featured)

        for index, image in enumerate(others, start=1 if featured is not None else 0):
            image.sort_order = index
            ordered.append(image)

        if ordered:
            ProfileImage.objects.bulk_update(
                ordered,
                ["is_featured", "visibility", "sort_order", "updated_at"],
            )
        return ordered

    @staticmethod
    @transaction.atomic
    def upload_photo(
        *,
        user_id: int,
        image_data: str,
        caption: str = "",
        visibility: str = ProfileImage.Visibility.PUBLIC,
        force_featured: bool = False,
    ) -> dict:
        user = Users.objects.get(pk=user_id)
        ordered_images = ProfileImageService._ordered_user_images(user_id)
        has_featured = any(image.is_featured for image in ordered_images)
        has_avatar = bool(user.avatar)
        should_auto_feature = (not has_featured) and (not has_avatar) and len(ordered_images) == 0
        should_feature = bool(force_featured) or should_auto_feature

        uploaded = cloudinary.uploader.upload(
            image_data,
            folder=f"profile_gallery/{user_id}",
            resource_type="image",
        )
        image_public_id = uploaded.get("public_id")
        if not image_public_id:
            raise ValueError("Unable to store profile photo.")

        profile_image = ProfileImage.objects.create(
            user=user,
            image=image_public_id,
            caption=(caption or "").strip(),
            visibility=ProfileImage.Visibility.PUBLIC if should_feature else visibility,
            sort_order=0,
            is_featured=False,
        )

        featured_id = None
        if should_feature:
            featured_id = profile_image.id
        else:
            existing_featured = next((image for image in ordered_images if image.is_featured), None)
            featured_id = existing_featured.id if existing_featured else None

        ordered = ProfileImageService._reorder_after_featured(user_id, featured_id)
        featured = next((item for item in ordered if item.is_featured), None)
        avatar_url = ProfileImageService._promote_image_to_avatar(featured) if featured else None

        images_count = ProfileImageService._sync_uploaded_count(user_id)
        profile_image.refresh_from_db()
        return {
            "image": profile_image,
            "images_count": images_count,
            "avatar_url": avatar_url,
            "images": ordered,
        }

    @staticmethod
    @transaction.atomic
    def set_featured_photo(*, user_id: int, image_id: int) -> dict:
        image = ProfileImage.objects.select_for_update().select_related("user").get(
            pk=image_id,
            user_id=user_id,
        )

        # Enforce a single featured image deterministically:
        # 1) clear all other featured flags
        # 2) set selected image featured/public
        ProfileImage.objects.filter(user_id=user_id).exclude(pk=image.id).update(
            is_featured=False,
        )
        ProfileImage.objects.filter(pk=image.id, user_id=user_id).update(
            is_featured=True,
            visibility=ProfileImage.Visibility.PUBLIC,
        )

        # Keep the selected image first, then order the rest newest-first.
        remaining = list(
            ProfileImage.objects.filter(user_id=user_id).exclude(pk=image.id).order_by("-created_at", "-id")
        )
        for index, item in enumerate(remaining, start=1):
            item.sort_order = index
        if remaining:
            ProfileImage.objects.bulk_update(remaining, ["sort_order", "updated_at"])

        ProfileImage.objects.filter(pk=image.id, user_id=user_id).update(sort_order=0)
        ordered = ProfileImageService._ordered_user_images(user_id)
        featured = next((item for item in ordered if item.is_featured), None) or image
        avatar_url = ProfileImageService._promote_image_to_avatar(featured)
        images_count = ProfileImageService._sync_uploaded_count(user_id)
        return {
            "image": featured,
            "images_count": images_count,
            "avatar_url": avatar_url,
            "images": ordered,
        }

    @staticmethod
    @transaction.atomic
    def toggle_visibility(*, user_id: int, image_id: int) -> dict:
        image = ProfileImage.objects.get(pk=image_id, user_id=user_id)
        if image.is_featured:
            image.visibility = ProfileImage.Visibility.PUBLIC
            image.save(update_fields=["visibility", "updated_at"])
            images_count = ProfileImageService._sync_uploaded_count(user_id)
            return {
                "image": image,
                "images_count": images_count,
            }
        image.visibility = (
            ProfileImage.Visibility.PRIVATE
            if image.visibility == ProfileImage.Visibility.PUBLIC
            else ProfileImage.Visibility.PUBLIC
        )
        image.save(update_fields=["visibility", "updated_at"])
        images_count = ProfileImageService._sync_uploaded_count(user_id)
        return {
            "image": image,
            "images_count": images_count,
        }

    @staticmethod
    @transaction.atomic
    def delete_photo(*, user_id: int, image_id: int) -> dict:
        image = ProfileImage.objects.get(pk=image_id, user_id=user_id)
        was_featured = image.is_featured
        deleted_id = image.id
        image.delete()

        avatar_url = None
        ordered_images: list[ProfileImage] = []
        if was_featured:
            remaining = list(ProfileImage.objects.filter(user_id=user_id).order_by("-created_at"))
            if remaining:
                next_featured = remaining[0]
                next_featured.is_featured = True
                next_featured.visibility = ProfileImage.Visibility.PUBLIC
                next_featured.sort_order = 0
                others = [item for item in remaining[1:]]
                for index, item in enumerate(others, start=1):
                    item.is_featured = False
                    item.sort_order = index
                ProfileImage.objects.bulk_update(
                    [next_featured, *others],
                    ["is_featured", "visibility", "sort_order", "updated_at"],
                )
                avatar_url = ProfileImageService._promote_image_to_avatar(next_featured)
                ordered_images = ProfileImageService._ordered_user_images(user_id)
            else:
                Users.objects.filter(pk=user_id).update(avatar=None)
        else:
            ordered_images = ProfileImageService._reorder_after_featured(user_id, None)

        if was_featured and not ordered_images:
            ordered_images = ProfileImageService._ordered_user_images(user_id)

        images_count = ProfileImageService._sync_uploaded_count(user_id)
        return {
            "deleted_id": deleted_id,
            "images_count": images_count,
            "avatar_url": avatar_url,
            "images": ordered_images,
        }

    @staticmethod
    @transaction.atomic
    def clear_avatar(*, user_id: int) -> dict:
        Users.objects.filter(pk=user_id).update(avatar=None)
        images = list(ProfileImage.objects.filter(user_id=user_id).order_by("sort_order", "created_at"))
        for index, image in enumerate(images):
            image.is_featured = False
            image.sort_order = index
        if images:
            ProfileImage.objects.bulk_update(images, ["is_featured", "sort_order", "updated_at"])

        images_count = ProfileImageService._sync_uploaded_count(user_id)
        return {
            "images_count": images_count,
            "avatar_url": None,
        }
