import json

from channels.db import database_sync_to_async
from rest_framework import serializers

from common.consumers.base import BaseCommentConsumer
from profiles.models import UserProfileSettings
from users.services.auth_service import AuthService


class ProfileSettingsUpdateSerializer(serializers.Serializer):
    action = serializers.CharField(required=False, default="update_profile_settings")
    user_id = serializers.CharField(max_length=2000)
    settings = serializers.DictField(child=serializers.BooleanField(), required=False, default=dict)


class ProfileSettingsSnapshotSerializer(serializers.Serializer):
    action = serializers.CharField(required=False, default="request_profile_settings")
    user_id = serializers.CharField(max_length=2000)


class ProfileSettingsConsumer(BaseCommentConsumer):
    group_name = "profile_settings_feed"

    async def connect(self):
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    def _serialize_settings(self, settings: UserProfileSettings):
        return {
            "profile_is_public": settings.profile_is_public,
            "allow_messages": settings.allow_messages,
            "show_activity_feed": settings.show_activity_feed,
            "show_watch_history": settings.show_watch_history,
            "show_ratings": settings.show_ratings,
            "show_uploaded_images": settings.show_uploaded_images,
            "receive_notifications": settings.receive_notifications,
            "receive_marketing_notifications": settings.receive_marketing_notifications,
            "disabled_at": settings.disabled_at.isoformat() if settings.disabled_at else None,
            "delete_requested_at": settings.delete_requested_at.isoformat() if settings.delete_requested_at else None,
            "metadata": settings.metadata or {},
            "updated_at": settings.updated_at.isoformat() if settings.updated_at else None,
        }

    @database_sync_to_async
    def _get_or_create_settings(self, user_id: int):
        user = AuthService.get_user(user_id)
        settings, _ = UserProfileSettings.objects.get_or_create(user=user)
        return settings

    @database_sync_to_async
    def _apply_settings(self, user_id: int, updates: dict):
        user = AuthService.get_user(user_id)
        settings, _ = UserProfileSettings.objects.get_or_create(user=user)

        allowed_fields = {
            "profile_is_public",
            "allow_messages",
            "show_activity_feed",
            "show_watch_history",
            "show_ratings",
            "show_uploaded_images",
            "receive_notifications",
            "receive_marketing_notifications",
        }
        update_fields = []
        for field, value in updates.items():
            if field not in allowed_fields:
                continue
            next_value = bool(value)
            if getattr(settings, field) == next_value:
                continue
            setattr(settings, field, next_value)
            update_fields.append(field)

        if update_fields:
            update_fields.append("updated_at")
            settings.save(update_fields=update_fields)
        return settings

    async def receive(self, text_data):
        payload = json.loads(text_data or "{}")
        action = payload.get("action", "request_profile_settings")

        if action == "update_profile_settings":
            await self._handle_update(payload)
            return
        await self._handle_snapshot(payload)

    async def _handle_snapshot(self, payload):
        serializer = ProfileSettingsSnapshotSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        user_id = int(serializer.validated_data["user_id"])
        settings = await self._get_or_create_settings(user_id)
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "profile.settings.message",
                "payload": {
                    "eventType": "profile_settings_snapshot",
                    "userId": str(user_id),
                    "settings": self._serialize_settings(settings),
                },
            },
        )

    async def _handle_update(self, payload):
        serializer = ProfileSettingsUpdateSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        user_id = int(serializer.validated_data["user_id"])
        updates = serializer.validated_data.get("settings", {})
        settings = await self._apply_settings(user_id, updates)
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "profile.settings.message",
                "payload": {
                    "eventType": "profile_settings_updated",
                    "userId": str(user_id),
                    "settings": self._serialize_settings(settings),
                },
            },
        )

    async def profile_settings_message(self, event):
        await self.send_json(event["payload"])
