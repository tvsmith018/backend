import graphene
from graphene import relay
from graphene_django import DjangoObjectType

from profiles.models import (
    UserProfileSettings,
    UserProfileStats,
    ProfileFollow,
    ProfilePost,
    ProfilePostLike,
    ProfilePostShare,
    ProfilePostReply,
    ProfileImage,
    VideoWatchHistory,
    UserRatingSummary,
    SavedArticle,
)


class UserProfileSettingsNode(DjangoObjectType):
    class Meta:
        model = UserProfileSettings
        interfaces = (relay.Node,)
        fields = (
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
            "disabled_at",
            "delete_requested_at",
            "metadata",
            "created_at",
            "updated_at",
        )


class UserProfileStatsNode(DjangoObjectType):
    class Meta:
        model = UserProfileStats
        interfaces = (relay.Node,)
        fields = (
            "id",
            "user",
            "posts_count",
            "followers_count",
            "following_count",
            "watched_videos_count",
            "rated_articles_count",
            "uploaded_images_count",
            "comments_written_count",
            "post_likes_given_count",
            "post_shares_given_count",
            "article_likes_given_count",
            "average_rating_given",
            "weekly_activity_series",
            "earnings_total_cents",
            "last_activity_at",
            "updated_at",
        )


class ProfileFollowNode(DjangoObjectType):
    viewer_follows_follower = graphene.Boolean()
    follower_follows_viewer = graphene.Boolean()

    class Meta:
        model = ProfileFollow
        interfaces = (relay.Node,)
        fields = (
            "id",
            "follower",
            "following",
            "status",
            "created_at",
            "updated_at",
        )

    @staticmethod
    def _resolve_viewer_user_id(info):
        request = getattr(info, "context", None)
        user = getattr(request, "user", None)
        if user and getattr(user, "is_authenticated", False):
            return user.id

        raw_viewer_user_id = None
        if request is not None:
            raw_viewer_user_id = (
                request.headers.get("x-profile-viewer-id")
                if hasattr(request, "headers")
                else None
            ) or request.META.get("HTTP_X_PROFILE_VIEWER_ID")
        if raw_viewer_user_id:
            try:
                return int(raw_viewer_user_id)
            except (TypeError, ValueError):
                return None
        return None

    def resolve_viewer_follows_follower(self, info):
        annotated = getattr(self, "viewer_follows_follower_live", None)
        if annotated is not None:
            return bool(annotated)

        viewer_user_id = self._resolve_viewer_user_id(info)
        if viewer_user_id is None:
            return False

        return ProfileFollow.objects.filter(
            follower_id=viewer_user_id,
            following_id=self.follower_id,
            status=ProfileFollow.Status.ACTIVE,
        ).exists()

    def resolve_follower_follows_viewer(self, info):
        annotated = getattr(self, "follower_follows_viewer_live", None)
        if annotated is not None:
            return bool(annotated)

        viewer_user_id = self._resolve_viewer_user_id(info)
        if viewer_user_id is None:
            return False

        return ProfileFollow.objects.filter(
            follower_id=self.follower_id,
            following_id=viewer_user_id,
            status=ProfileFollow.Status.ACTIVE,
        ).exists()


