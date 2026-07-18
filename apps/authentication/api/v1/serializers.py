from rest_framework import serializers


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)


class PasswordResetRequestSerializer(serializers.Serializer):
    domain = serializers.ChoiceField(choices=["it", "professor", "college"])
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    domain = serializers.ChoiceField(choices=["it", "professor", "college"])
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8, write_only=True)


class EmailVerifySerializer(serializers.Serializer):
    domain = serializers.ChoiceField(choices=["it", "professor", "college"])
    token = serializers.CharField()


class ResendEmailVerifySerializer(serializers.Serializer):
    domain = serializers.ChoiceField(
        choices=["it", "professor", "college"], required=False
    )
    email = serializers.EmailField(required=False)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(min_length=8, write_only=True)


class SessionLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class UserActivationSerializer(serializers.Serializer):
    domain = serializers.ChoiceField(choices=["it", "professor", "college"])
    user_id = serializers.UUIDField()
    action = serializers.ChoiceField(choices=["activate", "suspend", "deactivate"])
