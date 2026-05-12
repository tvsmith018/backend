from django.contrib import admin

from .models import (
    ContentCreatorAccount,
    CreatorAudienceDaily,
    CreatorEarningsLedger,
    CreatorPayout,
    CreatorPayoutCycle,
    CreatorPerformanceDaily,
)


@admin.register(ContentCreatorAccount)
class ContentCreatorAccountAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "display_name",
        "user",
        "status",
        "verified_at",
        "monetization_enabled",
        "policy_strikes",
        "subscriber_count",
        "watch_time_minutes",
        "share_count",
        "media_assets_count",
        "earnings_balance_cents",
        "lifetime_earnings_cents",
        "last_published_at",
    )
    search_fields = ("display_name", "user__email", "user__firstname", "user__lastname", "payout_email")
    list_filter = ("status", "monetization_enabled", "verified_at", "approved_at")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("user",)


@admin.register(CreatorPerformanceDaily)
class CreatorPerformanceDailyAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "creator",
        "article",
        "date",
        "views",
        "unique_views",
        "ratings_count",
        "average_rating",
        "engagement_count",
        "revenue_cents",
    )
    search_fields = ("creator__display_name", "article__title")
    list_filter = ("date",)
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("creator", "article")
    date_hierarchy = "date"


@admin.register(CreatorAudienceDaily)
class CreatorAudienceDailyAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "creator",
        "date",
        "subscribers_total",
        "new_subscribers",
        "returning_viewers",
        "unique_viewers",
        "shares",
        "top_country",
        "most_active_hour_label",
        "watch_time_minutes",
    )
    search_fields = ("creator__display_name", "creator__user__email", "top_country")
    list_filter = ("date", "top_country")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("creator",)
    date_hierarchy = "date"


@admin.register(CreatorEarningsLedger)
class CreatorEarningsLedgerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "creator",
        "entry_type",
        "amount_cents",
        "quantity",
        "reference",
        "occurred_at",
    )
    search_fields = ("creator__display_name", "reference", "article__title")
    list_filter = ("entry_type", "occurred_at")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("creator", "article")
    date_hierarchy = "occurred_at"


@admin.register(CreatorPayoutCycle)
class CreatorPayoutCycleAdmin(admin.ModelAdmin):
    list_display = ("id", "period_start", "period_end", "scheduled_processing_date", "status", "processed_at")
    search_fields = ("period_start", "period_end", "notes")
    list_filter = ("status", "scheduled_processing_date", "period_end")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "period_end"


@admin.register(CreatorPayout)
class CreatorPayoutAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "creator",
        "payout_cycle",
        "amount_cents",
        "status",
        "payable_on",
        "paid_at",
    )
    search_fields = ("creator__display_name", "external_reference")
    list_filter = ("status", "payable_on", "paid_at")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("creator", "payout_cycle")
    date_hierarchy = "payable_on"