class ProfilePostNode(DjangoObjectType):
    post_image_url = graphene.String()
    liked_by_me = graphene.Boolean()
    shared_by_me = graphene.Boolean()
    likes_count = graphene.Int()
    share_count = graphene.Int()

    class Meta:
        model = ProfilePost
        interfaces = (relay.Node,)
        fields = (
            "id",
            "user",
            "article",
            "body",
            "status",
            "likes_count",
            "share_count",
            "replies_count",
            "metadata",
            "post_image_url",
            "liked_by_me",
            "shared_by_me",
            "created_at",
            "updated_at",
        )

    def resolve_post_image_url(self, info):
        if not self.post_image:
            return None
        return getattr(self.post_image, "url", str(self.post_image))

    def resolve_likes_count(self, info):
        annotated = getattr(self, "likes_count_live", None)
        if annotated is not None:
            return int(annotated)
        return self.likes.count()

    def resolve_liked_by_me(self, info):
        annotated = getattr(self, "liked_by_me_live", None)
        if annotated is not None:
            return bool(annotated)

        request = getattr(info, "context", None)
        user = getattr(request, "user", None)
        viewer_user_id = None
        if user and getattr(user, "is_authenticated", False):
            viewer_user_id = user.id
        else:
            raw_viewer_user_id = None
            if request is not None:
                raw_viewer_user_id = (
                    request.headers.get("x-profile-viewer-id")
                    if hasattr(request, "headers")
                    else None
                ) or request.META.get("HTTP_X_PROFILE_VIEWER_ID")
            if raw_viewer_user_id:
                try:
                    viewer_user_id = int(raw_viewer_user_id)
                except (TypeError, ValueError):
                    viewer_user_id = None

        if viewer_user_id is None:
            return False

        prefetched_likes = getattr(self, "prefetched_likes_for_viewer", None)
        if prefetched_likes is not None:
            return len(prefetched_likes) > 0
        return ProfilePostLike.objects.filter(post_id=self.pk, user_id=viewer_user_id).exists()

    def resolve_share_count(self, info):
        annotated = getattr(self, "share_count_live", None)
        if annotated is not None:
            return int(annotated)
        return self.shares.count()

    def resolve_shared_by_me(self, info):
        annotated = getattr(self, "shared_by_me_live", None)
        if annotated is not None:
            return bool(annotated)

        request = getattr(info, "context", None)
        user = getattr(request, "user", None)
        viewer_user_id = None
        if user and getattr(user, "is_authenticated", False):
            viewer_user_id = user.id
        else:
            raw_viewer_user_id = None
            if request is not None:
                raw_viewer_user_id = (
                    request.headers.get("x-profile-viewer-id")
                    if hasattr(request, "headers")
                    else None
                ) or request.META.get("HTTP_X_PROFILE_VIEWER_ID")
            if raw_viewer_user_id:
                try:
                    viewer_user_id = int(raw_viewer_user_id)
                except (TypeError, ValueError):
                    viewer_user_id = None

        if viewer_user_id is None:
            return False

        prefetched_shares = getattr(self, "prefetched_shares_for_viewer", None)
        if prefetched_shares is not None:
            return len(prefetched_shares) > 0
        return ProfilePostShare.objects.filter(post_id=self.pk, user_id=viewer_user_id).exists()


class ProfilePostReplyNode(DjangoObjectType):
    class Meta:
        model = ProfilePostReply
        interfaces = (relay.Node,)
        fields = (
            "id",
            "post",
            "user",
            "body",
            "status",
            "created_at",
            "updated_at",
        )


class ProfileImageNode(DjangoObjectType):
    image_url = graphene.String()

    class Meta:
        model = ProfileImage
        interfaces = (relay.Node,)
        fields = (
            "id",
            "user",
            "caption",
            "visibility",
            "sort_order",
            "is_featured",
            "created_at",
            "updated_at",
            "image_url",
        )

    def resolve_image_url(self, info):
        if not self.image:
            return None
        return getattr(self.image, "url", str(self.image))


class VideoWatchHistoryNode(DjangoObjectType):
    class Meta:
        model = VideoWatchHistory
        interfaces = (relay.Node,)
        fields = (
            "id",
            "user",
            "article",
            "watched_seconds",
            "completed",
            "last_watched_at",
        )


class UserRatingSummaryNode(DjangoObjectType):
    class Meta:
        model = UserRatingSummary
        interfaces = (relay.Node,)
        fields = (
            "id",
            "user",
            "ratings_count",
            "average_rating_given",
            "highest_rating_count",
            "lowest_rating_count",
            "updated_at",
        )


class SavedArticleNode(DjangoObjectType):
    class Meta:
        model = SavedArticle
        interfaces = (relay.Node,)
        fields = (
            "id",
            "user",
            "article",
            "created_at",
        )
