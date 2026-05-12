from rest_framework import serializers

class OTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp_type = serializers.ChoiceField(
        choices=["signup", "password-reset"]
    )