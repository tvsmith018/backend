from django.urls import re_path

from articles.consumers.view_tracking import ArticleViewTrackingConsumer


websocket_urlpatterns = [
    re_path(
        r"ws/articles/(?P<article_id>[^/]+)/views/$",
        ArticleViewTrackingConsumer.as_asgi(),
    ),
]
