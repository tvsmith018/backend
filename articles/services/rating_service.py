from articles.models import Rating
from users.models import Users

class RatingService:

    @staticmethod
    def user_has_rated(tokenuser, article):
        user = Users.objects.get(id=tokenuser.user_id)
        return Rating.objects.filter(user=user, article=article).exists()

    @staticmethod
    def set_rating(tokenuser, article, rate):
        user = Users.objects.get(id=tokenuser.user_id)
        return Rating.objects.update_or_create(
            user=user,
            article=article,
            defaults={"rate": rate}
        )
