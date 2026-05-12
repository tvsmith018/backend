from django_filters import (
    FilterSet,
    CharFilter,
    NumberFilter,
    DateTimeFilter,
    OrderingFilter,
    BooleanFilter,
)
from graphql_relay.node.node import from_global_id

from profiles.models import (
    UserProfileSettings,
    UserProfileStats,
    ProfileFollow,
    ProfilePost,
    ProfilePostReply,
    ProfileImage,
    VideoWatchHistory,
    UserRatingSummary,
    SavedArticle,
)


class NodeIDFilterMixin:
    id = CharFilter(method="filter_id")

    def filter_id(self, qs, name, value):
        _, pk = from_global_id(value)
        return qs.filter(pk=pk)


class UserProfileSettingsFilter(NodeIDFilterMixin, FilterSet):
    user = NumberFilter(field_name="user__id")
    profile_is_public = BooleanFilter(field_name="profile_is_public")
    allow_messages = BooleanFilter(field_name="allow_messages")
    show_activity_feed = BooleanFilter(field_name="show_activity_feed")
    show_watch_history = BooleanFilter(field_name="show_watch_history")
    show_ratings = BooleanFilter(field_name="show_ratings")
    show_uploaded_images = BooleanFilter(field_name="show_uploaded_images")
    receive_notifications = BooleanFilter(field_name="receive_notifications")
    receive_marketing_notifications = BooleanFilter(field_name="receive_marketing_notifications")

    disabled_after = DateTimeFilter(field_name="disabled_at", lookup_expr="gte")
    delete_requested_after = DateTimeFilter(field_name="delete_requested_at", lookup_expr="gte")
    created_after = DateTimeFilter(field_name="created_at", lookup_expr="gte")
    updated_after = DateTimeFilter(field_name="updated_at", lookup_expr="gte")

    order_by = OrderingFilter(
        fields=(
            ("created_at", "created_at"),
            ("updated_at", "updated_at"),
            ("disabled_at", "disabled_at"),
        )
    )

    class Meta:
        model = UserProfileSettings
        fields = [
            "id",
            "user",
            "profile_is_public",
            "allow_messages",
            "show_activity_feed",
            "show_watch_history",
            "show_ratings",
            "show_uploaded_images",
            "receive_notifications",
            "receive_marketing_notifications",
            "disabled_after",
            "delete_requested_after",
            "created_after",
            "updated_after",
        ]


class UserProfileStatsFilter(NodeIDFilterMixin, FilterSet):
    user = NumberFilter(field_name="user__id")

    posts_count_min = NumberFilter(field_name="posts_count", lookup_expr="gte")
    posts_count_max = NumberFilter(field_name="posts_count", lookup_expr="lte")
    followers_count_min = NumberFilter(field_name="followers_count", lookup_expr="gte")
    followers_count_max = NumberFilter(field_name="followers_count", lookup_expr="lte")
    following_count_min = NumberFilter(field_name="following_count", lookup_expr="gte")
    following_count_max = NumberFilter(field_name="following_count", lookup_expr="lte")

    watched_videos_count_min = NumberFilter(field_name="watched_videos_count", lookup_expr="gte")
    watched_videos_count_max = NumberFilter(field_name="watched_videos_count", lookup_expr="lte")
    rated_articles_count_min = NumberFilter(field_name="rated_articles_count", lookup_expr="gte")
    rated_articles_count_max = NumberFilter(field_name="rated_articles_count", lookup_expr="lte")

    uploaded_images_count_min = NumberFilter(field_name="uploaded_images_count", lookup_expr="gte")
    uploaded_images_count_max = NumberFilter(field_name="uploaded_images_count", lookup_expr="lte")

    average_rating_given_min = NumberFilter(field_name="average_rating_given", lookup_expr="gte")
    average_rating_given_max = NumberFilter(field_name="average_rating_given", lookup_expr="lte")
    earnings_total_cents_min = NumberFilter(field_name="earnings_total_cents", lookup_expr="gte")
    earnings_total_cents_max = NumberFilter(field_name="earnings_total_cents", lookup_expr="lte")

    last_activity_after = DateTimeFilter(field_name="last_activity_at", lookup_expr="gte")
    updated_after = DateTimeFilter(field_name="updated_at", lookup_expr="gte")

    order_by = OrderingFilter(
        fields=(
            ("updated_at", "updated_at"),
            ("posts_count", "posts_count"),
            ("followers_count", "followers_count"),
            ("following_count", "following_count"),
            ("average_rating_given", "average_rating_given"),
            ("earnings_total_cents", "earnings_total_cents"),
        )
    )

    class Meta:
        model = UserProfileStats
        fields = [
            "id",
            "user",
            "posts_count_min",
            "posts_count_max",
            "followers_count_min",
            "followers_count_max",
            "following_count_min",
            "following_count_max",
            "watched_videos_count_min",
            "watched_videos_count_max",
            "rated_articles_count_min",
            "rated_articles_count_max",
            "uploaded_images_count_min",
            "uploaded_images_count_max",
            "average_rating_given_min",
            "average_rating_given_max",
            "earnings_total_cents_min",
            "earnings_total_cents_max",
            "last_activity_after",
            "updated_after",
        ]


