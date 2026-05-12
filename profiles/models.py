from django.db import models
from django.core.exceptions import ValidationError
from django.utils.text import slugify
import cloudinary.uploader

from articles.models import Articles
from users.models import Users
from cloudinary.models import CloudinaryField


class UserProfileSettings(models.Model):
    user = models.OneToOneField(
        Users,
        on_delete=models.CASCADE,
        related_name="profile_settings",
    )
    profile_is_public = models.BooleanField(default=True)
    allow_messages = models.BooleanField(default=True)
    show_activity_feed = models.BooleanField(default=True)
    show_watch_history = models.BooleanField(default=True)
    show_ratings = models.BooleanField(default=True)
    show_uploaded_images = models.BooleanField(default=True)
    receive_notifications = models.BooleanField(default=True)
    receive_marketing_notifications = models.BooleanField(default=False)
    disabled_at = models.DateTimeField(null=True, blank=True)
    delete_requested_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile settings for {self.user.email}"


class UserProfileStats(models.Model):
    user = models.OneToOneField(
        Users,
        on_delete=models.CASCADE,
        related_name="profile_stats",
    )
    posts_count = models.PositiveIntegerField(default=0)
    followers_count = models.PositiveIntegerField(default=0)
    following_count = models.PositiveIntegerField(default=0)
    watched_videos_count = models.PositiveIntegerField(default=0)
    rated_articles_count = models.PositiveIntegerField(default=0)
    uploaded_images_count = models.PositiveIntegerField(default=0)
    comments_written_count = models.PositiveIntegerField(default=0)
    post_likes_given_count = models.PositiveIntegerField(default=0)
    post_shares_given_count = models.PositiveIntegerField(default=0)
    article_likes_given_count = models.PositiveIntegerField(default=0)
    average_rating_given = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    weekly_activity_series = models.JSONField(default=list, blank=True)
    earnings_total_cents = models.BigIntegerField(default=0)
    last_activity_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile stats for {self.user.email}"


