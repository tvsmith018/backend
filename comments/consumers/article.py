import json
from channels.db import database_sync_to_async
from common.consumers.base import BaseCommentConsumer
from common.mixins.article import ArticleMixin
from comments.models import CommentLike, CommentReply, Comments
from comments.serializers.comment import (
    CommentCreateSerializer,
    CommentDeleteSerializer,
    CommentLikeSerializer,
    CommentReplyDeleteSerializer,
    CommentReplySerializer,
)
from comments.services.comment_service import CommentService
from users.services.auth_service import AuthService

class ArticleCommentConsumer(BaseCommentConsumer, ArticleMixin):
    def _serialize_comment_payload(self, comment):
        return {
            "id": str(comment.id),
            "body": comment.body,
            "created": comment.created.isoformat(),
            "likeCount": comment.like_count,
            "replyCount": comment.reply_count,
            "user": {
                "id": str(comment.user.id),
                "firstname": comment.user.firstname,
                "lastname": comment.user.lastname,
                "avatarUrl": comment.user.avatar.url if comment.user.avatar else None,
            },
        }

    async def connect(self):
        self.article_id = self.scope["url_route"]["kwargs"]["article_id"]
        article = await self.get_article(self.article_id)
        self.article_pk = article.pk

        safe_id = (
            self.article_id.replace("=", ".")
            .replace("+", "-")
            .replace("/", "_")
        )
        self.group_name = f"article_comments_{safe_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        payload = json.loads(text_data)
        action = payload.get("action", "create_comment")

        if action == "like_comment":
            await self._handle_like(payload)
            return
        if action == "unlike_comment":
            await self._handle_unlike(payload)
            return
        if action == "delete_comment":
            await self._handle_delete(payload)
            return
        if action == "reply_comment":
            await self._handle_reply(payload)
            return
        if action == "delete_comment_reply":
            await self._handle_delete_reply(payload)
            return

        await self._handle_create(payload)

    async def _handle_create(self, payload):
        serializer = CommentCreateSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        user_id = int(serializer.validated_data["user_id"])
        user = await database_sync_to_async(AuthService.get_user)(user_id)
        article = await self.get_article(self.article_id)

        comment = await database_sync_to_async(CommentService.create_comment)(
            user=user,
            article=article,
            body=serializer.validated_data["body"],
        )
        latest_comment = await database_sync_to_async(Comments.objects.select_related("user").get)(pk=comment.pk)

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "comment.message",
                "payload": {
                    "eventType": "article_comment_created",
                    "comment": self._serialize_comment_payload(latest_comment),
                },
            },
        )

    async def _handle_like(self, payload):
        serializer = CommentLikeSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        user_id = int(serializer.validated_data["user_id"])
        comment_id = int(serializer.validated_data["comment_id"])
        user = await database_sync_to_async(AuthService.get_user)(user_id)
        comment = await database_sync_to_async(Comments.objects.get)(pk=comment_id)
        if comment.article_id != self.article_pk:
            return

        _, created = await database_sync_to_async(CommentLike.objects.get_or_create)(
            comment=comment,
            user=user,
        )
        latest_comment = await database_sync_to_async(Comments.objects.get)(pk=comment.pk)

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "comment.message",
                "payload": {
                    "eventType": "article_comment_liked",
                    "commentId": str(latest_comment.id),
                    "likeCount": latest_comment.like_count,
                    "likedByUserId": str(user.id),
                    "created": created,
                },
            },
        )

    async def _handle_unlike(self, payload):
        serializer = CommentLikeSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        user_id = int(serializer.validated_data["user_id"])
        comment_id = int(serializer.validated_data["comment_id"])
        user = await database_sync_to_async(AuthService.get_user)(user_id)
        comment = await database_sync_to_async(Comments.objects.get)(pk=comment_id)
        if comment.article_id != self.article_pk:
            return

        deleted_count, _ = await database_sync_to_async(
            CommentLike.objects.filter(comment=comment, user=user).delete
        )()
        deleted = deleted_count > 0
        latest_comment = await database_sync_to_async(Comments.objects.get)(pk=comment.pk)

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "comment.message",
                "payload": {
                    "eventType": "article_comment_unliked",
                    "commentId": str(latest_comment.id),
                    "likeCount": latest_comment.like_count,
                    "likedByUserId": str(user.id),
                    "created": False,
                    "deleted": deleted,
                },
            },
        )

    async def _handle_delete(self, payload):
        serializer = CommentDeleteSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        user_id = int(serializer.validated_data["user_id"])
        comment_id = int(serializer.validated_data["comment_id"])
        user = await database_sync_to_async(AuthService.get_user)(user_id)

        try:
            comment = await database_sync_to_async(Comments.objects.get)(pk=comment_id)
        except Comments.DoesNotExist:
            return
        if comment.article_id != self.article_pk:
            return

        if comment.user_id != user.id:
            return

        deleted_comment_id = str(comment.id)
        await database_sync_to_async(comment.delete)()
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "comment.message",
                "payload": {
                    "eventType": "article_comment_deleted",
                    "commentId": deleted_comment_id,
                    "deletedByUserId": str(user.id),
                },
            },
        )

    async def _handle_reply(self, payload):
        serializer = CommentReplySerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        user_id = int(serializer.validated_data["user_id"])
        comment_id = int(serializer.validated_data["comment_id"])
        user = await database_sync_to_async(AuthService.get_user)(user_id)
        comment = await database_sync_to_async(Comments.objects.get)(pk=comment_id)
        if comment.article_id != self.article_pk:
            return

        reply = await database_sync_to_async(CommentService.create_comment_reply)(
            comment=comment,
            user=user,
            body=serializer.validated_data["body"],
        )
        latest_comment = await database_sync_to_async(Comments.objects.get)(pk=comment.pk)
        latest_reply = await database_sync_to_async(CommentReply.objects.select_related("user").get)(pk=reply.pk)

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "comment.message",
                "payload": {
                    "eventType": "article_comment_replied",
                    "commentId": str(latest_comment.id),
                    "replyCount": latest_comment.reply_count,
                    "repliedByUserId": str(user.id),
                    "reply": {
                        "id": str(latest_reply.id),
                        "body": latest_reply.body,
                        "created": latest_reply.created.isoformat(),
                        "user": {
                            "id": str(user.id),
                            "firstname": user.firstname,
                            "lastname": user.lastname,
                            "avatarUrl": user.avatar.url if user.avatar else None,
                        },
                    },
                },
            },
        )

    async def _handle_delete_reply(self, payload):
        serializer = CommentReplyDeleteSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        user_id = int(serializer.validated_data["user_id"])
        comment_id = int(serializer.validated_data["comment_id"])
        reply_id = int(serializer.validated_data["reply_id"])
        user = await database_sync_to_async(AuthService.get_user)(user_id)

        try:
            reply = await database_sync_to_async(CommentReply.objects.select_related("comment").get)(pk=reply_id)
        except CommentReply.DoesNotExist:
            return
        if reply.comment.article_id != self.article_pk:
            return

        if reply.comment_id != comment_id:
            return
        if reply.user_id != user.id:
            return

        deleted_reply_id = str(reply.id)
        parent_comment_id = reply.comment_id
        await database_sync_to_async(reply.delete)()

        latest_comment = await database_sync_to_async(Comments.objects.get)(pk=parent_comment_id)
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "comment.message",
                "payload": {
                    "eventType": "article_comment_reply_deleted",
                    "commentId": str(latest_comment.id),
                    "replyCount": latest_comment.reply_count,
                    "repliedByUserId": str(user.id),
                    "deletedReplyId": deleted_reply_id,
                    "deleted": True,
                },
            },
        )

    async def comment_message(self, event):
        await self.send_json(event["payload"])
