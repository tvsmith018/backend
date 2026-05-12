from django.contrib import admin

from .models import CommentLike, CommentReply, Comments


class HasLikesFilter(admin.SimpleListFilter):
    title = "has likes"
    parameter_name = "has_likes"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Yes"),
            ("no", "No"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "yes":
            return queryset.filter(like_count__gt=0)
        if value == "no":
            return queryset.filter(like_count=0)
        return queryset


class HasRepliesFilter(admin.SimpleListFilter):
    title = "has replies"
    parameter_name = "has_replies"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Yes"),
            ("no", "No"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "yes":
            return queryset.filter(reply_count__gt=0)
        if value == "no":
            return queryset.filter(reply_count=0)
        return queryset


class CommentLikeInline(admin.TabularInline):
    model = CommentLike
    extra = 0
    fields = ("user", "created")
    readonly_fields = ("created",)
    autocomplete_fields = ("user",)
    show_change_link = True


class CommentReplyInline(admin.TabularInline):
    model = CommentReply
    extra = 0
    fields = ("user", "body", "status", "created")
    readonly_fields = ("created", "updated")
    autocomplete_fields = ("user",)
    show_change_link = True


@admin.register(Comments)
class CommentsAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "article",
        "user",
        "parent",
        "root",
        "reply_count",
        "like_count",
        "active",
        "created",
    )
    search_fields = ("article__title", "user__email", "user__firstname", "user__lastname", "body")
    list_filter = ("active", "created", "updated", HasLikesFilter, HasRepliesFilter)
    readonly_fields = ("created", "updated")
    autocomplete_fields = ("article", "user", "parent", "root")
    inlines = [CommentLikeInline, CommentReplyInline]
    date_hierarchy = "created"


@admin.register(CommentLike)
class CommentLikeAdmin(admin.ModelAdmin):
    list_display = ("id", "comment", "user", "created")
    search_fields = ("comment__body", "user__email", "user__firstname", "user__lastname")
    list_filter = ("created",)
    readonly_fields = ("created",)
    autocomplete_fields = ("comment", "user")


@admin.register(CommentReply)
class CommentReplyAdmin(admin.ModelAdmin):
    list_display = ("id", "comment", "user", "status", "created")
    search_fields = ("comment__body", "user__email", "user__firstname", "user__lastname", "body")
    list_filter = ("status", "created")
    readonly_fields = ("created", "updated")
    autocomplete_fields = ("comment", "user")
