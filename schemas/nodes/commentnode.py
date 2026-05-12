import graphene
from graphene import relay
from graphene_django import DjangoObjectType

from comments.models import CommentLike, CommentReply, Comments

class CommentsNode(DjangoObjectType):
    like_count = graphene.Int()
    reply_count = graphene.Int()
    liked_by_me = graphene.Boolean()

    class Meta:
        model = Comments
        interfaces = (relay.Node,)
        fields = (
            "id",
            "article",
            "user",
            "body",
            "like_count",
            "reply_count",
            "liked_by_me",
            "created",
            "updated",
            "active",
        )

    def resolve_like_count(self, info):
        annotated = getattr(self, "like_count_live", None)
        if annotated is not None:
            return int(annotated)
        return self.likes.count()

    def resolve_reply_count(self, info):
        annotated = getattr(self, "reply_count_live", None)
        if annotated is not None:
            return int(annotated)
        return self.comment_replies.count()

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
        return CommentLike.objects.filter(comment_id=self.pk, user_id=viewer_user_id).exists()


class CommentReplyNode(DjangoObjectType):
    class Meta:
        model = CommentReply
        interfaces = (relay.Node,)
        fields = (
            "id",
            "comment",
            "user",
            "body",
            "status",
            "created",
            "updated",
        )
