from django_filters import (
    FilterSet,
    CharFilter,
    NumberFilter,
    DateTimeFilter,
    OrderingFilter,
    BooleanFilter,
)
from graphql_relay.node.node import from_global_id
from django.contrib.postgres.search import SearchVector
from articles.models import ArticleView, Articles

class ArticleFilter(FilterSet):
    id = CharFilter(method="filter_id")
    category = CharFilter()
    search = CharFilter(method="filter_search")
    author = NumberFilter(field_name="author__id")
    featuredType = CharFilter()
    created_after = DateTimeFilter(
        field_name="created",
        lookup_expr="gte",
    )

    order_by = OrderingFilter(
        fields=(
            ("created", "created"),
            ("title", "title"),
            ("category", "category"),
        )
    )

    def filter_id(self, qs, name, value):
        _, pk = from_global_id(value)
        return qs.filter(pk=pk)
    
    def filter_search(self, qs, name, value):
        return qs.annotate(
            search=SearchVector(
                "title",
                "category",
                "author__firstname",
                "author__lastname",
            )
        ).filter(search=value)

    
    class Meta:
        model = Articles
        fields = [
            "category",
            "author",
            "created_after",
            "id",
            "search",
            "featuredType"
        ]


class ArticleViewFilter(FilterSet):
    id = CharFilter(method="filter_id")
    article = NumberFilter(field_name="article__id")
    user = NumberFilter(field_name="user__id")
    source = CharFilter(field_name="source")
    is_counted = BooleanFilter(field_name="is_counted")
    is_unique = BooleanFilter(field_name="is_unique")
    created_after = DateTimeFilter(field_name="created_at", lookup_expr="gte")
    watched_seconds_min = NumberFilter(field_name="watched_seconds", lookup_expr="gte")
    watched_seconds_max = NumberFilter(field_name="watched_seconds", lookup_expr="lte")

    order_by = OrderingFilter(
        fields=(
            ("created_at", "created_at"),
            ("watched_seconds", "watched_seconds"),
        )
    )

    def filter_id(self, queryset, name, value):
        _, pk = from_global_id(value)
        return queryset.filter(pk=pk)

    class Meta:
        model = ArticleView
        fields = [
            "id",
            "article",
            "user",
            "source",
            "is_counted",
            "is_unique",
            "created_after",
            "watched_seconds_min",
            "watched_seconds_max",
        ]