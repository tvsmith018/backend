from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class UserTokenObtainPairSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["firstname"] = user.firstname
        token["lastname"] = user.lastname
        token["context"] = (
            f"Authorized for {user.firstname} {user.lastname}"
        )
        return token