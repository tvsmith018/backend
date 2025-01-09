import graphene 
from graphene_django import DjangoObjectType, filter
from django_filters import FilterSet, OrderingFilter
from graphene import relay
from graphql_relay import from_global_id

from .models import Articles
from django.db.models import Q



class ArticleFilter(FilterSet):
    class Meta:
        model = Articles
        fields = ['category', 'title', 'author', 'created']

    order_by = OrderingFilter(
        fields = (
            ('created'), ('title'), ('author')
        )
    )

    

class ArticlesNode(DjangoObjectType):

    class Meta:
        model = Articles
        interfaces = (graphene.relay.Node, )


class Query(graphene.ObjectType):
    articles = graphene.relay.Node.Field(ArticlesNode)
    all_articles = filter.DjangoFilterConnectionField(ArticlesNode, filterset_class=ArticleFilter, search=graphene.String(), exempt=graphene.List(graphene.String), id = graphene.String(), typefield=graphene.String())
    
    def resolve_articles(self, info, **kwargs):
        return ArticleFilter(kwargs).qs
    
    def resolve_all_articles(self, info, **kwargs):
        
        articles = Articles.objects.all()

        if "id" in kwargs:
            node_type, pk = from_global_id(kwargs["id"])
            articles = Articles.objects.filter(pk=pk)

        if "exempt" in kwargs:
            articles = articles.exclude(**{kwargs["typefield"]:kwargs["exempt"]})
        
        if "category" in kwargs:
            articles = articles.filter(category=kwargs["category"])

        if "search" in kwargs:
            filter = (
                Q(title__icontains=kwargs["search"]) |
                Q(title__startswith=kwargs["search"]) |
                Q(category__icontains=kwargs["search"]) |
                Q(category__startswith=kwargs["search"]) |
                Q(author__firstname__icontains=kwargs["search"]) |
                Q(author__firstname__startswith=kwargs["search"]) |
                Q(author__lastname__icontains=kwargs["search"]) |
                Q(author__lastname__startswith=kwargs["search"])
            )

            articles = Articles.objects.filter(filter)

        return articles

schema = graphene.Schema(query=Query)