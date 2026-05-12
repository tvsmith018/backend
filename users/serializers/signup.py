import logging

from cloudinary.exceptions import BadRequest
from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()
logger = logging.getLogger(__name__)


def _rewind_upload(f):
    """Reset file pointer so Cloudinary uploads full bytes (EOF → 'Invalid image file')."""
    if f is None or not hasattr(f, "seek"):
        return
    try:
        if getattr(f, "seekable", lambda: True)():
            f.seek(0)
    except OSError:
        pass


def _avatar_signature(upload):
    """Return non-sensitive upload metadata to debug intermittent invalid image bytes."""
    if upload is None:
        return {}
    signature = {}
    try:
        _rewind_upload(upload)
        head = upload.read(12) if hasattr(upload, "read") else b""
        _rewind_upload(upload)
        signature = {
            "name": getattr(upload, "name", None),
            "size": getattr(upload, "size", None),
            "content_type": getattr(upload, "content_type", None),
            "py_type": upload.__class__.__name__,
            "head_hex": head.hex() if isinstance(head, (bytes, bytearray)) else None,
        }
    except Exception:
        # Avoid breaking signup if diagnostics fail.
        logger.exception("Failed to read avatar signature for diagnostics")
    return signature


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    # FileField (not ImageField): Pillow rejects some valid uploads Cloudinary accepts (HEIC, etc.).
    avatar = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ["email", "firstname", "lastname", "dob", "avatar", "password"]

    def validate_avatar(self, value):
        if value in (None, ""):
            return None
        if getattr(value, "size", None) == 0:
            return None
        _rewind_upload(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        avatar = validated_data.pop("avatar", None)
        user = User(**validated_data)
        user.set_password(password)
        user.bio = "Please let the world know who you are!"
        # Source-of-truth note:
        # user.avatar write here is mirrored into profiles_profileimage by profiles.signals
        # and marked featured so ProfileImage remains the canonical image source.
        # Set file before first save() so CloudinaryField.pre_save() uploads on that save.
        # save(update_fields=["avatar"]) after a prior save() can skip Cloudinary's upload path.
        if avatar is not None:
            logger.info(
                "Signup avatar diagnostics email=%s signature=%s",
                getattr(user, "email", None),
                _avatar_signature(avatar),
            )
            _rewind_upload(avatar)
            user.avatar = avatar
        try:
            user.save()
        except BadRequest as exc:
            logger.warning(
                "Signup avatar rejected by Cloudinary for email=%s: %s",
                getattr(user, "email", None),
                exc,
            )
            if avatar is not None:
                user.avatar = None
                user.save(update_fields=["avatar"])
        except Exception:
            logger.exception(
                "Signup avatar upload failed for email=%s",
                getattr(user, "email", None),
            )
            if avatar is not None:
                user.avatar = None
                user.save(update_fields=["avatar"])
        return user
