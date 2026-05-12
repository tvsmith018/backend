from django.db import models

from cloudinary.models import CloudinaryField

from users.models import Users


class AdvertisingPartnerAccount(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        CLOSED = "closed", "Closed"

    class BillingModel(models.TextChoices):
        CPM = "cpm", "CPM"
        CPC = "cpc", "CPC"
        MIXED = "mixed", "Mixed"

    user = models.OneToOneField(
        Users,
        on_delete=models.CASCADE,
        related_name="advertising_partner_account",
    )
    business_name = models.CharField(max_length=255)
    contact_name = models.CharField(max_length=255)
    website_url = models.URLField(blank=True)
    billing_email = models.EmailField()
    phone_number = models.CharField(max_length=50, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    preferred_billing_model = models.CharField(
        max_length=10,
        choices=BillingModel.choices,
        default=BillingModel.CPM,
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    dashboard_enabled = models.BooleanField(default=True)
    fraud_monitoring_enabled = models.BooleanField(default=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    current_balance_cents = models.PositiveBigIntegerField(default=0)
    monthly_spend_cents = models.PositiveBigIntegerField(default=0)
    total_impressions = models.PositiveBigIntegerField(default=0)
    total_clicks = models.PositiveBigIntegerField(default=0)
    average_ctr = models.DecimalField(max_digits=6, decimal_places=3, default=0)
    last_funded_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.business_name


class AdPlacement(models.Model):
    class PlacementType(models.TextChoices):
        ARTICLE = "article", "Article"
        VIDEO = "video", "Video"
        HOMEPAGE = "homepage", "Homepage"
        SIDEBAR = "sidebar", "Sidebar"
        BANNER = "banner", "Banner"
        OTHER = "other", "Other"

    code = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    placement_type = models.CharField(
        max_length=20,
        choices=PlacementType.choices,
        default=PlacementType.OTHER,
        db_index=True,
    )
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class AdvertisingCampaign(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_APPROVAL = "pending_approval", "Pending Approval"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        COMPLETED = "completed", "Completed"
        REJECTED = "rejected", "Rejected"

    class PricingModel(models.TextChoices):
        CPM = "cpm", "CPM"
        CPC = "cpc", "CPC"

    partner = models.ForeignKey(
        AdvertisingPartnerAccount,
        on_delete=models.CASCADE,
        related_name="campaigns",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    pricing_model = models.CharField(
        max_length=10,
        choices=PricingModel.choices,
        default=PricingModel.CPM,
        db_index=True,
    )
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    budget_cents = models.PositiveBigIntegerField(default=0)
    daily_budget_cents = models.PositiveBigIntegerField(default=0)
    cpm_rate_cents = models.PositiveIntegerField(default=0)
    cpc_rate_cents = models.PositiveIntegerField(default=0)
    target_url = models.URLField(blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "pricing_model"]),
            models.Index(fields=["start_at", "end_at"]),
        ]

    def __str__(self):
        return self.name


class AdCreative(models.Model):
    class CreativeType(models.TextChoices):
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"
        HTML = "html", "HTML"

    class ReviewStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    campaign = models.ForeignKey(
        AdvertisingCampaign,
        on_delete=models.CASCADE,
        related_name="creatives",
    )
    title = models.CharField(max_length=255)
    creative_type = models.CharField(
        max_length=20,
        choices=CreativeType.choices,
        default=CreativeType.IMAGE,
    )
    media = CloudinaryField(
        "ad_creative",
        null=True,
        blank=True,
        folder="advertising_creatives",
    )
    alt_text = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)
    call_to_action = models.CharField(max_length=100, blank=True)
    destination_url = models.URLField(blank=True)
    review_status = models.CharField(
        max_length=20,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING,
        db_index=True,
    )
    is_active = models.BooleanField(default=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class CampaignPlacement(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        REMOVED = "removed", "Removed"

    campaign = models.ForeignKey(
        AdvertisingCampaign,
        on_delete=models.CASCADE,
        related_name="placements",
    )
    placement = models.ForeignKey(
        AdPlacement,
        on_delete=models.PROTECT,
        related_name="campaign_placements",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    priority = models.PositiveSmallIntegerField(default=1)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "placement"],
                name="unique_campaign_placement",
            )
        ]
        ordering = ["priority", "-created_at"]

    def __str__(self):
        return f"{self.campaign.name} @ {self.placement.name}"


class AdPerformanceDaily(models.Model):
    campaign = models.ForeignKey(
        AdvertisingCampaign,
        on_delete=models.CASCADE,
        related_name="daily_performance",
    )
    creative = models.ForeignKey(
        AdCreative,
        on_delete=models.CASCADE,
        related_name="daily_performance",
        null=True,
        blank=True,
    )
    placement = models.ForeignKey(
        AdPlacement,
        on_delete=models.SET_NULL,
        related_name="daily_performance",
        null=True,
        blank=True,
    )
    date = models.DateField(db_index=True)
    impressions = models.PositiveBigIntegerField(default=0)
    billable_impressions = models.PositiveBigIntegerField(default=0)
    clicks = models.PositiveBigIntegerField(default=0)
    billable_clicks = models.PositiveBigIntegerField(default=0)
    engagements = models.PositiveBigIntegerField(default=0)
    invalid_clicks = models.PositiveBigIntegerField(default=0)
    spend_cents = models.PositiveBigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "creative", "placement", "date"],
                name="unique_ad_daily_performance_record",
            )
        ]
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["campaign", "date"]),
        ]

    def __str__(self):
        return f"{self.campaign.name} - {self.date}"


class AdvertisingAudienceDaily(models.Model):
    partner = models.ForeignKey(
        AdvertisingPartnerAccount,
        on_delete=models.CASCADE,
        related_name="audience_daily",
    )
    date = models.DateField(db_index=True)
    impressions = models.PositiveBigIntegerField(default=0)
    clicks = models.PositiveBigIntegerField(default=0)
    ctr = models.DecimalField(max_digits=6, decimal_places=3, default=0)
    conversions = models.PositiveBigIntegerField(default=0)
    spend_cents = models.PositiveBigIntegerField(default=0)
    top_placement_code = models.CharField(max_length=100, blank=True)
    top_campaign_name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["partner", "date"],
                name="unique_advertising_audience_daily_record",
            )
        ]
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["partner", "date"]),
        ]

    def __str__(self):
        return f"{self.partner.business_name} - audience - {self.date}"
