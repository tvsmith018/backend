from django.contrib import admin

from .models import (
    ProfileFollow,
    ProfileImage,
    ProfilePost,
    ProfilePostLike,
    ProfilePostShare,
    ProfilePostReply,
    SavedArticle,
    UserProfileSettings,
    UserProfileStats,
    UserRatingSummary,
    VideoWatchHistory,
)


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
            return queryset.filter(likes_count__gt=0)
        if value == "no":
            return queryset.filter(likes_count=0)
        return queryset


class HasSharesFilter(admin.SimpleListFilter):
    title = "has shares"
    parameter_name = "has_shares"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Yes"),
            ("no", "No"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "yes":
            return queryset.filter(share_count__gt=0)
        if value == "no":
            return queryset.filter(share_count=0)
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
            return queryset.filter(replies_count__gt=0)
        if value == "no":
            return queryset.filter(replies_count=0)
        return queryset


class ProfilePostReplyInline(admin.TabularInline):
    model = ProfilePostReply
    extra = 0
    fields = ("user", "body", "status", "created_at")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("user",)
    show_change_link = True


class ProfilePostLikeInline(admin.TabularInline):
    model = ProfilePostLike
    extra = 0
    fields = ("user", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("user",)
    show_change_link = True


class ProfilePostShareInline(admin.TabularInline):
    model = ProfilePostShare
    extra = 0
    fields = ("user", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("user",)
    show_change_link = True


@admin.register(UserProfileSettings)
class UserProfileSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "profile_is_public",
        "allow_messages",
        "show_activity_feed",
        "show_watch_history",
        "show_ratings",
        "disabled_at",
        "delete_requested_at",
        "updated_at",
    )
    search_fields = ("user__email", "user__firstname", "user__lastname")
    list_filter = (
        "profile_is_public",
        "allow_messages",
        "show_activity_feed",
        "show_watch_history",
        "show_ratings",
        "show_uploaded_images",
        "receive_notifications",
        "receive_marketing_notifications",
    )
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("user",)


@admin.register(UserProfileStats)
class UserProfileStatsAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "posts_count",
        "followers_count",
        "following_count",
        "watched_videos_count",
        "rated_articles_count",
        "uploaded_images_count",
        "average_rating_given",
        "earnings_total_cents",
        "last_activity_at",
    )
    search_fields = ("user__email", "user__firstname", "user__lastname")
    readonly_fields = ("updated_at",)
    autocomplete_fields = ("user",)


@admin.register(ProfilePost)
class ProfilePostAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "article",
        "status",
        "likes_count",
        "share_count",
        "replies_count",
        "created_at",
    )
    search_fields = (
        "user__email",
        "user__firstname",
        "user__lastname",
        "article__title",
        "body",
    )
    list_filter = (
        "status",
        "created_at",
        HasLikesFilter,
        HasSharesFilter,
        HasRepliesFilter,
    )
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("user", "article")
    inlines = [ProfilePostReplyInline, ProfilePostLikeInline, ProfilePostShareInline]
    date_hierarchy = "created_at"


@admin.register(ProfilePostLike)
class ProfilePostLikeAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "user", "created_at")
    search_fields = (
        "user__email",
        "user__firstname",
        "user__lastname",
        "post__body",
    )
    list_filter = ("created_at", "post__status")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("post", "user")
    date_hierarchy = "created_at"


@admin.register(ProfilePostShare)
class ProfilePostShareAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "user", "created_at")
    search_fields = (
        "user__email",
        "user__firstname",
        "user__lastname",
        "post__body",
    )
    list_filter = ("created_at", "post__status")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("post", "user")
    date_hierarchy = "created_at"


@admin.register(ProfilePostReply)
class ProfilePostReplyAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "user", "status", "created_at")
    search_fields = ("user__email", "post__body", "body")
    list_filter = ("status", "created_at", "post__status")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("post", "user")
    date_hierarchy = "created_at"


@admin.register(ProfileImage)
class ProfileImageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "caption",
        "visibility",
        "sort_order",
        "is_featured",
        "created_at",
    )
    search_fields = ("user__email", "user__firstname", "user__lastname", "caption")
    list_filter = ("visibility", "is_featured", "created_at")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("user",)


@admin.register(ProfileFollow)
class ProfileFollowAdmin(admin.ModelAdmin):
    list_display = ("id", "follower", "following", "status", "created_at", "updated_at")
    search_fields = (
        "follower__email",
        "follower__firstname",
        "follower__lastname",
        "following__email",
        "following__firstname",
        "following__lastname",
    )
    list_filter = ("status", "created_at", "updated_at")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("follower", "following")
    date_hierarchy = "created_at"


@admin.register(VideoWatchHistory)
class VideoWatchHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "article",
        "watched_seconds",
        "completed",
        "last_watched_at",
    )
    search_fields = ("user__email", "article__title")
    list_filter = ("completed", "last_watched_at")
    readonly_fields = ("last_watched_at",)
    autocomplete_fields = ("user", "article")
    date_hierarchy = "last_watched_at"


@admin.register(UserRatingSummary)
class UserRatingSummaryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "ratings_count",
        "average_rating_given",
        "highest_rating_count",
        "lowest_rating_count",
        "updated_at",
    )
    search_fields = ("user__email", "user__firstname", "user__lastname")
    readonly_fields = ("updated_at",)
    autocomplete_fields = ("user",)


@admin.register(SavedArticle)
class SavedArticleAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "article", "created_at")
    search_fields = ("user__email", "article__title")
    list_filter = ("created_at",)
    readonly_fields = ("created_at",)
    autocomplete_fields = ("user", "article")
    date_hierarchy = "created_at"