class ProfileFollowFilter(NodeIDFilterMixin, FilterSet):
    follower = NumberFilter(field_name="follower__id")
    following = NumberFilter(field_name="following__id")
    status = CharFilter(field_name="status")

    created_after = DateTimeFilter(field_name="created_at", lookup_expr="gte")
    updated_after = DateTimeFilter(field_name="updated_at", lookup_expr="gte")

    order_by = OrderingFilter(
        fields=(
            ("created_at", "created_at"),
            ("updated_at", "updated_at"),
            ("status", "status"),
        )
    )

    class Meta:
        model = ProfileFollow
        fields = [
            "id",
            "follower",
            "following",
            "status",
            "created_after",
            "updated_after",
        ]


class ProfilePostFilter(NodeIDFilterMixin, FilterSet):
    user = NumberFilter(field_name="user__id")
    article = NumberFilter(field_name="article__id")
    status = CharFilter(field_name="status")
    body = CharFilter(field_name="body", lookup_expr="icontains")

    created_after = DateTimeFilter(field_name="created_at", lookup_expr="gte")
    updated_after = DateTimeFilter(field_name="updated_at", lookup_expr="gte")

    likes_count_min = NumberFilter(field_name="likes_count", lookup_expr="gte")
    likes_count_max = NumberFilter(field_name="likes_count", lookup_expr="lte")
    replies_count_min = NumberFilter(field_name="replies_count", lookup_expr="gte")
    replies_count_max = NumberFilter(field_name="replies_count", lookup_expr="lte")

    order_by = OrderingFilter(
        fields=(
            ("created_at", "created_at"),
            ("updated_at", "updated_at"),
            ("likes_count", "likes_count"),
            ("replies_count", "replies_count"),
        )
    )

    class Meta:
        model = ProfilePost
        fields = [
            "id",
            "user",
            "article",
            "status",
            "body",
            "created_after",
            "updated_after",
            "likes_count_min",
            "likes_count_max",
            "replies_count_min",
            "replies_count_max",
        ]


class ProfilePostReplyFilter(NodeIDFilterMixin, FilterSet):
    post = NumberFilter(field_name="post__id")
    user = NumberFilter(field_name="user__id")
    status = CharFilter(field_name="status")
    body = CharFilter(field_name="body", lookup_expr="icontains")

    created_after = DateTimeFilter(field_name="created_at", lookup_expr="gte")
    updated_after = DateTimeFilter(field_name="updated_at", lookup_expr="gte")

    order_by = OrderingFilter(
        fields=(
            ("created_at", "created_at"),
            ("updated_at", "updated_at"),
            ("post", "post"),
            ("user", "user"),
        )
    )

    class Meta:
        model = ProfilePostReply
        fields = [
            "id",
            "post",
            "user",
            "status",
            "body",
            "created_after",
            "updated_after",
        ]


