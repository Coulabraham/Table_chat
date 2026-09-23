import re

from django.contrib.auth import authenticate, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .access import email_verification_satisfied
from .models import AccountSession, User, UserBlock

PUBLIC_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{2,31}$")


class PublicUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "public_id", "display_name", "bio")


class MeSerializer(serializers.ModelSerializer):
    email_verified = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "email", "public_id", "display_name", "bio", "email_verified", "email_verified_at")
        read_only_fields = ("id", "email", "public_id", "email_verified", "email_verified_at")

    def get_email_verified(self, obj):
        return email_verification_satisfied(obj)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    class Meta:
        model = User
        fields = ("email", "public_id", "display_name", "password")

    def validate_public_id(self, value):
        value = value.lower()
        if not PUBLIC_ID_RE.fullmatch(value):
            raise serializers.ValidationError("Utilisez 3 à 32 lettres minuscules, chiffres, points, tirets ou underscores.")
        return value

    def validate_password(self, value):
        try:
            password_validation.validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False)

    def validate(self, attrs):
        user = authenticate(request=self.context.get("request"), email=attrs["email"].lower(), password=attrs["password"])
        if user is None or not user.is_active:
            raise serializers.ValidationError("Email ou mot de passe incorrect.")
        attrs["user"] = user
        return attrs


class TokenSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=256, trim_whitespace=False)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(TokenSerializer):
    new_password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)


class AccountSessionSerializer(serializers.ModelSerializer):
    current = serializers.SerializerMethodField()

    class Meta:
        model = AccountSession
        fields = ("id", "description", "ip_address", "created_at", "last_activity_at", "current")

    def get_current(self, obj):
        return obj.session_id == self.context["request"].session.session_key


class UserBlockSerializer(serializers.ModelSerializer):
    user = PublicUserSerializer(source="blocked", read_only=True)

    class Meta:
        model = UserBlock
        fields = ("id", "user", "created_at")


class CreateUserBlockSerializer(serializers.Serializer):
    public_id = serializers.CharField(max_length=32)
