from graphql_relay import from_global_id
from articles.models import Articles
from asgiref.sync import sync_to_async

class ArticleMixin:

    @sync_to_async
    def get_article(self, article_id):
        _, pk = from_global_id(article_id)
        return Articles.objects.get(pk=pk)
