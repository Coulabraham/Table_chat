from rest_framework import serializers

from accounts.serializers import PublicUserSerializer
from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    author_id = serializers.IntegerField(read_only=True)
    server_sequence = serializers.IntegerField(source="id", read_only=True)

    class Meta:
        model = Message
        fields = ("id", "server_sequence", "conversation_id", "author_id", "client_id", "content", "created_at")
        read_only_fields = fields


class ConversationSerializer(serializers.ModelSerializer):
    other_user = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ("id", "other_user", "last_message", "updated_at", "created_at")

    def get_other_user(self, obj):
        return PublicUserSerializer(obj.other_user(self.context["request"].user)).data

    def get_last_message(self, obj):
        message = obj.messages.order_by("-id").first()
        return MessageSerializer(message).data if message else None


class CreateMessageSerializer(serializers.Serializer):
    client_id = serializers.UUIDField()
    content = serializers.CharField(max_length=4000, trim_whitespace=False)

    def validate_content(self, value):
        if not value.strip():
            raise serializers.ValidationError("Le message ne peut pas être vide.")
        return value


class CreateConversationSerializer(serializers.Serializer):
    contact_public_id = serializers.CharField(max_length=32)

