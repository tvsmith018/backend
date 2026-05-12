from django.urls import re_path
from comments.consumers.article import ArticleCommentConsumer

websocket_urlpatterns = [
    re_path(r"ws/articles/(?P<article_id>[^/]+)/$", ArticleCommentConsumer.as_asgi())
]