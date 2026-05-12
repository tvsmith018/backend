from users.models import Users

from profiles.models import UserProfileSettings, UserProfileStats


class ProfileService:
    @staticmethod
    def get_profile_me(user_id: int) -> dict:
        user = Users.objects.get(pk=user_id)
        settings, _ = UserProfileSettings.objects.get_or_create(user=user)
        stats, _ = UserProfileStats.objects.get_or_create(user=user)

        return {
            "user": {
                "id": user.id,
                "firstname": user.firstname,
                "lastname": user.lastname,
                "email": user.email,
                "bio": user.bio,
                "dob": user.dob.isoformat() if user.dob else None,
                "avatar": user.avatar_url,
            },
            "settings": {
                "profile_is_public": settings.profile_is_public,
                "allow_messages": settings.allow_messages,
                "show_activity_feed": settings.show_activity_feed,
                "show_watch_history": settings.show_watch_history,
                "show_ratings": settings.show_ratings,
                "show_uploaded_images": settings.show_uploaded_images,
                "receive_notifications": settings.receive_notifications,
                "receive_marketing_notifications": settings.receive_marketing_notifications,
                "disabled_at": settings.disabled_at.isoformat()
                if settings.disabled_at
                else None,
                "delete_requested_at": settings.delete_requested_at.isoformat()
                if settings.delete_requested_at
                else None,
                "metadata": settings.metadata,
            },
            "stats": {
                "posts_count": stats.posts_count,
                "followers_count": stats.followers_count,
                "following_count": stats.following_count,
                "watched_videos_count": stats.watched_videos_count,
                "rated_articles_count": stats.rated_articles_count,
                "uploaded_images_count": stats.uploaded_images_count,
                "comments_written_count": stats.comments_written_count,
                "post_likes_given_count": stats.post_likes_given_count,
                "post_shares_given_count": stats.post_shares_given_count,
                "article_likes_given_count": stats.article_likes_given_count,
                "average_rating_given": str(stats.average_rating_given),
                "weekly_activity_series": stats.weekly_activity_series,
                "earnings_total_cents": stats.earnings_total_cents,
                "last_activity_at": stats.last_activity_at.isoformat()
                if stats.last_activity_at
                else None,
            },
        }
