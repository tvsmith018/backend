import graphene
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField
from graphql_relay.node.node import from_global_id
from django.db.models import Avg, BooleanField, Count, Exists, OuterRef, Prefetch, Q, Value

from schemas.nodes.articlenode import ArticleViewNode, ArticlesNode, ArticlesConnection
from schemas.nodes.commentnode import CommentReplyNode, CommentsNode
from schemas.nodes.usernode import UserNode
from schemas.nodes.ratingnode import RatingNode
from schemas.nodes.profilenode import (
    UserProfileSettingsNode,
    UserProfileStatsNode,
    ProfileFollowNode,
    ProfilePostNode,
    ProfilePostReplyNode,
    ProfileImageNode,
    VideoWatchHistoryNode,
    UserRatingSummaryNode,
    SavedArticleNode,
)

from schemas.filters.articlefilter import ArticleFilter, ArticleViewFilter
from schemas.filters.commentfilter import CommentReplyFilter, CommentsFilter
from schemas.filters.ratingfilter import RatingFilter
from schemas.filters.userfilter import UsersFilter
from schemas.filters.profilefilter import (
    UserProfileSettingsFilter,
    UserProfileStatsFilter,
    ProfileFollowFilter,
    ProfilePostFilter,
    ProfilePostReplyFilter,
    ProfileImageFilter,
    VideoWatchHistoryFilter,
    UserRatingSummaryFilter,
    SavedArticleFilter,
)

from articles.models import ArticleView, Articles, Rating
from comments.models import CommentLike, CommentReply, Comments
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
    ProfilePostLike,
    ProfilePostShare,
)
from users.models import Users


def resolve_profile_viewer_user_id(info):
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


