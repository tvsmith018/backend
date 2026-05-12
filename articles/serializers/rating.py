from rest_framework import serializers

class RatingSerializer(serializers.Serializer):
    rate = serializers.IntegerField(min_value=1, max_value=5)