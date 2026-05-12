from rest_framework import serializers
from graphql_relay import from_global_id

class CommentCreateSerializer(serializers.Serializer):
    action = serializers.CharField(required=False, default="create_comment")
    body = serializers.CharField(max_length=2000)
    user_id = serializers.CharField(max_length=2000)


class CommentLikeSerializer(serializers.Serializer):
    action = serializers.CharField(required=False, default="like_comment")
    comment_id = serializers.CharField(max_length=2000)
    user_id = serializers.CharField(max_length=2000)

    def validate_comment_id(self, value):
        raw = (value or "").strip()
        if raw.isdigit():
            return int(raw)
        try:
            _, decoded_id = from_global_id(raw)
            return int(decoded_id)
        except Exception as exc:
            raise serializers.ValidationError("Invalid comment id.") from exc


class CommentDeleteSerializer(serializers.Serializer):
    action = serializers.CharField(required=False, default="delete_comment")
    comment_id = serializers.CharField(max_length=2000)
    user_id = serializers.CharField(max_length=2000)

    def validate_comment_id(self, value):
        raw = (value or "").strip()
        if raw.isdigit():
            return int(raw)
        try:
            _, decoded_id = from_global_id(raw)
            return int(decoded_id)
        except Exception as exc:
            raise serializers.ValidationError("Invalid comment id.") from exc


class CommentReplySerializer(serializers.Serializer):
    action = serializers.CharField(required=False, default="reply_comment")
    comment_id = serializers.CharField(max_length=2000)
    user_id = serializers.CharField(max_length=2000)
    body = serializers.CharField(max_length=2000)

    def validate_comment_id(self, value):
        raw = (value or "").strip()
        if raw.isdigit():
            return int(raw)
        try:
            _, decoded_id = from_global_id(raw)
            return int(decoded_id)
        except Exception as exc:
            raise serializers.ValidationError("Invalid comment id.") from exc

    def validate_body(self, value):
        body = (value or "").strip()
        if not body:
            raise serializers.ValidationError("Reply body is required.")
        return body


class CommentReplyDeleteSerializer(serializers.Serializer):
    action = serializers.CharField(required=False, default="delete_comment_reply")
    comment_id = serializers.CharField(max_length=2000)
    reply_id = serializers.CharField(max_length=2000)
    user_id = serializers.CharField(max_length=2000)

    def validate_comment_id(self, value):
        raw = (value or "").strip()
        if raw.isdigit():
            return int(raw)
        try:
            _, decoded_id = from_global_id(raw)
            return int(decoded_id)
        except Exception as exc:
            raise serializers.ValidationError("Invalid comment id.") from exc

    def validate_reply_id(self, value):
        raw = (value or "").strip()
        if raw.isdigit():
            return int(raw)
        try:
            _, decoded_id = from_global_id(raw)
            return int(decoded_id)
        except Exception as exc:
            raise serializers.ValidationError("Invalid reply id.") from exc