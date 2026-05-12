from django.db import models
from django.db.models import F, Q

from articles.models import Articles
from users.models import Users

# Create your models here.
class Comments(models.Model):
    article = models.ForeignKey(Articles, on_delete=models.CASCADE, related_name='comments', null=True, blank=True)
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="comments")
    body = models.TextField()
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="replies",
        null=True,
        blank=True,
    )
    root = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="thread_comments",
        null=True,
        blank=True,
    )
    reply_count = models.PositiveIntegerField(default=0)
    like_count = models.PositiveIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    updated = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True) 

    class Meta:
        ordering = ['created']
        indexes = [
            models.Index(fields=["article", "created"]),
            models.Index(fields=["user", "created"]),
            models.Index(fields=["parent", "created"]),
            models.Index(fields=["root", "created"]),
            models.Index(fields=["active", "created"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~Q(parent=F("id")),
                name="comment_cannot_reply_to_self",
            ),
        ]

    def __str__(self):
        return f'Comment by {self.user} on {self.article}'


class CommentLike(models.Model):
    comment = models.ForeignKey(
        Comments,
        on_delete=models.CASCADE,
        related_name="likes",
    )
    user = models.ForeignKey(
        Users,
        on_delete=models.CASCADE,
        related_name="comment_likes",
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]
        constraints = [
            models.UniqueConstraint(
                fields=["comment", "user"],
                name="unique_comment_like_per_user",
            )
        ]
        indexes = [
            models.Index(fields=["comment", "created"]),
            models.Index(fields=["user", "created"]),
        ]

    def __str__(self):
        return f"{self.user} liked comment {self.comment_id}"


class CommentReply(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        HIDDEN = "hidden", "Hidden"
        REMOVED = "removed", "Removed"

    comment = models.ForeignKey(
        Comments,
        on_delete=models.CASCADE,
        related_name="comment_replies",
    )
    user = models.ForeignKey(
        Users,
        on_delete=models.CASCADE,
        related_name="comment_replies",
    )
    body = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created"]
        indexes = [
            models.Index(fields=["comment", "created"]),
            models.Index(fields=["user", "created"]),
            models.Index(fields=["status", "created"]),
        ]

    def __str__(self):
        return f"{self.user} reply on comment {self.comment_id}"
