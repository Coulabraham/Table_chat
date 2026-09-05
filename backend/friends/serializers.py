from rest_framework import serializers
from accounts.serializers import UserSerializer
from accounts.models import User
from .models import Friendship


class FriendshipSerializer(serializers.ModelSerializer):
    requester = UserSerializer(read_only=True)
    addressee = UserSerializer(read_only=True)
    addressee_id = serializers.PrimaryKeyRelatedField(source="addressee", queryset=User.objects.all(), write_only=True)

    class Meta:
        model = Friendship
        fields = ("id", "requester", "addressee", "addressee_id", "status", "created_at")
        read_only_fields = ("status",)

    def create(self, validated_data):
        validated_data["requester"] = self.context["request"].user
        return super().create(validated_data)

