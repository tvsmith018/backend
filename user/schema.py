import graphene 
from graphene_django import DjangoObjectType

from .models import User

class UserType(DjangoObjectType):
    class Meta:
        model = User
        fields= "__all__"

class Query(graphene.ObjectType):
    user = graphene.List(UserType)

    def resolve_user(self, info):
        return User.objects.all()
    
schema = graphene.Schema(query=Query)