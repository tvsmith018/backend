from models import Articles
from common.services.cache import get_or_set

class ArticleService:

    @staticmethod
    def list_articles():
        return (
            Articles.objects
            .select_related("author")
            .prefetch_related("comments")
        )
    
    @staticmethod
    def get_article(article_id):
        return get_or_set(
            f"article:{article_id}",
            60 * 5,
            lambda: Articles.objects
                .select_related("author")
                .get(id=article_id)
        )
