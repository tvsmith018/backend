from django.conf import settings
from graphene_django.views import GraphQLView
from graphql.validation import NoSchemaIntrospectionCustomRule


def build_graphql_validation_rules():
    if settings.GRAPHQL_ALLOW_INTROSPECTION:
        return None
    return [NoSchemaIntrospectionCustomRule]


def build_graphql_view():
    return GraphQLView.as_view(
        graphiql=settings.GRAPHQL_ENABLE_GRAPHIQL,
        validation_rules=build_graphql_validation_rules(),
    )
