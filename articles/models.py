from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.urls import reverse
from users.models import Users
from cloudinary.models import CloudinaryField


class Articles(models.Model):
    image1x1 = CloudinaryField('image1x1', null=True, blank=True, folder=f"article_image_1x1")
    image4x3 = CloudinaryField('image4x3', null=True, blank=True, folder=f"article_image_4x3")
    image16x9 = CloudinaryField('image16x9', null=True, blank=True, folder=f"article_image_16x9")
    title = models.CharField(max_length=200, null=False, blank=False)
    altImage = models.CharField(max_length=200, null=False, blank=False)
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    category = models.CharField(max_length=100, null=False, blank=False)
    briefsummary = models.TextField(null=False, blank=False)
    author = models.ForeignKey(Users, on_delete=models.CASCADE, null=False, blank=False)
    badgeColor = models.CharField(max_length=200, null=True, blank=True)
    featuredType = models.CharField(max_length=200, null=True, blank=True)
    videoLink = models.CharField(max_length=300, null=True, blank=True)
    body = models.TextField(null=True, blank=True)
    videoType = models.CharField(max_length=300, null=True, blank=True)
    ratings =  models.ManyToManyField(Users, through='Rating', related_name='rating_articles', blank=True)

    views_count = models.PositiveBigIntegerField(default=0)
    unique_views_count = models.PositiveBigIntegerField(default=0)
    counted_views_count = models.PositiveBigIntegerField(default=0)
    last_viewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('article_detail', args=[str(self.id)])
    
    @property
    def image1x1_url(self):
        return self.image1x1.url if self.image1x1 else None

    @property
    def image4x3_url(self):
        return self.image4x3.url if self.image4x3 else None

    @property
    def image16x9_url(self):
        return self.image16x9.url if self.image16x9 else None
    

class Rating(models.Model):
    user = models.ForeignKey(
        Users, 
        on_delete=models.CASCADE,
        related_name="article_ratings",
        db_index=True,
    )

    article = models.ForeignKey(
        Articles, 
        on_delete=models.CASCADE,
        related_name="rating_records",
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    rate = models.IntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "article"], name="unique_user_article_rating")
        ]
        indexes = [
            models.Index(fields=["article", "created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]


    def __str__(self):
        return f"{self.user.firstname} {self.user.lastname} likes {self.article.title}"


class ArticleView(models.Model):
    """
    Raw view-event table.
    This is what makes the system enterprise-grade instead of just a dumb counter.
    """

    class SourceChoices(models.TextChoices):
        WEB = "web", "Web"
        MOBILE = "mobile", "Mobile"
        API = "api", "API"
        EMBED = "embed", "Embed"
        OTHER = "other", "Other"

    article = models.ForeignKey(
        Articles,
        on_delete=models.CASCADE,
        related_name="view_events",
        db_index=True,
    )

    user = models.ForeignKey(
        Users,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="article_view_events",
        db_index=True,
    )

    session_key = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True, db_index=True)
    user_agent = models.TextField(null=True, blank=True)

    source = models.CharField(
        max_length=20,
        choices=SourceChoices.choices,
        default=SourceChoices.WEB,
        db_index=True,
    )

    is_counted = models.BooleanField(default=False, db_index=True)
    is_unique = models.BooleanField(default=False, db_index=True)
    watched_seconds = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["article", "created_at"]),
            models.Index(fields=["article", "user", "created_at"]),
            models.Index(fields=["article", "session_key", "created_at"]),
            models.Index(fields=["article", "ip_address", "created_at"]),
            models.Index(fields=["article", "is_counted", "created_at"]),
            models.Index(fields=["article", "is_unique", "created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(watched_seconds__gte=0),
                name="articleview_watched_seconds_gte_0",
            ),
        ]

    def __str__(self):
        identifier = self.user_id or self.session_key or self.ip_address or "anonymous"
        return f"View<{self.article_id}> - {identifier}"
    

class ArticleViewDaily(models.Model):
    """
    Daily analytics rollup.
    Good for dashboards, CPM, creator payouts, and trending metrics.
    """

    article = models.ForeignKey(
        Articles,
        on_delete=models.CASCADE,
        related_name="daily_view_stats",
        db_index=True,
    )
    date = models.DateField(db_index=True)

    views_count = models.PositiveBigIntegerField(default=0)
    unique_views_count = models.PositiveBigIntegerField(default=0)
    counted_views_count = models.PositiveBigIntegerField(default=0)

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(fields=["article", "date"], name="unique_article_daily_view_stat")
        ]
        indexes = [
            models.Index(fields=["article", "date"]),
            models.Index(fields=["date"]),
        ]

    def __str__(self):
        return f"{self.article.title} - {self.date}"