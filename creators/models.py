from django.db import models
from django.utils import timezone

from articles.models import Articles
from users.models import Users


class ContentCreatorAccount(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        DEMONETIZED = "demonetized", "Demonetized"
        SUSPENDED = "suspended", "Suspended"

    user = models.OneToOneField(
        Users,
        on_delete=models.CASCADE,
        related_name="content_creator_account",
    )
    display_name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    monetization_enabled = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    demonetized_at = models.DateTimeField(null=True, blank=True)
    payout_email = models.EmailField(blank=True)
    payout_notes = models.TextField(blank=True)
    policy_strikes = models.PositiveSmallIntegerField(default=0)
    subscriber_count = models.PositiveBigIntegerField(default=0)
    watch_time_minutes = models.PositiveBigIntegerField(default=0)
    share_count = models.PositiveBigIntegerField(default=0)
    media_assets_count = models.PositiveIntegerField(default=0)
    earnings_balance_cents = models.BigIntegerField(default=0)
    lifetime_earnings_cents = models.BigIntegerField(default=0)
    last_published_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.display_name


class CreatorPerformanceDaily(models.Model):
    creator = models.ForeignKey(
        ContentCreatorAccount,
        on_delete=models.CASCADE,
        related_name="daily_performance",
    )
    article = models.ForeignKey(
        Articles,
        on_delete=models.CASCADE,
        related_name="creator_daily_performance",
        null=True,
        blank=True,
    )
    date = models.DateField(db_index=True)
    views = models.PositiveBigIntegerField(default=0)
    unique_views = models.PositiveBigIntegerField(default=0)
    comments_count = models.PositiveBigIntegerField(default=0)
    ratings_count = models.PositiveBigIntegerField(default=0)
    average_rating = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    engagement_count = models.PositiveBigIntegerField(default=0)
    revenue_cents = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["creator", "article", "date"],
                name="unique_creator_daily_performance_record",
            )
        ]
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["creator", "date"]),
            models.Index(fields=["article", "date"]),
        ]

    def __str__(self):
        return f"{self.creator.display_name} - {self.date}"


class CreatorAudienceDaily(models.Model):
    creator = models.ForeignKey(
        ContentCreatorAccount,
        on_delete=models.CASCADE,
        related_name="audience_daily",
    )
    date = models.DateField(db_index=True)
    subscribers_total = models.PositiveBigIntegerField(default=0)
    new_subscribers = models.PositiveBigIntegerField(default=0)
    returning_viewers = models.PositiveBigIntegerField(default=0)
    unique_viewers = models.PositiveBigIntegerField(default=0)
    shares = models.PositiveBigIntegerField(default=0)
    top_country = models.CharField(max_length=100, blank=True)
    most_active_hour_label = models.CharField(max_length=50, blank=True)
    watch_time_minutes = models.PositiveBigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["creator", "date"],
                name="unique_creator_audience_daily_record",
            )
        ]
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["creator", "date"]),
        ]

    def __str__(self):
        return f"{self.creator.display_name} - audience - {self.date}"


class CreatorEarningsLedger(models.Model):
    class EntryType(models.TextChoices):
        AD_IMPRESSION = "ad_impression", "Ad Impression"
        AD_CLICK = "ad_click", "Ad Click"
        ADJUSTMENT = "adjustment", "Adjustment"
        PAYOUT = "payout", "Payout"
        REVERSAL = "reversal", "Reversal"

    creator = models.ForeignKey(
        ContentCreatorAccount,
        on_delete=models.CASCADE,
        related_name="earnings_entries",
    )
    article = models.ForeignKey(
        Articles,
        on_delete=models.SET_NULL,
        related_name="creator_earnings_entries",
        null=True,
        blank=True,
    )
    entry_type = models.CharField(
        max_length=30,
        choices=EntryType.choices,
        db_index=True,
    )
    amount_cents = models.BigIntegerField()
    quantity = models.PositiveBigIntegerField(default=0)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)
    reference = models.CharField(max_length=255, blank=True, db_index=True)
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-occurred_at", "-created_at"]
        indexes = [
            models.Index(fields=["creator", "occurred_at"]),
            models.Index(fields=["entry_type", "occurred_at"]),
        ]

    def __str__(self):
        return f"{self.creator.display_name} - {self.entry_type}"


class CreatorPayoutCycle(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        PROCESSING = "processing", "Processing"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"

    period_start = models.DateField(db_index=True)
    period_end = models.DateField(db_index=True)
    scheduled_processing_date = models.DateField(
        help_text="Should stay within 10 days after the cycle closes.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["period_start", "period_end"],
                name="unique_creator_payout_cycle_window",
            )
        ]
        ordering = ["-period_end"]

    def __str__(self):
        return f"{self.period_start} to {self.period_end}"


class CreatorPayout(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        HELD = "held", "Held"

    creator = models.ForeignKey(
        ContentCreatorAccount,
        on_delete=models.CASCADE,
        related_name="payouts",
    )
    payout_cycle = models.ForeignKey(
        CreatorPayoutCycle,
        on_delete=models.CASCADE,
        related_name="creator_payouts",
    )
    amount_cents = models.BigIntegerField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    payable_on = models.DateField()
    paid_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)
    external_reference = models.CharField(max_length=255, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["creator", "payout_cycle"],
                name="unique_creator_payout_per_cycle",
            )
        ]
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "payable_on"]),
            models.Index(fields=["creator", "status"]),
        ]

    def __str__(self):
        return f"{self.creator.display_name} - {self.amount_cents}"
