from django.contrib import admin

from .models import (
    Message,
    MessageAttachment,
    MessageReceipt,
    MessageThread,
    MessageThreadParticipant,
    UserMessageBlock,
)


class MessageThreadParticipantInline(admin.TabularInline):
    model = MessageThreadParticipant
    extra = 0
    fields = ("user", "role", "status", "last_read_at", "archived_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("user", "last_read_message")
    show_change_link = True


class MessageAttachmentInline(admin.TabularInline):
    model = MessageAttachment
    extra = 0
    fields = ("attachment_type", "file_name", "mime_type", "file_size_bytes", "created_at")
    readonly_fields = ("created_at",)
    show_change_link = True


class MessageReceiptInline(admin.TabularInline):
    model = MessageReceipt
    extra = 0
    fields = ("user", "receipt_type", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("user",)
    show_change_link = True


@admin.register(MessageThread)
class MessageThreadAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "thread_type",
        "status",
        "subject",
        "created_by",
        "last_message_at",
        "updated_at",
    )
    search_fields = (
        "subject",
        "created_by__email",
        "participants__user__email",
    )
    list_filter = ("thread_type", "status", "created_at", "updated_at")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("created_by",)
    inlines = [MessageThreadParticipantInline]
    date_hierarchy = "last_message_at"


@admin.register(MessageThreadParticipant)
class MessageThreadParticipantAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "thread",
        "user",
        "role",
        "status",
        "last_read_at",
        "archived_at",
    )
    search_fields = ("thread__subject", "user__email", "user__firstname", "user__lastname")
    list_filter = ("role", "status", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("thread", "user", "last_read_message")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "thread",
        "sender",
        "message_type",
        "status",
        "reply_to",
        "reply_count",
        "created_at",
    )
    search_fields = (
        "thread__subject",
        "sender__email",
        "sender__firstname",
        "sender__lastname",
        "body",
    )
    list_filter = ("message_type", "status", "created_at", "edited_at", "deleted_at")
    readonly_fields = ("created_at", "updated_at", "edited_at", "deleted_at")
    autocomplete_fields = ("thread", "sender", "reply_to", "root_message")
    inlines = [MessageAttachmentInline, MessageReceiptInline]
    date_hierarchy = "created_at"


@admin.register(MessageAttachment)
class MessageAttachmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "message",
        "attachment_type",
        "file_name",
        "mime_type",
        "file_size_bytes",
        "created_at",
    )
    search_fields = ("message__body", "file_name", "mime_type")
    list_filter = ("attachment_type", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("message",)


@admin.register(MessageReceipt)
class MessageReceiptAdmin(admin.ModelAdmin):
    list_display = ("id", "message", "user", "receipt_type", "created_at")
    search_fields = ("message__body", "user__email")
    list_filter = ("receipt_type", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("message", "user")


@admin.register(UserMessageBlock)
class UserMessageBlockAdmin(admin.ModelAdmin):
    list_display = ("id", "blocker", "blocked", "created_at")
    search_fields = (
        "blocker__email",
        "blocker__firstname",
        "blocker__lastname",
        "blocked__email",
        "blocked__firstname",
        "blocked__lastname",
    )
    list_filter = ("created_at",)
    readonly_fields = ("created_at",)
    autocomplete_fields = ("blocker", "blocked")
