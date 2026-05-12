import json

from channels.db import database_sync_to_async
from rest_framework import serializers
from graphql_relay import from_global_id

from common.consumers.base import BaseCommentConsumer
from common.mixins.article import ArticleMixin
from profiles.models import ProfilePost, ProfilePostLike, ProfilePostReply, ProfilePostShare
from users.services.auth_service import AuthService


class ProfilePostCreateSerializer(serializers.Serializer):
    action = serializers.CharField(required=False, default="create_post")
    body = serializers.CharField(max_length=4000, required=False, allow_blank=True, allow_null=True)
    user_id = serializers.CharField(max_length=2000)
    article_id = serializers.CharField(max_length=2000, required=False, allow_blank=True, allow_null=True)
    image_data = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    metadata = serializers.JSONField(required=False)

    def validate(self, attrs):
        body = (attrs.get("body") or "").strip()
        image_data = attrs.get("image_data")
        if not body and not image_data:
            raise serializers.ValidationError("Post body or image is required.")
        attrs["body"] = body
        return attrs


class ProfilePostLikeSerializer(serializers.Serializer):
    action = serializers.CharField(required=False, default="like_post")
    post_id = serializers.CharField(max_length=2000)
    user_id = serializers.CharField(max_length=2000)

    def validate_post_id(self, value):
        raw = (value or "").strip()
        if raw.isdigit():
            return int(raw)
        try:
            _, decoded_id = from_global_id(raw)
            return int(decoded_id)
        except Exception as exc:
            raise serializers.ValidationError("Invalid post id.") from exc


class ProfilePostDeleteSerializer(serializers.Serializer):
    action = serializers.CharField(required=False, default="delete_post")
    post_id = serializers.CharField(max_length=2000)
    user_id = serializers.CharField(max_length=2000)

    def validate_post_id(self, value):
        raw = (value or "").strip()
        if raw.isdigit():
            return int(raw)
        try:
            _, decoded_id = from_global_id(raw)
            return int(decoded_id)
        except Exception as exc:
            raise serializers.ValidationError("Invalid post id.") from exc


class ProfilePostShareSerializer(serializers.Serializer):
    action = serializers.CharField(required=False, default="share_post")
    post_id = serializers.CharField(max_length=2000)
    user_id = serializers.CharField(max_length=2000)

    def validate_post_id(self, value):
        raw = (value or "").strip()
        if raw.isdigit():
            return int(raw)
        try:
            _, decoded_id = from_global_id(raw)
            return int(decoded_id)
        except Exception as exc:
            raise serializers.ValidationError("Invalid post id.") from exc


class ProfilePostReplySerializer(serializers.Serializer):
    action = serializers.CharField(required=False, default="reply_post")
    post_id = serializers.CharField(max_length=2000)
    user_id = serializers.CharField(max_length=2000)
    body = serializers.CharField(max_length=2000)

    def validate_post_id(self, value):
        raw = (value or "").strip()
        if raw.isdigit():
            return int(raw)
        try:
            _, decoded_id = from_global_id(raw)
            return int(decoded_id)
        except Exception as exc:
            raise serializers.ValidationError("Invalid post id.") from exc

    def validate_body(self, value):
        body = (value or "").strip()
        if not body:
            raise serializers.ValidationError("Reply body is required.")
        return body


class ProfilePostReplyDeleteSerializer(serializers.Serializer):
    action = serializers.CharField(required=False, default="delete_reply")
    post_id = serializers.CharField(max_length=2000)
    reply_id = serializers.CharField(max_length=2000)
    user_id = serializers.CharField(max_length=2000)

    def validate_post_id(self, value):
        raw = (value or "").strip()
        if raw.isdigit():
            return int(raw)
        try:
            _, decoded_id = from_global_id(raw)
            return int(decoded_id)
        except Exception as exc:
            raise serializers.ValidationError("Invalid post id.") from exc

    def validate_reply_id(self, value):
        raw = (value or "").strip()
        if raw.isdigit():
            return int(raw)
        try:
            _, decoded_id = from_global_id(raw)
            return int(decoded_id)
        except Exception as exc:
            raise serializers.ValidationError("Invalid reply id.") from exc


