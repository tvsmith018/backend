import json

from channels.db import database_sync_to_async
from rest_framework import serializers
from graphql_relay import from_global_id

from common.consumers.base import BaseCommentConsumer
from profiles.models import ProfileFollow
from users.services.auth_service import AuthService


class ProfileFollowActionSerializer(serializers.Serializer):
    action = serializers.CharField(required=False, default="follow_user")
    user_id = serializers.CharField(max_length=2000)
    following_user_id = serializers.CharField(max_length=2000)

    def validate_user_id(self, value):
        raw = (value or "").strip()
        if raw.isdigit():
            return int(raw)
        try:
            _, decoded_id = from_global_id(raw)
            return int(decoded_id)
        except Exception as exc:
            raise serializers.ValidationError("Invalid user id.") from exc

    def validate_following_user_id(self, value):
        raw = (value or "").strip()
        if raw.isdigit():
            return int(raw)
        try:
            _, decoded_id = from_global_id(raw)
            return int(decoded_id)
        except Exception as exc:
            raise serializers.ValidationError("Invalid following user id.") from exc


class ProfileFollowConsumer(BaseCommentConsumer):
    async def connect(self):
        self.group_name = "profile_follows_feed"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        payload = json.loads(text_data)
        action = payload.get("action", "follow_user")

        if action == "unfollow_user":
            await self._handle_unfollow(payload)
            return
        await self._handle_follow(payload)

    async def _handle_follow(self, payload):
        serializer = ProfileFollowActionSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        follower_id = int(serializer.validated_data["user_id"])
        following_id = int(serializer.validated_data["following_user_id"])
        if follower_id == following_id:
            return

        follower = await database_sync_to_async(AuthService.get_user)(follower_id)
        following = await database_sync_to_async(AuthService.get_user)(following_id)

        relation, created = await database_sync_to_async(ProfileFollow.objects.get_or_create)(
            follower=follower,
            following=following,
            defaults={"status": ProfileFollow.Status.ACTIVE},
        )
        if not created and relation.status != ProfileFollow.Status.ACTIVE:
            relation.status = ProfileFollow.Status.ACTIVE
            await database_sync_to_async(relation.save)(update_fields=["status", "updated_at"])

        reciprocal_exists = await database_sync_to_async(
            ProfileFollow.objects.filter(
                follower_id=following_id,
                following_id=follower_id,
                status=ProfileFollow.Status.ACTIVE,
            ).exists
        )()

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "profile.follow.message",
                "payload": {
                    "eventType": "profile_user_followed",
                    "action": "follow_user",
                    "actorUserId": str(follower_id),
                    "targetUserId": str(following_id),
                    "viewerFollowsTarget": True,
                    "targetFollowsViewer": reciprocal_exists,
                    "created": created,
                },
            },
        )

    async def _handle_unfollow(self, payload):
        serializer = ProfileFollowActionSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        follower_id = int(serializer.validated_data["user_id"])
        following_id = int(serializer.validated_data["following_user_id"])
        if follower_id == following_id:
            return

        await database_sync_to_async(AuthService.get_user)(follower_id)
        await database_sync_to_async(AuthService.get_user)(following_id)

        deleted_count, _ = await database_sync_to_async(
            ProfileFollow.objects.filter(
                follower_id=follower_id,
                following_id=following_id,
                status=ProfileFollow.Status.ACTIVE,
            ).delete
        )()
        deleted = deleted_count > 0

        reciprocal_exists = await database_sync_to_async(
            ProfileFollow.objects.filter(
                follower_id=following_id,
                following_id=follower_id,
                status=ProfileFollow.Status.ACTIVE,
            ).exists
        )()

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "profile.follow.message",
                "payload": {
                    "eventType": "profile_user_unfollowed",
                    "action": "unfollow_user",
                    "actorUserId": str(follower_id),
                    "targetUserId": str(following_id),
                    "viewerFollowsTarget": False,
                    "targetFollowsViewer": reciprocal_exists,
                    "deleted": deleted,
                },
            },
        )

    async def profile_follow_message(self, event):
        await self.send_json(event["payload"])
