import graphene
from graphene import relay
from graphene_django import DjangoObjectType

from articles.models import Rating

class RatingNode(DjangoObjectType):
    class Meta:
        model = Rating
        interfaces = (relay.Node,)
        fields = (
            "id",
            "article",
            "user",
            "rate",
            "created_at",
        )