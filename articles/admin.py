from django.contrib import admin

from .models import ArticleView, ArticleViewDaily, Articles, Rating


class RatingInline(admin.TabularInline):
    model = Rating
    extra = 0
    fields = ("user", "rate", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("user",)
    show_change_link = True


class ArticleViewDailyInline(admin.TabularInline):
    model = ArticleViewDaily
    extra = 0
    fields = ("date", "views_count", "unique_views_count", "counted_views_count")
    readonly_fields = ("date",)
    show_change_link = True


@admin.register(Articles)
class ArticlesAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "category",
        "author",
        "featuredType",
        "videoType",
        "views_count",
        "unique_views_count",
        "counted_views_count",
        "last_viewed_at",
        "created",
    )
    search_fields = (
        "title",
        "altImage",
        "category",
        "author__email",
        "author__firstname",
        "author__lastname",
        "briefsummary",
    )
    list_filter = (
        "category",
        "featuredType",
        "videoType",
        "badgeColor",
        "created",
        "last_viewed_at",
    )
    readonly_fields = ("created", "last_viewed_at")
    autocomplete_fields = ("author",)
    inlines = [RatingInline, ArticleViewDailyInline]
    date_hierarchy = "created"


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "article",
        "user",
        "rate",
        "created_at",
    )
    search_fields = (
        "article__title",
        "user__email",
        "user__firstname",
        "user__lastname",
    )
    list_filter = ("rate", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("article", "user")
    date_hierarchy = "created_at"


@admin.register(ArticleView)
class ArticleViewAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "article",
        "user",
        "source",
        "is_counted",
        "is_unique",
        "watched_seconds",
        "session_key",
        "ip_address",
        "created_at",
    )
    search_fields = (
        "article__title",
        "user__email",
        "user__firstname",
        "user__lastname",
        "session_key",
        "ip_address",
        "user_agent",
    )
    list_filter = (
        "source",
        "is_counted",
        "is_unique",
        "created_at",
    )
    readonly_fields = ("created_at",)
    autocomplete_fields = ("article", "user")
    date_hierarchy = "created_at"


@admin.register(ArticleViewDaily)
class ArticleViewDailyAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "article",
        "date",
        "views_count",
        "unique_views_count",
        "counted_views_count",
    )
    search_fields = ("article__title",)
    list_filter = ("date",)
    autocomplete_fields = ("article",)
    date_hierarchy = "date"
