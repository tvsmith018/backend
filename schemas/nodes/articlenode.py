import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from django.db.models import Avg

from articles.models import ArticleView, Articles

class ArticlesNode(DjangoObjectType):
    image1x1_url = graphene.String()
    image4x3_url = graphene.String()
    image16x9_url = graphene.String()
    average_rating = graphene.Float()
    ratings_count = graphene.Int()

    class Meta:
        model = Articles
        interfaces = (relay.Node,)
        fields = (
            "id",
            "title",
            "altImage",
            "category",
            "briefsummary",
            "body",
            "author",
            "badgeColor",
            "featuredType",
            "videoLink",
            "videoType",
            "created",
            "views_count",
            "unique_views_count",
            "counted_views_count",
            "last_viewed_at",
            "image1x1_url",
            "image4x3_url",
            "image16x9_url",
        )

    def resolve_average_rating(self, info):
        annotated = getattr(self, "average_rating_live", None)
        if annotated is not None:
            return float(annotated)
        return self.rating_records.aggregate(avg=Avg("rate")).get("avg")

    def resolve_ratings_count(self, info):
        annotated = getattr(self, "ratings_count_live", None)
        if annotated is not None:
            return int(annotated)
        return int(self.rating_records.count())

class ArticlesConnection(relay.Connection):
    class Meta:
        node = ArticlesNode


class ArticleViewNode(DjangoObjectType):
    class Meta:
        model = ArticleView
        interfaces = (relay.Node,)
        fields = (
            "id",
            "article",
            "user",
            "session_key",
            "ip_address",
            "user_agent",
            "source",
            "is_counted",
            "is_unique",
            "watched_seconds",
            "created_at",
        )