class ProfileFollow(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        MUTED = "muted", "Muted"
        BLOCKED = "blocked", "Blocked"

    follower = models.ForeignKey(
        Users,
        on_delete=models.CASCADE,
        related_name="following_relationships",
    )
    following = models.ForeignKey(
        Users,
        on_delete=models.CASCADE,
        related_name="follower_relationships",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["follower", "following"],
                name="unique_profile_follow_relationship",
            ),
            models.CheckConstraint(
                condition=~models.Q(follower=models.F("following")),
                name="prevent_self_follow_relationship",
            ),
        ]
        indexes = [
            models.Index(fields=["following", "status", "created_at"]),
            models.Index(fields=["follower", "status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.follower} follows {self.following}"


class ProfilePost(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        HIDDEN = "hidden", "Hidden"
        REMOVED = "removed", "Removed"

    user = models.ForeignKey(
        Users,
        on_delete=models.CASCADE,
        related_name="profile_posts",
    )
    article = models.ForeignKey(
        Articles,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profile_posts",
    )
    body = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    likes_count = models.PositiveIntegerField(default=0)
    share_count = models.PositiveIntegerField(default=0)
    replies_count = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    post_image = CloudinaryField(
        "post_image",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def _post_image_folder(self) -> str:
        first = slugify(self.user.firstname or "", allow_unicode=False).replace("-", "_")
        last = slugify(self.user.lastname or "", allow_unicode=False).replace("-", "_")
        user_post = f"{first}_{last}_post".strip("_") or "user_post"
        post_id = self.pk if self.pk is not None else "pending"
        return f"post/{user_post}/{post_id}/image"

    def upload_post_image(self, image_file):
        """
        Uploads post image to Cloudinary under:
        post/<firstname_lastname_post>/<post_id>/image
        """
        if not image_file:
            return None

        if self.pk is None:
            self.save()

        uploaded = cloudinary.uploader.upload(
            image_file,
            folder=self._post_image_folder(),
            public_id="image",
            overwrite=True,
            resource_type="image",
        )

        self.post_image = uploaded.get("public_id")
        self.save(update_fields=["post_image", "updated_at"])
        return uploaded

    def __str__(self):
        return f"{self.user} profile post {self.id}"


class ProfilePostLike(models.Model):
    post = models.ForeignKey(
        ProfilePost,
        on_delete=models.CASCADE,
        related_name="likes",
    )
    user = models.ForeignKey(
        Users,
        on_delete=models.CASCADE,
        related_name="profile_post_likes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["post", "user"],
                name="unique_profile_post_like_per_user",
            )
        ]
        indexes = [
            models.Index(fields=["post", "created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user} liked profile post {self.post_id}"


class ProfilePostShare(models.Model):
    post = models.ForeignKey(
        ProfilePost,
        on_delete=models.CASCADE,
        related_name="shares",
    )
    user = models.ForeignKey(
        Users,
        on_delete=models.CASCADE,
        related_name="profile_post_shares",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["post", "user"],
                name="unique_profile_post_share_per_user",
            )
        ]
        indexes = [
            models.Index(fields=["post", "created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user} shared profile post {self.post_id}"


class ProfilePostReply(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        HIDDEN = "hidden", "Hidden"
        REMOVED = "removed", "Removed"

    post = models.ForeignKey(
        ProfilePost,
        on_delete=models.CASCADE,
        related_name="replies",
    )
    user = models.ForeignKey(
        Users,
        on_delete=models.CASCADE,
        related_name="profile_post_replies",
    )
    body = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user} reply on post {self.post_id}"


class ProfileImage(models.Model):
    MAX_IMAGES_PER_USER = 10

    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        PRIVATE = "private", "Private"

    user = models.ForeignKey(
        Users,
        on_delete=models.CASCADE,
        related_name="profile_images",
    )
    image = CloudinaryField("profile_image", folder="profile_gallery")
    caption = models.CharField(max_length=255, blank=True)
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
        db_index=True,
    )
    sort_order = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_featured", "sort_order", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_featured=True),
                name="unique_featured_profile_image_per_user",
            )
        ]
        indexes = [
            models.Index(fields=["user", "sort_order", "created_at"]),
            models.Index(fields=["user", "is_featured"]),
        ]

    def clean(self):
        super().clean()
        if not self.user_id:
            return

        existing = ProfileImage.objects.filter(user_id=self.user_id)
        if self.pk:
            existing = existing.exclude(pk=self.pk)

        if existing.count() >= self.MAX_IMAGES_PER_USER:
            raise ValidationError(
                {"user": f"A user can only have up to {self.MAX_IMAGES_PER_USER} profile images."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} image {self.id}"


class VideoWatchHistory(models.Model):
    user = models.ForeignKey(
        Users,
        on_delete=models.CASCADE,
        related_name="video_watch_history",
    )
    article = models.ForeignKey(
        Articles,
        on_delete=models.CASCADE,
        related_name="watch_history_entries",
    )
    watched_seconds = models.PositiveIntegerField(default=0)
    completed = models.BooleanField(default=False)
    last_watched_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "article"],
                name="unique_user_video_watch_history",
            )
        ]

    def __str__(self):
        return f"{self.user} watched {self.article}"


class UserRatingSummary(models.Model):
    user = models.OneToOneField(
        Users,
        on_delete=models.CASCADE,
        related_name="rating_summary",
    )
    ratings_count = models.PositiveIntegerField(default=0)
    average_rating_given = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    highest_rating_count = models.PositiveIntegerField(default=0)
    lowest_rating_count = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Rating summary for {self.user.email}"


class SavedArticle(models.Model):
    user = models.ForeignKey(
        Users,
        on_delete=models.CASCADE,
        related_name="saved_articles",
    )
    article = models.ForeignKey(
        Articles,
        on_delete=models.CASCADE,
        related_name="saved_by_users",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "article"],
                name="unique_saved_article_per_user",
            )
        ]

    def __str__(self):
        return f"{self.user} saved {self.article}"
