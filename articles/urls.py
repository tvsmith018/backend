from django.urls import path
from articles.views.rating import (
    UserArticleRatingView,
    SetArticleRatingView,
)

urlpatterns = [
    path("rating/<str:article_id>/", UserArticleRatingView.as_view()),
    path("rating/<str:article_id>/set/", SetArticleRatingView.as_view()),
]