class ProfilePostConsumer(BaseCommentConsumer, ArticleMixin):
    def _parse_post_id_value(self, value):
        raw = str(value or "").strip()
        if raw.isdigit():
            return int(raw)
        try:
            _, decoded_id = from_global_id(raw)
            return int(decoded_id)
        except Exception:
            return None

    async def _resolve_share_source_post(self, post):
        metadata = post.metadata if isinstance(post.metadata, dict) else {}
        origin_id = self._parse_post_id_value(metadata.get("share_origin_id"))
        if not origin_id or origin_id == post.id:
            return post
        try:
            return await database_sync_to_async(ProfilePost.objects.select_related("user", "article").get)(pk=origin_id)
        except ProfilePost.DoesNotExist:
            return post

    def _serialize_post_payload(self, post, user, uploaded_image=None):
        return {
            "eventType": "profile_post_created",
            "id": str(post.id),
            "body": post.body,
            "status": post.status,
            "likesCount": post.likes_count,
            "shareCount": post.share_count,
            "repliesCount": post.replies_count,
            "postImageUrl": (
                uploaded_image.get("secure_url")
                if uploaded_image
                else (post.post_image.url if post.post_image else None)
            ),
            "metadata": post.metadata,
            "createdAt": post.created_at.isoformat(),
            "updatedAt": post.updated_at.isoformat(),
            "user": {
                "id": str(user.id),
                "firstname": user.firstname,
                "lastname": user.lastname,
                "avatarUrl": user.avatar.url if user.avatar else None,
            },
            "article": (
                {
                    "id": str(post.article.id),
                }
                if post.article
                else None
            ),
        }

    async def connect(self):
        self.group_name = "profile_posts_feed"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        payload = json.loads(text_data)
        action = payload.get("action", "create_post")

        if action == "like_post":
            await self._handle_like(payload)
            return
        if action == "unlike_post":
            await self._handle_unlike(payload)
            return
        if action == "delete_post":
            await self._handle_delete(payload)
            return
        if action == "share_post":
            await self._handle_share(payload)
            return
        if action == "unshare_post":
            await self._handle_unshare(payload)
            return
        if action == "reply_post":
            await self._handle_reply(payload)
            return
        if action == "delete_reply":
            await self._handle_delete_reply(payload)
            return

        await self._handle_create(payload)

    async def _handle_create(self, payload):
        serializer = ProfilePostCreateSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        user_id = int(serializer.validated_data["user_id"])
        user = await database_sync_to_async(AuthService.get_user)(user_id)

        article = None
        article_id = serializer.validated_data.get("article_id")
        if article_id:
            article = await self.get_article(article_id)

        post = await database_sync_to_async(ProfilePost.objects.create)(
            user=user,
            article=article,
            body=serializer.validated_data["body"],
            metadata=serializer.validated_data.get("metadata", {}),
        )

        uploaded_image = None
        image_data = serializer.validated_data.get("image_data")
        if image_data:
            uploaded_image = await database_sync_to_async(post.upload_post_image)(image_data)

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "profile.post.message",
                "post": self._serialize_post_payload(post, user, uploaded_image),
            },
        )

    async def _handle_like(self, payload):
        serializer = ProfilePostLikeSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        user_id = int(serializer.validated_data["user_id"])
        post_id = int(serializer.validated_data["post_id"])
        user = await database_sync_to_async(AuthService.get_user)(user_id)
        post = await database_sync_to_async(ProfilePost.objects.select_related("user", "article").get)(pk=post_id)

        _, created = await database_sync_to_async(ProfilePostLike.objects.get_or_create)(
            post=post,
            user=user,
        )

        latest_post = await database_sync_to_async(ProfilePost.objects.get)(pk=post.pk)

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "profile.like.message",
                "payload": {
                    "eventType": "profile_post_liked",
                    "postId": str(latest_post.id),
                    "likesCount": latest_post.likes_count,
                    "likedByUserId": str(user.id),
                    "created": created,
                },
            },
        )

    async def _handle_unlike(self, payload):
        serializer = ProfilePostLikeSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        user_id = int(serializer.validated_data["user_id"])
        post_id = int(serializer.validated_data["post_id"])
        user = await database_sync_to_async(AuthService.get_user)(user_id)
        post = await database_sync_to_async(ProfilePost.objects.get)(pk=post_id)

        deleted_count, _ = await database_sync_to_async(
            ProfilePostLike.objects.filter(post=post, user=user).delete
        )()
        deleted = deleted_count > 0

        latest_post = await database_sync_to_async(ProfilePost.objects.get)(pk=post.pk)

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "profile.like.message",
                "payload": {
                    "eventType": "profile_post_unliked",
                    "postId": str(latest_post.id),
                    "likesCount": latest_post.likes_count,
                    "likedByUserId": str(user.id),
                    "created": False,
                    "deleted": deleted,
                },
            },
        )

    async def _handle_delete(self, payload):
        serializer = ProfilePostDeleteSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        user_id = int(serializer.validated_data["user_id"])
        post_id = int(serializer.validated_data["post_id"])
        user = await database_sync_to_async(AuthService.get_user)(user_id)
        post = await database_sync_to_async(ProfilePost.objects.get)(pk=post_id)

        metadata = post.metadata if isinstance(post.metadata, dict) else {}
        if not metadata and isinstance(post.metadata, str):
            try:
                parsed = json.loads(post.metadata)
                if isinstance(parsed, dict):
                    metadata = parsed
            except Exception:
                metadata = {}
        share_origin_raw = metadata.get("share_origin_id")
        share_origin_id = self._parse_post_id_value(share_origin_raw)
        source_post = None
        if share_origin_id:
            try:
                source_post = await database_sync_to_async(ProfilePost.objects.get)(pk=share_origin_id)
            except ProfilePost.DoesNotExist:
                source_post = None

        if post.user_id != user.id:
            return

        deleted_post_id = str(post.id)
        await database_sync_to_async(post.delete)()

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "profile.post.message",
                "post": {
                    "eventType": "profile_post_deleted",
                    "id": deleted_post_id,
                    "deletedByUserId": str(user.id),
                },
            },
        )

        if source_post:
            deleted_count, _ = await database_sync_to_async(
                ProfilePostShare.objects.filter(post=source_post, user=user).delete
            )()
            latest_source_post = await database_sync_to_async(ProfilePost.objects.get)(pk=source_post.pk)
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "profile.share.message",
                    "payload": {
                        "eventType": "profile_post_unshared",
                        "postId": str(latest_source_post.id),
                        "shareCount": latest_source_post.share_count,
                        "sharedByUserId": str(user.id),
                        "created": False,
                        "deleted": deleted_count > 0,
                    },
                },
            )

    async def _handle_share(self, payload):
        serializer = ProfilePostShareSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        user_id = int(serializer.validated_data["user_id"])
        post_id = int(serializer.validated_data["post_id"])
        user = await database_sync_to_async(AuthService.get_user)(user_id)
        post = await database_sync_to_async(ProfilePost.objects.select_related("user", "article").get)(pk=post_id)
        source_post = await self._resolve_share_source_post(post)

        if source_post.user_id == user.id:
            return

        _, created = await database_sync_to_async(ProfilePostShare.objects.get_or_create)(
            post=source_post,
            user=user,
        )

        latest_post = await database_sync_to_async(ProfilePost.objects.get)(pk=source_post.pk)

        if created:
            share_snapshot = {
                "id": str(source_post.id),
                "body": source_post.body,
                "postImageUrl": source_post.post_image.url if source_post.post_image else None,
                "shareCount": latest_post.share_count,
                "createdAt": source_post.created_at.isoformat(),
                "user": {
                    "id": str(source_post.user_id),
                    "firstname": source_post.user.firstname,
                    "lastname": source_post.user.lastname,
                    "avatarUrl": source_post.user.avatar.url if source_post.user.avatar else None,
                },
            }
            shared_post = await database_sync_to_async(ProfilePost.objects.create)(
                user=user,
                article=source_post.article,
                body="",
                metadata={
                    "share_origin_id": str(source_post.id),
                    "share_origin_snapshot": share_snapshot,
                    "is_share_post": True,
                },
            )
            latest_shared_post = await database_sync_to_async(ProfilePost.objects.select_related("user", "article").get)(
                pk=shared_post.pk
            )
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "profile.post.message",
                    "post": self._serialize_post_payload(latest_shared_post, user),
                },
            )

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "profile.share.message",
                "payload": {
                    "eventType": "profile_post_shared",
                    "postId": str(latest_post.id),
                    "shareCount": latest_post.share_count,
                    "sharedByUserId": str(user.id),
                    "created": created,
                },
            },
        )

    async def _handle_unshare(self, payload):
        serializer = ProfilePostShareSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        user_id = int(serializer.validated_data["user_id"])
        post_id = int(serializer.validated_data["post_id"])
        user = await database_sync_to_async(AuthService.get_user)(user_id)
        post = await database_sync_to_async(ProfilePost.objects.select_related("user", "article").get)(pk=post_id)
        source_post = await self._resolve_share_source_post(post)

        deleted_count, _ = await database_sync_to_async(
            ProfilePostShare.objects.filter(post=source_post, user=user).delete
        )()
        deleted = deleted_count > 0

        latest_post = await database_sync_to_async(ProfilePost.objects.get)(pk=source_post.pk)

        if deleted:
            share_posts = await database_sync_to_async(list)(
                ProfilePost.objects.filter(
                    user_id=user.id,
                    metadata__share_origin_id=str(source_post.id),
                )
            )
            for share_post in share_posts:
                deleted_post_id = str(share_post.id)
                await database_sync_to_async(share_post.delete)()
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "profile.post.message",
                        "post": {
                            "eventType": "profile_post_deleted",
                            "id": deleted_post_id,
                            "deletedByUserId": str(user.id),
                        },
                    },
                )

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "profile.share.message",
                "payload": {
                    "eventType": "profile_post_unshared",
                    "postId": str(latest_post.id),
                    "shareCount": latest_post.share_count,
                    "sharedByUserId": str(user.id),
                    "created": False,
                    "deleted": deleted,
                },
            },
        )

    async def _handle_reply(self, payload):
        serializer = ProfilePostReplySerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        user_id = int(serializer.validated_data["user_id"])
        post_id = int(serializer.validated_data["post_id"])
        user = await database_sync_to_async(AuthService.get_user)(user_id)
        post = await database_sync_to_async(ProfilePost.objects.get)(pk=post_id)

        reply = await database_sync_to_async(ProfilePostReply.objects.create)(
            post=post,
            user=user,
            body=serializer.validated_data["body"],
        )

        latest_post = await database_sync_to_async(ProfilePost.objects.get)(pk=post.pk)
        latest_reply = await database_sync_to_async(ProfilePostReply.objects.select_related("user").get)(
            pk=reply.pk
        )

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "profile.reply.message",
                "payload": {
                    "eventType": "profile_post_replied",
                    "postId": str(latest_post.id),
                    "repliesCount": latest_post.replies_count,
                    "repliedByUserId": str(user.id),
                    "reply": {
                        "id": str(latest_reply.id),
                        "body": latest_reply.body,
                        "createdAt": latest_reply.created_at.isoformat(),
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
        serializer = ProfilePostReplyDeleteSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        user_id = int(serializer.validated_data["user_id"])
        post_id = int(serializer.validated_data["post_id"])
        reply_id = int(serializer.validated_data["reply_id"])
        user = await database_sync_to_async(AuthService.get_user)(user_id)

        try:
            reply = await database_sync_to_async(ProfilePostReply.objects.select_related("post").get)(pk=reply_id)
        except ProfilePostReply.DoesNotExist:
            return

        if reply.post_id != post_id:
            return
        if reply.user_id != user.id:
            return

        deleted_reply_id = str(reply.id)
        parent_post_id = reply.post_id
        await database_sync_to_async(reply.delete)()

        latest_post = await database_sync_to_async(ProfilePost.objects.get)(pk=parent_post_id)
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "profile.reply.message",
                "payload": {
                    "eventType": "profile_post_reply_deleted",
                    "postId": str(latest_post.id),
                    "repliesCount": latest_post.replies_count,
                    "repliedByUserId": str(user.id),
                    "deletedReplyId": deleted_reply_id,
                    "deleted": True,
                },
            },
        )

    async def profile_post_message(self, event):
        await self.send_json(event["post"])

    async def profile_like_message(self, event):
        await self.send_json(event["payload"])

    async def profile_share_message(self, event):
        await self.send_json(event["payload"])

    async def profile_reply_message(self, event):
        await self.send_json(event["payload"])
