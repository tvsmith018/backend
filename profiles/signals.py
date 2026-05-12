from django.apps import apps
from django.db.models.signals import post_delete, post_save

from profiles.services.profile_stats_sync import sync_profile_stats_for_user
from profiles.services.profile_image_service import ProfileImageService


def register_signals():
    """Connect after app registry is ready so sender matches AUTH_USER_MODEL."""
    User = apps.get_model("users", "Users")
    from .models import (
        ProfileFollow,
        ProfileImage,
        ProfilePost,
        ProfilePostLike,
        ProfilePostReply,
        ProfilePostShare,
        UserProfileSettings,
        UserProfileStats,
        UserRatingSummary,
    )
    Rating = apps.get_model("articles", "Rating")
    ArticleView = apps.get_model("articles", "ArticleView")
    Comments = apps.get_model("comments", "Comments")
    CommentReply = apps.get_model("comments", "CommentReply")

    def ensure_user_profile_rows(sender, instance, created, **kwargs):
        if not created:
            return
        UserProfileSettings.objects.get_or_create(user=instance)
        UserProfileStats.objects.get_or_create(user=instance)
        UserRatingSummary.objects.get_or_create(user=instance)

    def resolve_avatar_public_id(user) -> str:
        avatar = getattr(user, "avatar", None)
        if not avatar:
            return ""
        if isinstance(avatar, str):
            return avatar.strip()
        return (getattr(avatar, "public_id", None) or str(avatar) or "").strip()

    def resolve_profile_image_public_id(image) -> str:
        if not image:
            return ""
        if isinstance(image, str):
            return image.strip()
        return (getattr(image, "public_id", None) or str(image) or "").strip()

    def sync_user_avatar_to_profile_image(sender, instance, created, update_fields=None, **kwargs):
        if not instance or not getattr(instance, "pk", None):
            return
        if not created and update_fields and "avatar" not in set(update_fields):
            return

        avatar_public_id = resolve_avatar_public_id(instance)
        if not avatar_public_id:
            return

        target = ProfileImage.objects.filter(user_id=instance.pk, image=avatar_public_id).first()
        if target is None:
            try:
                target = ProfileImage.objects.create(
                    user_id=instance.pk,
                    image=avatar_public_id,
                    caption="Profile avatar",
                    visibility=ProfileImage.Visibility.PUBLIC,
                    sort_order=0,
                    is_featured=True,
                )
            except Exception:
                # Keep signup/profile save resilient if avatar mirroring fails.
                return

        ordered = ProfileImageService._reorder_after_featured(instance.pk, target.id)
        featured = next((item for item in ordered if item.is_featured), target)
        featured_public_id = resolve_profile_image_public_id(featured.image)
        if featured_public_id and featured_public_id != avatar_public_id:
            User.objects.filter(pk=instance.pk).update(avatar=featured_public_id)
        ProfileImageService._sync_uploaded_count(instance.pk)

    post_save.connect(
        ensure_user_profile_rows,
        sender=User,
        dispatch_uid="profiles.ensure_user_profile_rows",
    )
    post_save.connect(
        sync_user_avatar_to_profile_image,
        sender=User,
        dispatch_uid="profiles.sync_user_avatar_to_profile_image",
    )

    def sync_profile_post_like_count(post_id: int):
        total = ProfilePostLike.objects.filter(post_id=post_id).count()
        ProfilePost.objects.filter(pk=post_id).update(likes_count=total)

    def sync_profile_post_share_count(post_id: int):
        total = ProfilePostShare.objects.filter(post_id=post_id).count()
        ProfilePost.objects.filter(pk=post_id).update(share_count=total)

    def sync_profile_post_reply_count(post_id: int):
        total = ProfilePostReply.objects.filter(post_id=post_id).count()
        ProfilePost.objects.filter(pk=post_id).update(replies_count=total)

    def update_like_count_on_like_save(sender, instance, **kwargs):
        sync_profile_post_like_count(instance.post_id)

    def update_like_count_on_like_delete(sender, instance, **kwargs):
        sync_profile_post_like_count(instance.post_id)

    def update_share_count_on_share_save(sender, instance, **kwargs):
        sync_profile_post_share_count(instance.post_id)

    def update_share_count_on_share_delete(sender, instance, **kwargs):
        sync_profile_post_share_count(instance.post_id)

    def update_reply_count_on_reply_save(sender, instance, **kwargs):
        sync_profile_post_reply_count(instance.post_id)

    def update_reply_count_on_reply_delete(sender, instance, **kwargs):
        sync_profile_post_reply_count(instance.post_id)

    def sync_profile_stats_for_actor_user(user_id: int | None):
        if not user_id:
            return
        if not User.objects.filter(pk=user_id).exists():
            return
        sync_profile_stats_for_user(int(user_id), touch_last_activity=True)

    def sync_profile_stats_on_post_save(sender, instance, **kwargs):
        sync_profile_stats_for_actor_user(getattr(instance, "user_id", None))

    def sync_profile_stats_on_post_delete(sender, instance, **kwargs):
        sync_profile_stats_for_actor_user(getattr(instance, "user_id", None))

    def sync_profile_stats_on_post_like_save(sender, instance, **kwargs):
        sync_profile_stats_for_actor_user(getattr(instance, "user_id", None))

    def sync_profile_stats_on_post_like_delete(sender, instance, **kwargs):
        sync_profile_stats_for_actor_user(getattr(instance, "user_id", None))

    def sync_profile_stats_on_post_share_save(sender, instance, **kwargs):
        sync_profile_stats_for_actor_user(getattr(instance, "user_id", None))

    def sync_profile_stats_on_post_share_delete(sender, instance, **kwargs):
        sync_profile_stats_for_actor_user(getattr(instance, "user_id", None))

    def sync_profile_stats_on_follow_save(sender, instance, **kwargs):
        sync_profile_stats_for_actor_user(getattr(instance, "follower_id", None))
        sync_profile_stats_for_actor_user(getattr(instance, "following_id", None))

    def sync_profile_stats_on_follow_delete(sender, instance, **kwargs):
        sync_profile_stats_for_actor_user(getattr(instance, "follower_id", None))
        sync_profile_stats_for_actor_user(getattr(instance, "following_id", None))

    def sync_profile_stats_on_article_view_save(sender, instance, **kwargs):
        # Ignore anonymous view events for profile stats.
        sync_profile_stats_for_actor_user(getattr(instance, "user_id", None))

    def sync_profile_stats_on_rating_save(sender, instance, **kwargs):
        sync_profile_stats_for_actor_user(getattr(instance, "user_id", None))

    def sync_profile_stats_on_rating_delete(sender, instance, **kwargs):
        sync_profile_stats_for_actor_user(getattr(instance, "user_id", None))

    def sync_profile_stats_on_profile_image_save(sender, instance, **kwargs):
        sync_profile_stats_for_actor_user(getattr(instance, "user_id", None))

    def sync_profile_stats_on_profile_image_delete(sender, instance, **kwargs):
        sync_profile_stats_for_actor_user(getattr(instance, "user_id", None))

    def sync_profile_stats_on_comment_save(sender, instance, **kwargs):
        sync_profile_stats_for_actor_user(getattr(instance, "user_id", None))

    def sync_profile_stats_on_comment_delete(sender, instance, **kwargs):
        sync_profile_stats_for_actor_user(getattr(instance, "user_id", None))

    def sync_profile_stats_on_comment_reply_save(sender, instance, **kwargs):
        sync_profile_stats_for_actor_user(getattr(instance, "user_id", None))

    def sync_profile_stats_on_comment_reply_delete(sender, instance, **kwargs):
        sync_profile_stats_for_actor_user(getattr(instance, "user_id", None))

    def resolve_profile_image_public_id(image_field) -> str:
        if not image_field:
            return ""
        if isinstance(image_field, str):
            return image_field.strip()
        return (getattr(image_field, "public_id", None) or str(image_field) or "").strip()

    def sync_user_avatar_from_featured_profile_image(user_id: int | None):
        if not user_id:
            return
        featured = (
            ProfileImage.objects.filter(user_id=user_id, is_featured=True)
            .order_by("sort_order", "created_at", "id")
            .first()
        )
        if not featured:
            User.objects.filter(pk=user_id).update(avatar=None)
            return

        # Featured image must always be public.
        if featured.visibility != ProfileImage.Visibility.PUBLIC:
            ProfileImage.objects.filter(pk=featured.pk).update(visibility=ProfileImage.Visibility.PUBLIC)

        featured_public_id = resolve_profile_image_public_id(featured.image)
        if not featured_public_id:
            User.objects.filter(pk=user_id).update(avatar=None)
            return

        User.objects.filter(pk=user_id).exclude(avatar=featured_public_id).update(avatar=featured_public_id)

    def sync_avatar_on_profile_image_save(sender, instance, **kwargs):
        sync_user_avatar_from_featured_profile_image(getattr(instance, "user_id", None))

    def sync_avatar_on_profile_image_delete(sender, instance, **kwargs):
        sync_user_avatar_from_featured_profile_image(getattr(instance, "user_id", None))

    post_save.connect(
        update_like_count_on_like_save,
        sender=ProfilePostLike,
        dispatch_uid="profiles.sync_profile_post_likes_on_save",
    )
    post_delete.connect(
        update_like_count_on_like_delete,
        sender=ProfilePostLike,
        dispatch_uid="profiles.sync_profile_post_likes_on_delete",
    )
    post_save.connect(
        update_share_count_on_share_save,
        sender=ProfilePostShare,
        dispatch_uid="profiles.sync_profile_post_shares_on_save",
    )
    post_delete.connect(
        update_share_count_on_share_delete,
        sender=ProfilePostShare,
        dispatch_uid="profiles.sync_profile_post_shares_on_delete",
    )
    post_save.connect(
        update_reply_count_on_reply_save,
        sender=ProfilePostReply,
        dispatch_uid="profiles.sync_profile_post_replies_on_save",
    )
    post_delete.connect(
        update_reply_count_on_reply_delete,
        sender=ProfilePostReply,
        dispatch_uid="profiles.sync_profile_post_replies_on_delete",
    )
    post_save.connect(
        sync_profile_stats_on_post_save,
        sender=ProfilePost,
        dispatch_uid="profiles.sync_user_profile_stats_on_profile_post_save",
    )
    post_delete.connect(
        sync_profile_stats_on_post_delete,
        sender=ProfilePost,
        dispatch_uid="profiles.sync_user_profile_stats_on_profile_post_delete",
    )
    post_save.connect(
        sync_profile_stats_on_post_like_save,
        sender=ProfilePostLike,
        dispatch_uid="profiles.sync_user_profile_stats_on_profile_post_like_save",
    )
    post_delete.connect(
        sync_profile_stats_on_post_like_delete,
        sender=ProfilePostLike,
        dispatch_uid="profiles.sync_user_profile_stats_on_profile_post_like_delete",
    )
    post_save.connect(
        sync_profile_stats_on_post_share_save,
        sender=ProfilePostShare,
        dispatch_uid="profiles.sync_user_profile_stats_on_profile_post_share_save",
    )
    post_delete.connect(
        sync_profile_stats_on_post_share_delete,
        sender=ProfilePostShare,
        dispatch_uid="profiles.sync_user_profile_stats_on_profile_post_share_delete",
    )
    post_save.connect(
        sync_profile_stats_on_follow_save,
        sender=ProfileFollow,
        dispatch_uid="profiles.sync_user_profile_stats_on_profile_follow_save",
    )
    post_delete.connect(
        sync_profile_stats_on_follow_delete,
        sender=ProfileFollow,
        dispatch_uid="profiles.sync_user_profile_stats_on_profile_follow_delete",
    )
    post_save.connect(
        sync_profile_stats_on_article_view_save,
        sender=ArticleView,
        dispatch_uid="profiles.sync_user_profile_stats_on_article_view_save",
    )
    post_save.connect(
        sync_profile_stats_on_rating_save,
        sender=Rating,
        dispatch_uid="profiles.sync_user_profile_stats_on_rating_save",
    )
    post_delete.connect(
        sync_profile_stats_on_rating_delete,
        sender=Rating,
        dispatch_uid="profiles.sync_user_profile_stats_on_rating_delete",
    )
    post_save.connect(
        sync_profile_stats_on_profile_image_save,
        sender=ProfileImage,
        dispatch_uid="profiles.sync_user_profile_stats_on_profile_image_save",
    )
    post_delete.connect(
        sync_profile_stats_on_profile_image_delete,
        sender=ProfileImage,
        dispatch_uid="profiles.sync_user_profile_stats_on_profile_image_delete",
    )
    post_save.connect(
        sync_profile_stats_on_comment_save,
        sender=Comments,
        dispatch_uid="profiles.sync_user_profile_stats_on_comment_save",
    )
    post_delete.connect(
        sync_profile_stats_on_comment_delete,
        sender=Comments,
        dispatch_uid="profiles.sync_user_profile_stats_on_comment_delete",
    )
    post_save.connect(
        sync_profile_stats_on_comment_reply_save,
        sender=CommentReply,
        dispatch_uid="profiles.sync_user_profile_stats_on_comment_reply_save",
    )
    post_delete.connect(
        sync_profile_stats_on_comment_reply_delete,
        sender=CommentReply,
        dispatch_uid="profiles.sync_user_profile_stats_on_comment_reply_delete",
    )
    post_save.connect(
        sync_avatar_on_profile_image_save,
        sender=ProfileImage,
        dispatch_uid="profiles.sync_user_avatar_on_profile_image_save",
    )
    post_delete.connect(
        sync_avatar_on_profile_image_delete,
        sender=ProfileImage,
        dispatch_uid="profiles.sync_user_avatar_on_profile_image_delete",
    )
