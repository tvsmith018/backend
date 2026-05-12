from django_filters import FilterSet, CharFilter, NumberFilter, DateTimeFilter, OrderingFilter
from graphql_relay.node.node import from_global_id

from comments.models import CommentReply, Comments


class NodeIDFilterMixin:
    id = CharFilter(method="filter_id")

    def filter_id(self, qs, name, value):
        _, pk = from_global_id(value)
        return qs.filter(pk=pk)


class CommentsFilter(NodeIDFilterMixin, FilterSet):
    article = CharFilter(method="filter_article")
    user = NumberFilter(field_name="user__id")
    like_count_min = NumberFilter(field_name="like_count", lookup_expr="gte")
    like_count_max = NumberFilter(field_name="like_count", lookup_expr="lte")
    reply_count_min = NumberFilter(field_name="reply_count", lookup_expr="gte")
    reply_count_max = NumberFilter(field_name="reply_count", lookup_expr="lte")

    body = CharFilter(
        field_name="body",
        lookup_expr="icontains",
    )

    created_after = DateTimeFilter(
        field_name="created",
        lookup_expr="gte",
    )

    order_by = OrderingFilter(
        fields=(
            ("created", "created"),
            ("article", "article"),
            ("user", "user"),
            ("like_count", "like_count"),
            ("reply_count", "reply_count"),
        )
    )

    class Meta:
        model = Comments
        fields = [
            "id",
            "article",
            "user",
            "body",
            "like_count_min",
            "like_count_max",
            "reply_count_min",
            "reply_count_max",
            "created_after",
        ]

    def filter_article(self, qs, name, value):
        raw = (value or "").strip()
        if raw.isdigit():
            return qs.filter(article__id=int(raw))
        try:
            _, pk = from_global_id(raw)
            return qs.filter(article__id=int(pk))
        except Exception:
            return qs.none()


class CommentReplyFilter(NodeIDFilterMixin, FilterSet):
    comment = CharFilter(method="filter_comment")
    user = NumberFilter(field_name="user__id")
    status = CharFilter(field_name="status")
    body = CharFilter(field_name="body", lookup_expr="icontains")
    created_after = DateTimeFilter(field_name="created", lookup_expr="gte")
    updated_after = DateTimeFilter(field_name="updated", lookup_expr="gte")
    order_by = OrderingFilter(
        fields=(
            ("created", "created"),
            ("updated", "updated"),
            ("comment", "comment"),
            ("user", "user"),
        )
    )

    class Meta:
        model = CommentReply
        fields = [
            "id",
            "comment",
            "user",
            "status",
            "body",
            "created_after",
            "updated_after",
        ]

    def filter_comment(self, qs, name, value):
        raw = (value or "").strip()
        if raw.isdigit():
            return qs.filter(comment__id=int(raw))
        try:
            _, pk = from_global_id(raw)
            return qs.filter(comment__id=int(pk))
        except Exception:
            return qs.none()