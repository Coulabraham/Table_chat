import re

from django.contrib.auth import authenticate, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import User

PUBLIC_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{2,31}$")


class PublicUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "public_id", "display_name", "bio")


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "public_id", "display_name", "bio")
        read_only_fields = ("id", "email", "public_id")


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
