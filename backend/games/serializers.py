from rest_framework import serializers
from accounts.models import User
from accounts.serializers import UserSerializer
from .models import Game, GameInvitation, GameParticipant


class ParticipantSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = GameParticipant
        fields = ("user", "role")


class GameSerializer(serializers.ModelSerializer):
    participants = ParticipantSerializer(many=True, read_only=True)
    conversation_id = serializers.SerializerMethodField()

    class Meta:
        model = Game
        fields = ("id", "game_type", "mode", "status", "configuration", "result", "end_reason", "participants", "conversation_id", "created_at", "started_at", "finished_at")

    def get_conversation_id(self, obj):
        try:
            return obj.conversation.id
        except Exception:
            return None


class InvitationSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    recipient = UserSerializer(read_only=True)
    recipient_id = serializers.PrimaryKeyRelatedField(source="recipient", queryset=User.objects.all(), write_only=True)
    game_id = serializers.UUIDField(source="game.id", read_only=True)

    class Meta:
        model = GameInvitation
        fields = ("id", "sender", "recipient", "recipient_id", "configuration", "status", "expires_at", "game_id", "created_at")
        read_only_fields = ("status", "expires_at")

    def create(self, validated_data):
        validated_data["sender"] = self.context["request"].user
        return super().create(validated_data)