class ProfileImageFilter(NodeIDFilterMixin, FilterSet):
    user = NumberFilter(field_name="user__id")
    visibility = CharFilter(field_name="visibility")
    caption = CharFilter(field_name="caption", lookup_expr="icontains")
    is_featured = BooleanFilter(field_name="is_featured")

    created_after = DateTimeFilter(field_name="created_at", lookup_expr="gte")
    updated_after = DateTimeFilter(field_name="updated_at", lookup_expr="gte")

    sort_order_min = NumberFilter(field_name="sort_order", lookup_expr="gte")
    sort_order_max = NumberFilter(field_name="sort_order", lookup_expr="lte")

    order_by = OrderingFilter(
        fields=(
            ("sort_order", "sort_order"),
            ("created_at", "created_at"),
            ("updated_at", "updated_at"),
        )
    )

    class Meta:
        model = ProfileImage
        fields = [
            "id",
            "user",
            "visibility",
            "caption",
            "is_featured",
            "created_after",
            "updated_after",
            "sort_order_min",
            "sort_order_max",
        ]


class VideoWatchHistoryFilter(NodeIDFilterMixin, FilterSet):
    user = NumberFilter(field_name="user__id")
    article = NumberFilter(field_name="article__id")
    completed = BooleanFilter(field_name="completed")

    watched_seconds_min = NumberFilter(field_name="watched_seconds", lookup_expr="gte")
    watched_seconds_max = NumberFilter(field_name="watched_seconds", lookup_expr="lte")
    last_watched_after = DateTimeFilter(field_name="last_watched_at", lookup_expr="gte")

    order_by = OrderingFilter(
        fields=(
            ("last_watched_at", "last_watched_at"),
            ("watched_seconds", "watched_seconds"),
        )
    )

    class Meta:
        model = VideoWatchHistory
        fields = [
            "id",
            "user",
            "article",
            "completed",
            "watched_seconds_min",
            "watched_seconds_max",
            "last_watched_after",
        ]


class UserRatingSummaryFilter(NodeIDFilterMixin, FilterSet):
    user = NumberFilter(field_name="user__id")

    ratings_count_min = NumberFilter(field_name="ratings_count", lookup_expr="gte")
    ratings_count_max = NumberFilter(field_name="ratings_count", lookup_expr="lte")
    average_rating_given_min = NumberFilter(field_name="average_rating_given", lookup_expr="gte")
    average_rating_given_max = NumberFilter(field_name="average_rating_given", lookup_expr="lte")
    highest_rating_count_min = NumberFilter(field_name="highest_rating_count", lookup_expr="gte")
    highest_rating_count_max = NumberFilter(field_name="highest_rating_count", lookup_expr="lte")
    lowest_rating_count_min = NumberFilter(field_name="lowest_rating_count", lookup_expr="gte")
    lowest_rating_count_max = NumberFilter(field_name="lowest_rating_count", lookup_expr="lte")

    updated_after = DateTimeFilter(field_name="updated_at", lookup_expr="gte")

    order_by = OrderingFilter(
        fields=(
            ("updated_at", "updated_at"),
            ("ratings_count", "ratings_count"),
            ("average_rating_given", "average_rating_given"),
        )
    )

    class Meta:
        model = UserRatingSummary
        fields = [
            "id",
            "user",
            "ratings_count_min",
            "ratings_count_max",
            "average_rating_given_min",
            "average_rating_given_max",
            "highest_rating_count_min",
            "highest_rating_count_max",
            "lowest_rating_count_min",
            "lowest_rating_count_max",
            "updated_after",
        ]


class SavedArticleFilter(NodeIDFilterMixin, FilterSet):
    user = NumberFilter(field_name="user__id")
    article = NumberFilter(field_name="article__id")
    created_after = DateTimeFilter(field_name="created_at", lookup_expr="gte")

    order_by = OrderingFilter(
        fields=(
            ("created_at", "created_at"),
            ("user", "user"),
            ("article", "article"),
        )
    )

    class Meta:
        model = SavedArticle
        fields = [
            "id",
            "user",
            "article",
            "created_after",
        ]
