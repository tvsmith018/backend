from django.db import models
from django.db.models import F, Q

from users.models import Users


class MessageThread(models.Model):
    class ThreadType(models.TextChoices):
        DIRECT = "direct", "Direct"
        GROUP = "group", "Group"
        SYSTEM = "system", "System"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"
        CLOSED = "closed", "Closed"

    thread_type = models.CharField(
        max_length=20,
        choices=ThreadType.choices,
        default=ThreadType.DIRECT,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    subject = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        Users,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_message_threads",
    )
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_message_at", "-updated_at", "-created_at"]

    def __str__(self):
        return f"{self.thread_type} thread {self.id}"


class MessageThreadParticipant(models.Model):
    class Role(models.TextChoices):
        MEMBER = "member", "Member"
        ADMIN = "admin", "Admin"
        OWNER = "owner", "Owner"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        LEFT = "left", "Left"
        REMOVED = "removed", "Removed"
        BLOCKED = "blocked", "Blocked"

    thread = models.ForeignKey(
        MessageThread,
        on_delete=models.CASCADE,
        related_name="participants",
    )
    user = models.ForeignKey(
        Users,
        on_delete=models.CASCADE,
        related_name="message_participations",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    last_read_message = models.ForeignKey(
        "Message",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    last_read_at = models.DateTimeField(null=True, blank=True)
    muted_until = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["thread", "user"],
                name="unique_message_thread_participant",
            )
        ]

    def __str__(self):
        return f"{self.user} in thread {self.thread_id}"


class Message(models.Model):
    class MessageType(models.TextChoices):
        TEXT = "text", "Text"
        IMAGE = "image", "Image"
        FILE = "file", "File"
        SYSTEM = "system", "System"

    class Status(models.TextChoices):
        SENT = "sent", "Sent"
        EDITED = "edited", "Edited"
        DELETED = "deleted", "Deleted"

    thread = models.ForeignKey(
        MessageThread,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        Users,
        on_delete=models.CASCADE,
        related_name="sent_messages",
    )
    body = models.TextField(blank=True)
    message_type = models.CharField(
        max_length=20,
        choices=MessageType.choices,
        default=MessageType.TEXT,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SENT,
        db_index=True,
    )
    reply_to = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="direct_replies",
    )
    root_message = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="thread_replies",
    )
    reply_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["thread", "created_at"]),
            models.Index(fields=["sender", "created_at"]),
            models.Index(fields=["reply_to", "created_at"]),
            models.Index(fields=["root_message", "created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~Q(reply_to=F("id")),
                name="message_cannot_reply_to_self",
            ),
        ]

    def __str__(self):
        return f"Message {self.id} in thread {self.thread_id}"


class MessageAttachment(models.Model):
    class AttachmentType(models.TextChoices):
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"
        AUDIO = "audio", "Audio"
        FILE = "file", "File"

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    attachment_type = models.CharField(
        max_length=20,
        choices=AttachmentType.choices,
        db_index=True,
    )
    file_url = models.URLField()
    file_name = models.CharField(max_length=255, blank=True)
    mime_type = models.CharField(max_length=100, blank=True)
    file_size_bytes = models.PositiveBigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.attachment_type} attachment for message {self.message_id}"


class MessageReceipt(models.Model):
    class ReceiptType(models.TextChoices):
        DELIVERED = "delivered", "Delivered"
        READ = "read", "Read"

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="receipts",
    )
    user = models.ForeignKey(
        Users,
        on_delete=models.CASCADE,
        related_name="message_receipts",
    )
    receipt_type = models.CharField(
        max_length=20,
        choices=ReceiptType.choices,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["message", "user", "receipt_type"],
                name="unique_message_receipt_per_type",
            )
        ]

    def __str__(self):
        return f"{self.receipt_type} receipt for message {self.message_id}"


class UserMessageBlock(models.Model):
    blocker = models.ForeignKey(
        Users,
        on_delete=models.CASCADE,
        related_name="blocked_users",
    )
    blocked = models.ForeignKey(
        Users,
        on_delete=models.CASCADE,
        related_name="blocked_by_users",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["blocker", "blocked"],
                name="unique_user_message_block",
            ),
            models.CheckConstraint(
                condition=~Q(blocker=F("blocked")),
                name="prevent_self_message_block",
            ),
        ]

    def __str__(self):
        return f"{self.blocker} blocked {self.blocked}"
