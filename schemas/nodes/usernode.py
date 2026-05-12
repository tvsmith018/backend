import graphene
from graphene import relay
from graphene_django import DjangoObjectType

from users.models import Users

class UserNode(DjangoObjectType):
    avatar_url = graphene.String()

    class Meta:
        model = Users
        interfaces = (relay.Node,)
        fields = (
            "id",
            "firstname",
            "lastname",
            "email",
            "avatar_url",
        )