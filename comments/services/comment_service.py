from comments.models import CommentReply, Comments

class CommentService:

    @staticmethod
    def create_comment(*, user, article, body):
        return Comments.objects.create(
            user=user,
            article=article,
            body=body
        )

    @staticmethod
    def create_comment_reply(*, comment, user, body):
        return CommentReply.objects.create(
            comment=comment,
            user=user,
            body=body,
        )
