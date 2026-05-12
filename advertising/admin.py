from django.contrib import admin

from .models import (
    AdCreative,
    AdPerformanceDaily,
    AdPlacement,
    AdvertisingCampaign,
    AdvertisingAudienceDaily,
    AdvertisingPartnerAccount,
    CampaignPlacement,
)


@admin.register(AdvertisingPartnerAccount)
class AdvertisingPartnerAccountAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "business_name",
        "user",
        "status",
        "verified_at",
        "preferred_billing_model",
        "dashboard_enabled",
        "current_balance_cents",
        "monthly_spend_cents",
        "total_impressions",
        "total_clicks",
        "average_ctr",
        "last_funded_at",
        "approved_at",
    )
    search_fields = ("business_name", "contact_name", "billing_email", "user__email")
    list_filter = ("status", "preferred_billing_model", "dashboard_enabled", "fraud_monitoring_enabled")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("user",)


@admin.register(AdPlacement)
class AdPlacementAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "placement_type", "active", "created_at")
    search_fields = ("code", "name")
    list_filter = ("placement_type", "active")
    readonly_fields = ("created_at", "updated_at")


@admin.register(AdvertisingCampaign)
class AdvertisingCampaignAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "partner",
        "status",
        "pricing_model",
        "budget_cents",
        "start_at",
        "end_at",
    )
    search_fields = ("name", "partner__business_name", "partner__user__email")
    list_filter = ("status", "pricing_model", "start_at", "end_at")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("partner",)


@admin.register(AdCreative)
class AdCreativeAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "campaign", "creative_type", "review_status", "is_active", "approved_at")
    search_fields = ("title", "campaign__name")
    list_filter = ("creative_type", "review_status", "is_active")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("campaign",)


@admin.register(CampaignPlacement)
class CampaignPlacementAdmin(admin.ModelAdmin):
    list_display = ("id", "campaign", "placement", "status", "priority", "started_at", "ended_at")
    search_fields = ("campaign__name", "placement__name")
    list_filter = ("status", "placement__placement_type")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("campaign", "placement")


@admin.register(AdPerformanceDaily)
class AdPerformanceDailyAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "campaign",
        "creative",
        "placement",
        "date",
        "impressions",
        "clicks",
        "billable_impressions",
        "billable_clicks",
        "engagements",
        "spend_cents",
    )
    search_fields = ("campaign__name", "creative__title", "placement__name")
    list_filter = ("date",)
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("campaign", "creative", "placement")
    date_hierarchy = "date"


@admin.register(AdvertisingAudienceDaily)
class AdvertisingAudienceDailyAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "partner",
        "date",
        "impressions",
        "clicks",
        "ctr",
        "conversions",
        "spend_cents",
        "top_placement_code",
        "top_campaign_name",
    )
    search_fields = (
        "partner__business_name",
        "partner__user__email",
        "top_placement_code",
        "top_campaign_name",
    )
    list_filter = ("date",)
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("partner",)
    date_hierarchy = "date"
