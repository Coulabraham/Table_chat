from rest_framework import serializers
from accounts.serializers import UserSerializer
from .models import Conversation, ConversationParticipant, Message


class MessageSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ("id", "author", "content", "client_id", "created_at")
        read_only_fields = ("id", "created_at")


class ConversationSerializer(serializers.ModelSerializer):
    participants = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ("id", "kind", "game_id", "participants", "unread_count", "created_at")

    def get_participants(self, obj):
        return UserSerializer([item.user for item in obj.memberships.all()], many=True).data

    def get_unread_count(self, obj):
        request = self.context.get("request")
        membership = next((item for item in obj.memberships.all() if request and item.user_id == request.user.id), None)
        messages = obj.messages.exclude(author=request.user) if request else obj.messages.none()
        return messages.filter(created_at__gt=membership.last_read_at).count() if membership and membership.last_read_at else messages.count()

