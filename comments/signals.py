from django.db.models.signals import post_delete, post_save


def register_signals():
    from .models import CommentLike, CommentReply, Comments

    def sync_comment_like_count(comment_id: int):
        total = CommentLike.objects.filter(comment_id=comment_id).count()
        Comments.objects.filter(pk=comment_id).update(like_count=total)

    def sync_comment_reply_count(comment_id: int):
        total = CommentReply.objects.filter(comment_id=comment_id).count()
        Comments.objects.filter(pk=comment_id).update(reply_count=total)

    def update_like_count_on_like_save(sender, instance, **kwargs):
        sync_comment_like_count(instance.comment_id)

    def update_like_count_on_like_delete(sender, instance, **kwargs):
        sync_comment_like_count(instance.comment_id)

    def update_reply_count_on_reply_save(sender, instance, **kwargs):
        sync_comment_reply_count(instance.comment_id)

    def update_reply_count_on_reply_delete(sender, instance, **kwargs):
        sync_comment_reply_count(instance.comment_id)

    post_save.connect(
        update_like_count_on_like_save,
        sender=CommentLike,
        dispatch_uid="comments.sync_comment_likes_on_save",
    )
    post_delete.connect(
        update_like_count_on_like_delete,
        sender=CommentLike,
        dispatch_uid="comments.sync_comment_likes_on_delete",
    )
    post_save.connect(
        update_reply_count_on_reply_save,
        sender=CommentReply,
        dispatch_uid="comments.sync_comment_replies_on_save",
    )
    post_delete.connect(
        update_reply_count_on_reply_delete,
        sender=CommentReply,
        dispatch_uid="comments.sync_comment_replies_on_delete",
    )
