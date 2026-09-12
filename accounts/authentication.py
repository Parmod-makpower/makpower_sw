from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed


class CustomJWTAuthentication(JWTAuthentication):

    def get_user(self, validated_token):
        user = super().get_user(validated_token)

        # -----------------------------------------
        # 1. ACCOUNT ACTIVE CHECK
        # -----------------------------------------
        if not user.is_active:
            raise AuthenticationFailed(
                "Account is deactivated.",
                code="user_inactive"
            )

        # -----------------------------------------
        # 2. AUTH VERSION CHECK
        # -----------------------------------------
        token_auth_version = validated_token.get("auth_version")

        if token_auth_version is None:
            raise AuthenticationFailed(
                "Session is no longer valid. Please login again.",
                code="session_invalid"
            )

        # -----------------------------------------
        # 3. OLD TOKEN CHECK
        # -----------------------------------------
        if int(token_auth_version) != user.auth_version:
            raise AuthenticationFailed(
                "Session is no longer valid. Please login again.",
                code="session_invalid"
            )

        return user