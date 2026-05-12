import json

from channels.db import database_sync_to_async
from graphql_relay import from_global_id
from rest_framework import serializers

from common.consumers.base import BaseCommentConsumer
from profiles.models import ProfileImage
from profiles.services.profile_image_service import ProfileImageService
from users.models import Users
from users.services.auth_service import AuthService


class ProfilePhotoUploadSerializer(serializers.Serializer):
    action = serializers.CharField(required=False, default="upload_photo")
    user_id = serializers.CharField(max_length=2000)
    image_data = serializers.CharField()
    caption = serializers.CharField(max_length=255, required=False, allow_blank=True)
    visibility = serializers.ChoiceField(
        choices=[ProfileImage.Visibility.PUBLIC, ProfileImage.Visibility.PRIVATE],
        required=False,
    )
    is_featured = serializers.BooleanField(required=False, default=False)


class ProfilePhotoImageActionSerializer(serializers.Serializer):
    action = serializers.CharField()
    user_id = serializers.CharField(max_length=2000)
    image_id = serializers.CharField(max_length=2000)

    def validate_image_id(self, value):
        raw = (value or "").strip()
        if raw.isdigit():
            return int(raw)
        try:
            _, decoded = from_global_id(raw)
            return int(decoded)
        except Exception as exc:
            raise serializers.ValidationError("Invalid image id.") from exc


class ProfilePhotoConsumer(BaseCommentConsumer):
    group_name = "profile_photos_feed"

    async def connect(self):
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    def _serialize_photo(self, image: ProfileImage):
        return {
            "id": str(image.id),
            "userId": str(image.user_id),
            "caption": image.caption,
            "visibility": image.visibility,
            "sortOrder": image.sort_order,
            "isFeatured": image.is_featured,
            "imageUrl": image.image.url if image.image else None,
            "createdAt": image.created_at.isoformat(),
            "updatedAt": image.updated_at.isoformat(),
        }

    async def _broadcast_event(self, payload: dict):
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "profile.photo.message",
                "payload": payload,
            },
        )

    async def receive(self, text_data):
        payload = json.loads(text_data)
        action = payload.get("action", "upload_photo")

        if action == "set_featured_photo":
            await self._handle_set_featured(payload)
            return
        if action == "toggle_photo_visibility":
            await self._handle_toggle_visibility(payload)
            return
        if action == "delete_photo":
            await self._handle_delete(payload)
            return
        if action == "clear_avatar":
            await self._handle_clear_avatar(payload)
            return
        await self._handle_upload(payload)

    async def _handle_upload(self, payload):
        serializer = ProfilePhotoUploadSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        user_id = int(serializer.validated_data["user_id"])
        await database_sync_to_async(AuthService.get_user)(user_id)
        result = await database_sync_to_async(ProfileImageService.upload_photo)(
            user_id=user_id,
            image_data=serializer.validated_data["image_data"],
            caption=serializer.validated_data.get("caption", ""),
            visibility=serializer.validated_data.get("visibility", ProfileImage.Visibility.PUBLIC),
            force_featured=serializer.validated_data.get("is_featured", False),
        )
        image = result["image"]
        user = await database_sync_to_async(Users.objects.filter(pk=user_id).first)()
        avatar_url = result.get("avatar_url")
        if avatar_url is None:
            avatar_url = user.avatar_url if user else None
        await self._broadcast_event(
            {
                "eventType": "photo_created",
                "userId": str(user_id),
                "image": self._serialize_photo(image),
                "images": [self._serialize_photo(item) for item in result.get("images", [])],
                "imagesCount": result["images_count"],
                "avatarUrl": avatar_url,
            }
        )

    async def _handle_set_featured(self, payload):
        serializer = ProfilePhotoImageActionSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        user_id = int(serializer.validated_data["user_id"])
        image_id = int(serializer.validated_data["image_id"])
        await database_sync_to_async(AuthService.get_user)(user_id)
        result = await database_sync_to_async(ProfileImageService.set_featured_photo)(
            user_id=user_id,
            image_id=image_id,
        )
        image = result["image"]
        user = await database_sync_to_async(Users.objects.filter(pk=user_id).first)()
        avatar_url = result.get("avatar_url")
        if avatar_url is None:
            avatar_url = user.avatar_url if user else None
        await self._broadcast_event(
            {
                "eventType": "photo_featured_changed",
                "userId": str(user_id),
                "image": self._serialize_photo(image),
                "images": [self._serialize_photo(item) for item in result.get("images", [])],
                "imagesCount": result["images_count"],
                "avatarUrl": avatar_url,
            }
        )

    async def _handle_toggle_visibility(self, payload):
        serializer = ProfilePhotoImageActionSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        user_id = int(serializer.validated_data["user_id"])
        image_id = int(serializer.validated_data["image_id"])
        await database_sync_to_async(AuthService.get_user)(user_id)
        result = await database_sync_to_async(ProfileImageService.toggle_visibility)(
            user_id=user_id,
            image_id=image_id,
        )
        image = result["image"]
        await self._broadcast_event(
            {
                "eventType": "photo_visibility_changed",
                "userId": str(user_id),
                "image": self._serialize_photo(image),
                "imagesCount": result["images_count"],
            }
        )

    async def _handle_delete(self, payload):
        serializer = ProfilePhotoImageActionSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        user_id = int(serializer.validated_data["user_id"])
        image_id = int(serializer.validated_data["image_id"])
        await database_sync_to_async(AuthService.get_user)(user_id)
        result = await database_sync_to_async(ProfileImageService.delete_photo)(
            user_id=user_id,
            image_id=image_id,
        )
        user = await database_sync_to_async(Users.objects.filter(pk=user_id).first)()
        avatar_url = result.get("avatar_url")
        if avatar_url is None:
            avatar_url = user.avatar_url if user else None
        await self._broadcast_event(
            {
                "eventType": "photo_deleted",
                "userId": str(user_id),
                "imageId": str(result["deleted_id"]),
                "images": [self._serialize_photo(item) for item in result.get("images", [])],
                "imagesCount": result["images_count"],
                "avatarUrl": avatar_url,
            }
        )

    async def _handle_clear_avatar(self, payload):
        raw_user_id = str(payload.get("user_id") or "").strip()
        if not raw_user_id.isdigit():
            return
        user_id = int(raw_user_id)
        await database_sync_to_async(AuthService.get_user)(user_id)
        result = await database_sync_to_async(ProfileImageService.clear_avatar)(user_id=user_id)
        await self._broadcast_event(
            {
                "eventType": "photo_featured_changed",
                "userId": str(user_id),
                "avatarUrl": result.get("avatar_url"),
                "imagesCount": result["images_count"],
            }
        )

    async def profile_photo_message(self, event):
        await self.send_json(event["payload"])
