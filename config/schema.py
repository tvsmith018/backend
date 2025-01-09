import graphene
import articles.schema
import user.schema

class Query(articles.schema.Query, user.schema.Query, graphene.ObjectType):
    pass

schema = graphene.Schema(query=Query)