class Query(graphene.ObjectType):
    node = relay.Node.Field()
    users = DjangoFilterConnectionField(
        UserNode,
        filterset_class=UsersFilter
    )

    articles = DjangoFilterConnectionField(
        ArticlesNode,
        filterset_class=ArticleFilter,
    )
    article_views = DjangoFilterConnectionField(
        ArticleViewNode,
        filterset_class=ArticleViewFilter,
    )

    comments = DjangoFilterConnectionField(
        CommentsNode,
        filterset_class=CommentsFilter,
    )
    comment_replies = DjangoFilterConnectionField(
        CommentReplyNode,
        filterset_class=CommentReplyFilter,
    )

    ratings = DjangoFilterConnectionField(
        RatingNode,
        filterset_class=RatingFilter,
    )

    user_profile_settings = DjangoFilterConnectionField(
        UserProfileSettingsNode,
        filterset_class=UserProfileSettingsFilter,
    )

    user_profile_stats = DjangoFilterConnectionField(
        UserProfileStatsNode,
        filterset_class=UserProfileStatsFilter,
    )

    profile_follows = DjangoFilterConnectionField(
        ProfileFollowNode,
        filterset_class=ProfileFollowFilter,
    )
    followers = DjangoFilterConnectionField(
        ProfileFollowNode,
        user_id=graphene.Decimal(required=True),
        filterset_class=ProfileFollowFilter,
    )
    following = DjangoFilterConnectionField(
        ProfileFollowNode,
        user_id=graphene.Decimal(required=True),
        filterset_class=ProfileFollowFilter,
    )

    profile_posts = DjangoFilterConnectionField(
        ProfilePostNode,
        filterset_class=ProfilePostFilter,
    )

    profile_post_replies = DjangoFilterConnectionField(
        ProfilePostReplyNode,
        filterset_class=ProfilePostReplyFilter,
    )

    profile_images = DjangoFilterConnectionField(
        ProfileImageNode,
        filterset_class=ProfileImageFilter,
    )

    video_watch_history = DjangoFilterConnectionField(
        VideoWatchHistoryNode,
        filterset_class=VideoWatchHistoryFilter,
    )

    user_rating_summaries = DjangoFilterConnectionField(
        UserRatingSummaryNode,
        filterset_class=UserRatingSummaryFilter,
    )

    saved_articles = DjangoFilterConnectionField(
        SavedArticleNode,
        filterset_class=SavedArticleFilter,
    )

    category_articles = relay.ConnectionField(
        ArticlesConnection,
        category=graphene.String(required=True),
        exclude_id=graphene.ID(),
    )


    def resolve_users(self, info, **kwargs):
        request = getattr(info, "context", None)
        user = getattr(request, "user", None)
        viewer_user_id = user.id if user and getattr(user, "is_authenticated", False) else None
        queryset = Users.objects.filter(
            Q(profile_settings__disabled_at__isnull=True) | Q(profile_settings__isnull=True)
        )
        if viewer_user_id is not None:
            queryset = queryset | Users.objects.filter(id=viewer_user_id)
        return queryset.distinct()

    def resolve_articles(self, info, **kwargs):
        qs = (
            Articles.objects
            .select_related("author")
            .prefetch_related("comments")
            .annotate(
                average_rating_live=Avg("rating_records__rate"),
                ratings_count_live=Count("rating_records", distinct=True),
            )
        )
        return qs

    def resolve_article_views(self, info, **kwargs):
        return (
            ArticleView.objects
            .select_related("article", "user")
            .order_by("-created_at")
        )
        

    def resolve_comments(self, info, **kwargs):
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

        like_prefetch = Prefetch(
            "likes",
            queryset=CommentLike.objects.filter(user_id=viewer_user_id)
            if viewer_user_id is not None
            else CommentLike.objects.none(),
            to_attr="prefetched_likes_for_viewer",
        )
        liked_by_me_annotation = Value(False, output_field=BooleanField())
        if viewer_user_id is not None:
            liked_by_me_annotation = Exists(
                CommentLike.objects.filter(
                    comment_id=OuterRef("pk"),
                    user_id=viewer_user_id,
                )
            )

        return (
            Comments.objects
            .select_related("user", "article")
            .prefetch_related(like_prefetch, "comment_replies")
            .filter(parent__isnull=True)
            .annotate(
                like_count_live=Count("likes", distinct=True),
                reply_count_live=Count("comment_replies", distinct=True),
                liked_by_me_live=liked_by_me_annotation,
            )
            .order_by("created")
        )

    def resolve_comment_replies(self, info, **kwargs):
        return (
            CommentReply.objects
            .select_related("comment", "user")
            .order_by("created")
        )

    def resolve_ratings(self, info, **kwargs):
        return (
            Rating.objects
            .select_related("user", "article")
            .order_by("-created_at")
        )

    def resolve_user_profile_settings(self, info, **kwargs):
        return UserProfileSettings.objects.select_related("user").order_by("-created_at")

    def resolve_user_profile_stats(self, info, **kwargs):
        return UserProfileStats.objects.select_related("user").order_by("-updated_at")

    def resolve_profile_follows(self, info, **kwargs):
        return (
            ProfileFollow.objects
            .select_related("follower", "following")
            .order_by("-created_at")
        )

    def resolve_followers(self, info, user_id, **kwargs):
        queryset = (
            ProfileFollow.objects
            .select_related("follower", "following")
            .filter(following_id=user_id)
        )
        viewer_user_id = resolve_profile_viewer_user_id(info)
        if viewer_user_id is None:
            queryset = queryset.annotate(
                viewer_follows_follower_live=Value(False, output_field=BooleanField()),
                follower_follows_viewer_live=Value(False, output_field=BooleanField()),
            )
        else:
            queryset = queryset.annotate(
                viewer_follows_follower_live=Exists(
                    ProfileFollow.objects.filter(
                        follower_id=viewer_user_id,
                        following_id=OuterRef("follower_id"),
                        status=ProfileFollow.Status.ACTIVE,
                    )
                ),
                follower_follows_viewer_live=Exists(
                    ProfileFollow.objects.filter(
                        follower_id=OuterRef("follower_id"),
                        following_id=viewer_user_id,
                        status=ProfileFollow.Status.ACTIVE,
                    )
                ),
            )
        return queryset.order_by("-created_at")

    def resolve_following(self, info, user_id, **kwargs):
        queryset = (
            ProfileFollow.objects
            .select_related("follower", "following")
            .filter(follower_id=user_id)
        )
        viewer_user_id = resolve_profile_viewer_user_id(info)
        if viewer_user_id is None:
            queryset = queryset.annotate(
                viewer_follows_follower_live=Value(False, output_field=BooleanField()),
                follower_follows_viewer_live=Value(False, output_field=BooleanField()),
            )
        else:
            queryset = queryset.annotate(
                viewer_follows_follower_live=Exists(
                    ProfileFollow.objects.filter(
                        follower_id=viewer_user_id,
                        following_id=OuterRef("following_id"),
                        status=ProfileFollow.Status.ACTIVE,
                    )
                ),
                follower_follows_viewer_live=Exists(
                    ProfileFollow.objects.filter(
                        follower_id=OuterRef("following_id"),
                        following_id=viewer_user_id,
                        status=ProfileFollow.Status.ACTIVE,
                    )
                ),
            )
        return queryset.order_by("-created_at")

    def resolve_profile_posts(self, info, **kwargs):
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

        like_prefetch = Prefetch(
            "likes",
            queryset=ProfilePostLike.objects.filter(user_id=viewer_user_id)
            if viewer_user_id is not None
            else ProfilePostLike.objects.none(),
            to_attr="prefetched_likes_for_viewer",
        )
        share_prefetch = Prefetch(
            "shares",
            queryset=ProfilePostShare.objects.filter(user_id=viewer_user_id)
            if viewer_user_id is not None
            else ProfilePostShare.objects.none(),
            to_attr="prefetched_shares_for_viewer",
        )

        liked_by_me_annotation = Value(False, output_field=BooleanField())
        shared_by_me_annotation = Value(False, output_field=BooleanField())
        if viewer_user_id is not None:
            liked_by_me_annotation = Exists(
                ProfilePostLike.objects.filter(
                    post_id=OuterRef("pk"),
                    user_id=viewer_user_id,
                )
            )
            shared_by_me_annotation = Exists(
                ProfilePostShare.objects.filter(
                    post_id=OuterRef("pk"),
                    user_id=viewer_user_id,
                )
            )

        return (
            ProfilePost.objects
            .select_related("user", "article")
            .prefetch_related("replies", like_prefetch, share_prefetch)
            .annotate(
                likes_count_live=Count("likes", distinct=True),
                share_count_live=Count("shares", distinct=True),
                liked_by_me_live=liked_by_me_annotation,
                shared_by_me_live=shared_by_me_annotation,
            )
            .order_by("-created_at")
        )

    def resolve_profile_post_replies(self, info, **kwargs):
        return (
            ProfilePostReply.objects
            .select_related("post", "user")
            .order_by("created_at")
        )

    def resolve_profile_images(self, info, **kwargs):
        queryset = ProfileImage.objects.select_related("user")
        viewer_user_id = resolve_profile_viewer_user_id(info)
        raw_owner_id = kwargs.get("user")
        owner_user_id = None
        if raw_owner_id is not None:
            try:
                owner_user_id = int(raw_owner_id)
            except (TypeError, ValueError):
                owner_user_id = None

        if owner_user_id is not None and owner_user_id != viewer_user_id:
            queryset = queryset.filter(
                user_id=owner_user_id,
                visibility=ProfileImage.Visibility.PUBLIC,
            )
        elif owner_user_id is not None:
            queryset = queryset.filter(user_id=owner_user_id)
        elif viewer_user_id is None:
            queryset = queryset.filter(visibility=ProfileImage.Visibility.PUBLIC)
        else:
            queryset = queryset.filter(
                Q(user_id=viewer_user_id) | Q(visibility=ProfileImage.Visibility.PUBLIC)
            )

        return queryset.order_by("-is_featured", "sort_order", "created_at")

    def resolve_video_watch_history(self, info, **kwargs):
        return (
            VideoWatchHistory.objects
            .select_related("user", "article")
            .order_by("-last_watched_at")
        )

    def resolve_user_rating_summaries(self, info, **kwargs):
        return UserRatingSummary.objects.select_related("user").order_by("-updated_at")

    def resolve_saved_articles(self, info, **kwargs):
        return (
            SavedArticle.objects
            .select_related("user", "article")
            .order_by("-created_at")
        )
    
    def resolve_category_articles(
        self,
        info,
        category,
        exclude_id=None,
        **kwargs
    ):
        qs = (
            Articles.objects
            .filter(category=category)
            .select_related("author")
            .prefetch_related("comments")
            .annotate(
                average_rating_live=Avg("rating_records__rate"),
                ratings_count_live=Count("rating_records", distinct=True),
            )
            .order_by("-created")
        )

        if exclude_id:
            _, pk = from_global_id(exclude_id)
            qs = qs.exclude(pk=pk)

        return qs