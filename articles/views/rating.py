from asgiref.sync import sync_to_async
from drf_spectacular.utils import extend_schema

from articles.serializers.rating import RatingSerializer
from articles.services.rating_service import RatingService
from common.mixins.article import ArticleMixin
from common.openapi import EnvelopeError, EnvelopeSuccess
from common.views.base import AuthenticatedAsyncAPIView
from users.throttling import PublicWriteThrottle


@extend_schema(
    responses={200: EnvelopeSuccess, 401: EnvelopeError, 404: EnvelopeError},
)
class UserArticleRatingView(AuthenticatedAsyncAPIView, ArticleMixin):

    async def get(self, request, article_id):
        article = await self.get_article(article_id)
        user = request.user

        has_rate = await sync_to_async(
            RatingService.user_has_rated
        )(user, article)

        return self.success({
            "has_rated": has_rate
        })


@extend_schema(
    request=RatingSerializer,
    responses={200: EnvelopeSuccess, 400: EnvelopeError, 401: EnvelopeError, 404: EnvelopeError},
)
class SetArticleRatingView(AuthenticatedAsyncAPIView, ArticleMixin):
    throttle_classes = [PublicWriteThrottle]

    async def post(self, request, article_id):
        serializer = RatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        article = await self.get_article(article_id)
        user = request.user

        await sync_to_async(RatingService.set_rating)(
            user,
            article,
            serializer.validated_data["rate"]
        )

        return self.success({
            "message":"Rating saved"
        })