"""Shared OpenAPI schema fragments for drf-spectacular (documentation only; no runtime effect)."""

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

EnvelopeSuccess = inline_serializer(
    name="EnvelopeSuccess",
    fields={
        "success": serializers.BooleanField(),
        "data": serializers.JSONField(allow_null=True),
    },
)

EnvelopeError = inline_serializer(
    name="EnvelopeError",
    fields={
        "success": serializers.BooleanField(),
        "message": serializers.CharField(allow_blank=True),
    },
)
