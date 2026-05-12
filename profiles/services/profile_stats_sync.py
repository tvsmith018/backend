from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta
from typing import Any

from django.db.models import Avg, Count
from django.db.models.functions import TruncDate
from django.utils import timezone

from articles.models import ArticleView, Rating
from comments.models import CommentReply, Comments
from profiles.models import (
    ProfileFollow,
    ProfileImage,
    ProfilePost,
    ProfilePostLike,
    ProfilePostShare,
    UserProfileStats,
    UserRatingSummary,
)
from users.models import Users

TWO_DECIMAL_PLACES = Decimal("0.01")


def _to_decimal_rating(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value.quantize(TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP)
    return Decimal(str(value)).quantize(TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP)


def _group_daily_counts(
    queryset,
    *,
    date_field: str,
    distinct_field: str | None = None,
) -> dict:
    grouped = queryset.annotate(day=TruncDate(date_field)).values("day")
    if distinct_field:
        grouped = grouped.annotate(total=Count(distinct_field, distinct=True))
    else:
        grouped = grouped.annotate(total=Count("id"))
    return {
        row["day"]: int(row["total"])
        for row in grouped
        if row.get("day") is not None
    }


def _build_weekly_activity_series(user_id: int) -> list[dict[str, Any]]:
    today = timezone.localdate()
    start_date = today - timedelta(days=6)

    post_counts_by_day = _group_daily_counts(
        ProfilePost.objects.filter(
            user_id=user_id,
            created_at__date__gte=start_date,
        ),
        date_field="created_at",
    )
    follower_counts_by_day = _group_daily_counts(
        ProfileFollow.objects.filter(
            following_id=user_id,
            status=ProfileFollow.Status.ACTIVE,
            created_at__date__gte=start_date,
        ),
        date_field="created_at",
    )
    following_counts_by_day = _group_daily_counts(
        ProfileFollow.objects.filter(
            follower_id=user_id,
            status=ProfileFollow.Status.ACTIVE,
            created_at__date__gte=start_date,
        ),
        date_field="created_at",
    )
    video_counts_by_day = _group_daily_counts(
        ArticleView.objects.filter(
            user_id=user_id,
            is_counted=True,
            created_at__date__gte=start_date,
        ),
        date_field="created_at",
        distinct_field="article_id",
    )
    rating_counts_by_day = _group_daily_counts(
        Rating.objects.filter(
            user_id=user_id,
            created_at__date__gte=start_date,
        ),
        date_field="created_at",
    )
    upload_counts_by_day = _group_daily_counts(
        ProfileImage.objects.filter(
            user_id=user_id,
            created_at__date__gte=start_date,
        ),
        date_field="created_at",
    )
    comment_counts_by_day = _group_daily_counts(
        Comments.objects.filter(
            user_id=user_id,
            active=True,
            created__date__gte=start_date,
        ),
        date_field="created",
    )
    reply_counts_by_day = _group_daily_counts(
        CommentReply.objects.filter(
            user_id=user_id,
            status=CommentReply.Status.ACTIVE,
            created__date__gte=start_date,
        ),
        date_field="created",
    )
    post_like_counts_by_day = _group_daily_counts(
        ProfilePostLike.objects.filter(
            user_id=user_id,
            created_at__date__gte=start_date,
        ),
        date_field="created_at",
    )
    post_share_counts_by_day = _group_daily_counts(
        ProfilePostShare.objects.filter(
            user_id=user_id,
            created_at__date__gte=start_date,
        ),
        date_field="created_at",
    )
    article_like_counts_by_day = _group_daily_counts(
        Rating.objects.filter(
            user_id=user_id,
            rate__gte=4,
            created_at__date__gte=start_date,
        ),
        date_field="created_at",
    )

    points: list[dict[str, Any]] = []
    for day_offset in range(7):
        date_value = start_date + timedelta(days=day_offset)
        posts_created = post_counts_by_day.get(date_value, 0)
        followers_gained = follower_counts_by_day.get(date_value, 0)
        following_actions = following_counts_by_day.get(date_value, 0)
        videos_watched = video_counts_by_day.get(date_value, 0)
        rated_articles = rating_counts_by_day.get(date_value, 0)
        uploaded_images = upload_counts_by_day.get(date_value, 0)
        comments_written = comment_counts_by_day.get(date_value, 0) + reply_counts_by_day.get(date_value, 0)
        post_likes_given = post_like_counts_by_day.get(date_value, 0)
        post_shares_given = post_share_counts_by_day.get(date_value, 0)
        article_likes_given = article_like_counts_by_day.get(date_value, 0)
        interactions_total = (
            posts_created
            + followers_gained
            + following_actions
            + videos_watched
            + rated_articles
            + uploaded_images
            + comments_written
            + post_likes_given
            + post_shares_given
            + article_likes_given
        )

        points.append(
            {
                "date": date_value.isoformat(),
                "day_label": date_value.strftime("%a"),
                "posts_created": posts_created,
                "followers_gained": followers_gained,
                "following_actions": following_actions,
                "videos_watched": videos_watched,
                "rated_articles": rated_articles,
                "uploaded_images": uploaded_images,
                "comments_written": comments_written,
                "post_likes_given": post_likes_given,
                "post_shares_given": post_shares_given,
                "article_likes_given": article_likes_given,
                "interactions_total": interactions_total,
            }
        )
    return points


def compute_profile_stats_values(user_id: int) -> dict[str, Any]:
    rated_articles_count = Rating.objects.filter(user_id=user_id).count()
    average_rating_raw = Rating.objects.filter(user_id=user_id).aggregate(avg=Avg("rate")).get("avg")
    average_rating_given = _to_decimal_rating(average_rating_raw)
    comments_written_count = (
        Comments.objects.filter(user_id=user_id, active=True).count()
        + CommentReply.objects.filter(user_id=user_id, status=CommentReply.Status.ACTIVE).count()
    )

    return {
        "posts_count": ProfilePost.objects.filter(user_id=user_id).count(),
        "followers_count": ProfileFollow.objects.filter(
            following_id=user_id,
            status=ProfileFollow.Status.ACTIVE,
        ).count(),
        "following_count": ProfileFollow.objects.filter(
            follower_id=user_id,
            status=ProfileFollow.Status.ACTIVE,
        ).count(),
        "uploaded_images_count": ProfileImage.objects.filter(user_id=user_id).count(),
        # Count unique videos watched by this user once they pass the counted threshold.
        "watched_videos_count": ArticleView.objects.filter(
            user_id=user_id,
            is_counted=True,
        )
        .values("article_id")
        .distinct()
        .count(),
        "rated_articles_count": rated_articles_count,
        "comments_written_count": comments_written_count,
        "post_likes_given_count": ProfilePostLike.objects.filter(user_id=user_id).count(),
        "post_shares_given_count": ProfilePostShare.objects.filter(user_id=user_id).count(),
        "article_likes_given_count": Rating.objects.filter(user_id=user_id, rate__gte=4).count(),
        "average_rating_given": average_rating_given,
        "weekly_activity_series": _build_weekly_activity_series(user_id),
    }


def sync_profile_stats_for_user(
    user_id: int,
    *,
    touch_last_activity: bool = True,
    dry_run: bool = False,
) -> bool:
    # Deletion cascades can trigger profile signals after the user row is gone.
    # Guarding here prevents FK violations from get_or_create(user_id=...).
    if not Users.objects.filter(pk=user_id).exists():
        return False

    if dry_run:
        stats = UserProfileStats.objects.filter(user_id=user_id).first() or UserProfileStats(
            user_id=user_id
        )
    else:
        stats = UserProfileStats.objects.filter(user_id=user_id).first()
    changed = False
    if stats is not None:
        next_values = compute_profile_stats_values(user_id)
        changed = any(getattr(stats, field) != value for field, value in next_values.items())

        if changed and not dry_run:
            for field, value in next_values.items():
                setattr(stats, field, value)
            if touch_last_activity:
                stats.last_activity_at = timezone.now()
            stats.save(
                update_fields=[
                    "posts_count",
                    "followers_count",
                    "following_count",
                    "uploaded_images_count",
                    "watched_videos_count",
                    "rated_articles_count",
                    "comments_written_count",
                    "post_likes_given_count",
                    "post_shares_given_count",
                    "article_likes_given_count",
                    "average_rating_given",
                    "weekly_activity_series",
                    "last_activity_at",
                    "updated_at",
                ]
            )

    if dry_run:
        rating_summary = UserRatingSummary.objects.filter(user_id=user_id).first() or UserRatingSummary(
            user_id=user_id
        )
    else:
        rating_summary = UserRatingSummary.objects.filter(user_id=user_id).first()
    if rating_summary is None:
        return changed
    ratings = Rating.objects.filter(user_id=user_id)
    ratings_count = ratings.count()
    avg_rating = _to_decimal_rating(ratings.aggregate(avg=Avg("rate")).get("avg"))
    highest_rating_count = ratings.filter(rate=5).count()
    lowest_rating_count = ratings.filter(rate=1).count()
    rating_summary_changed = (
        rating_summary.ratings_count != ratings_count
        or rating_summary.average_rating_given != avg_rating
        or rating_summary.highest_rating_count != highest_rating_count
        or rating_summary.lowest_rating_count != lowest_rating_count
    )
    if rating_summary_changed and not dry_run:
        rating_summary.ratings_count = ratings_count
        rating_summary.average_rating_given = avg_rating
        rating_summary.highest_rating_count = highest_rating_count
        rating_summary.lowest_rating_count = lowest_rating_count
        rating_summary.save(
            update_fields=[
                "ratings_count",
                "average_rating_given",
                "highest_rating_count",
                "lowest_rating_count",
                "updated_at",
            ]
        )

    return changed or rating_summary_changed
