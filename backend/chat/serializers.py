from rest_framework import serializers

from accounts.serializers import PublicUserSerializer
from .models import Conversation, ConversationMembership, GroupInvitation, Message


class MessageSerializer(serializers.ModelSerializer):
    author_id = serializers.IntegerField(read_only=True)
    author = PublicUserSerializer(read_only=True)
    server_sequence = serializers.IntegerField(source="id", read_only=True)

    class Meta:
        model = Message
        fields = (
            "id",
            "server_sequence",
            "conversation_id",
            "author_id",
            "author",
            "client_id",
            "content",
            "created_at",
        )
        read_only_fields = fields


class ConversationSerializer(serializers.ModelSerializer):
    other_user = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    blocked_by_me = serializers.SerializerMethodField()
    owner = PublicUserSerializer(read_only=True)
    my_role = serializers.SerializerMethodField()
    muted = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = (
            "id",
            "kind",
            "name",
            "description",
            "owner",
            "other_user",
            "last_message",
            "blocked_by_me",
            "my_role",
            "muted",
            "member_count",
            "unread_count",
            "updated_at",
            "created_at",
        )

    def _membership(self, obj):
        if not hasattr(obj, "_request_membership"):
            obj._request_membership = obj.memberships.filter(
                user=self.context["request"].user, left_at__isnull=True
            ).first()
        return obj._request_membership

    def _visible_messages(self, obj):
        membership = self._membership(obj)
        if not membership:
            return obj.messages.none()
        return obj.messages.filter(id__gt=membership.joined_after_message_id)

    def get_other_user(self, obj):
        other = obj.other_user(self.context["request"].user)
        return PublicUserSerializer(other).data if other else None

    def get_last_message(self, obj):
        message = self._visible_messages(obj).select_related("author").order_by("-id").first()
        return MessageSerializer(message).data if message else None

    def get_blocked_by_me(self, obj):
        if obj.kind != Conversation.Kind.PRIVATE:
            return False
        user = self.context["request"].user
        return user.blocks_created.filter(blocked=obj.other_user(user)).exists()

    def get_my_role(self, obj):
        membership = self._membership(obj)
        return membership.role if membership else None

    def get_muted(self, obj):
        membership = self._membership(obj)
        return membership.muted if membership else False

    def get_member_count(self, obj):
        return obj.memberships.filter(left_at__isnull=True).count()

    def get_unread_count(self, obj):
        membership = self._membership(obj)
        if not membership:
            return 0
        cursor = max(membership.joined_after_message_id, membership.last_read_message_id or 0)
        return obj.messages.filter(id__gt=cursor).exclude(author=self.context["request"].user).count()


class MembershipSerializer(serializers.ModelSerializer):
    user = PublicUserSerializer(read_only=True)

    class Meta:
        model = ConversationMembership
        fields = ("id", "user", "role", "joined_at")
        read_only_fields = fields


class GroupInvitationSerializer(serializers.ModelSerializer):
    conversation = serializers.SerializerMethodField()
    inviter = PublicUserSerializer(read_only=True)
    invitee = PublicUserSerializer(read_only=True)

    class Meta:
        model = GroupInvitation
        fields = (
            "id",
            "conversation",
            "inviter",
            "invitee",
            "status",
            "created_at",
            "expires_at",
            "responded_at",
        )
        read_only_fields = fields

    def get_conversation(self, obj):
        return {"id": str(obj.conversation_id), "name": obj.conversation.name}


class CreateMessageSerializer(serializers.Serializer):
    client_id = serializers.UUIDField()
    content = serializers.CharField(max_length=4000, trim_whitespace=False)

    def validate_content(self, value):
        if not value.strip():
            raise serializers.ValidationError("Le message ne peut pas être vide.")
        return value


class CreateConversationSerializer(serializers.Serializer):
    contact_public_id = serializers.CharField(max_length=32)


class CreateGroupSerializer(serializers.Serializer):
    name = serializers.CharField(min_length=1, max_length=80)
    description = serializers.CharField(max_length=500, allow_blank=True, required=False, default="")

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Le nom du groupe ne peut pas être vide.")
        return value


class UpdateGroupSerializer(serializers.Serializer):
    name = serializers.CharField(min_length=1, max_length=80, required=False)
    description = serializers.CharField(max_length=500, allow_blank=True, required=False)

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Le nom du groupe ne peut pas être vide.")
        return value


class CreateInvitationSerializer(serializers.Serializer):
    public_id = serializers.CharField(max_length=32)


class UpdateRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=(ConversationMembership.Role.ADMIN, ConversationMembership.Role.MEMBER))


class TransferOwnerSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)


class LeaveGroupSerializer(serializers.Serializer):
    confirm_archive = serializers.BooleanField(default=False)


class ReadCursorSerializer(serializers.Serializer):
    message_id = serializers.IntegerField(min_value=1)


class ConversationPreferencesSerializer(serializers.Serializer):
    muted = serializers.BooleanField()
