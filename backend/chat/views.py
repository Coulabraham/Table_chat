from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import IsEmailVerified
from .models import Conversation, ConversationMembership, GroupInvitation, Message
from .serializers import (
    ConversationPreferencesSerializer,
    ConversationSerializer,
    CreateConversationSerializer,
    CreateGroupSerializer,
    CreateInvitationSerializer,
    CreateMessageSerializer,
    GroupInvitationSerializer,
    LeaveGroupSerializer,
    MembershipSerializer,
    MessageSerializer,
    ReadCursorSerializer,
    TransferOwnerSerializer,
    UpdateGroupSerializer,
    UpdateRoleSerializer,
)
from .services import (
    GroupActionError,
    MessagingBlockedError,
    active_membership,
    advance_read_cursor,
    cancel_invitation,
    change_member_role,
    create_group,
    create_group_invitation,
    create_message,
    get_or_create_private_conversation,
    leave_group,
    remove_group_member,
    respond_to_invitation,
    transfer_group_ownership,
    update_group,
)
from .throttles import GroupCreateRateThrottle, GroupInviteRateThrottle, MessageRateThrottle


def user_conversations(user):
    return Conversation.objects.select_related("user_low", "user_high", "owner").filter(
        memberships__user=user,
        memberships__left_at__isnull=True,
        archived_at__isnull=True,
    ).distinct()


def accessible_conversation_or_404(user, conversation_id):
    return get_object_or_404(user_conversations(user), pk=conversation_id)


def action_error(exc, http_status=status.HTTP_400_BAD_REQUEST):
    return Response({"error": {"status": http_status, "details": str(exc)}}, status=http_status)


class ConversationListCreateView(APIView):
    permission_classes = [IsEmailVerified]

    def get(self, request):
        conversations = user_conversations(request.user).order_by("-updated_at")[:100]
        return Response(ConversationSerializer(conversations, many=True, context={"request": request}).data)

    def post(self, request):
        serializer = CreateConversationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contact = get_object_or_404(
            User, public_id=serializer.validated_data["contact_public_id"].lower(), is_active=True
        )
        if contact.pk == request.user.pk:
            return Response(
                {"error": {"status": 400, "details": "Impossible de discuter avec vous-même."}}, status=400
            )
        conversation = get_or_create_private_conversation(request.user, contact)
        return Response(
            ConversationSerializer(conversation, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


class GroupCreateView(APIView):
    permission_classes = [IsEmailVerified]
    throttle_classes = [GroupCreateRateThrottle]

    def post(self, request):
        serializer = CreateGroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conversation = create_group(request.user, **serializer.validated_data)
        return Response(
            ConversationSerializer(conversation, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ConversationDetailView(APIView):
    permission_classes = [IsEmailVerified]

    def get(self, request, conversation_id):
        conversation = accessible_conversation_or_404(request.user, conversation_id)
        return Response(ConversationSerializer(conversation, context={"request": request}).data)

    def patch(self, request, conversation_id):
        serializer = UpdateGroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            conversation = update_group(conversation_id, request.user, **serializer.validated_data)
        except (Conversation.DoesNotExist, GroupActionError) as exc:
            return action_error(exc, status.HTTP_403_FORBIDDEN)
        return Response(ConversationSerializer(conversation, context={"request": request}).data)


class MessageListCreateView(APIView):
    permission_classes = [IsEmailVerified]
    throttle_classes = [MessageRateThrottle]

    def get(self, request, conversation_id):
        conversation = accessible_conversation_or_404(request.user, conversation_id)
        membership = get_object_or_404(
            ConversationMembership, conversation=conversation, user=request.user, left_at__isnull=True
        )
        queryset = Message.objects.filter(
            conversation=conversation, id__gt=membership.joined_after_message_id
        ).select_related("author")
        after = request.query_params.get("after")
        before = request.query_params.get("before")
        if after:
            try:
                queryset = queryset.filter(id__gt=max(int(after), membership.joined_after_message_id)).order_by("id")[:100]
            except ValueError:
                return action_error("Curseur invalide.")
            messages = list(queryset)
            return Response({"results": MessageSerializer(messages, many=True).data, "next_before": None})
        if before:
            try:
                queryset = queryset.filter(id__lt=int(before))
            except ValueError:
                return action_error("Curseur invalide.")
        newest_first = list(queryset.order_by("-id")[:50])
        messages = list(reversed(newest_first))
        next_before = messages[0].id if len(messages) == 50 else None
        return Response({"results": MessageSerializer(messages, many=True).data, "next_before": next_before})

    def post(self, request, conversation_id):
        conversation = accessible_conversation_or_404(request.user, conversation_id)
        serializer = CreateMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            message, created = create_message(conversation, request.user, **serializer.validated_data)
        except MessagingBlockedError:
            return action_error(
                "La messagerie n’est pas disponible pour cette conversation.", status.HTTP_403_FORBIDDEN
            )
        except (GroupActionError, IntegrityError) as exc:
            return action_error(exc, status.HTTP_403_FORBIDDEN)
        return Response(
            MessageSerializer(message).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class InvitationInboxView(APIView):
    permission_classes = [IsEmailVerified]

    def get(self, request):
        now = timezone.now()
        request.user.group_invitations_received.filter(
            status=GroupInvitation.Status.PENDING, expires_at__lte=now
        ).update(status=GroupInvitation.Status.EXPIRED, responded_at=now)
        invitations = request.user.group_invitations_received.filter(
            status=GroupInvitation.Status.PENDING, expires_at__gt=now
        ).select_related("conversation", "inviter", "invitee")
        return Response(GroupInvitationSerializer(invitations, many=True).data)


class GroupInvitationCollectionView(APIView):
    permission_classes = [IsEmailVerified]
    throttle_classes = [GroupInviteRateThrottle]

    def get(self, request, conversation_id):
        conversation = accessible_conversation_or_404(request.user, conversation_id)
        membership = active_membership(conversation, request.user)
        if conversation.kind != Conversation.Kind.GROUP or membership.role not in (
            ConversationMembership.Role.OWNER,
            ConversationMembership.Role.ADMIN,
        ):
            return action_error("Accès refusé.", status.HTTP_403_FORBIDDEN)
        invitations = conversation.invitations.select_related("conversation", "inviter", "invitee")[:100]
        return Response(GroupInvitationSerializer(invitations, many=True).data)

    def post(self, request, conversation_id):
        serializer = CreateInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conversation = accessible_conversation_or_404(request.user, conversation_id)
        invitee = get_object_or_404(
            User, public_id=serializer.validated_data["public_id"].lower(), is_active=True
        )
        try:
            invitation = create_group_invitation(conversation, request.user, invitee)
        except GroupActionError as exc:
            return action_error(exc)
        return Response(GroupInvitationSerializer(invitation).data, status=status.HTTP_201_CREATED)


class InvitationResponseView(APIView):
    permission_classes = [IsEmailVerified]

    def post(self, request, invitation_id, action):
        if action not in ("accept", "decline"):
            return action_error("Action invalide.")
        try:
            invitation, _ = respond_to_invitation(
                invitation_id, request.user, accept=action == "accept"
            )
        except GroupInvitation.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except GroupActionError as exc:
            return action_error(exc)
        if invitation.status == GroupInvitation.Status.EXPIRED:
            return action_error("Cette invitation a expiré.")
        return Response(GroupInvitationSerializer(invitation).data)


class InvitationCancelView(APIView):
    permission_classes = [IsEmailVerified]

    def delete(self, request, invitation_id):
        try:
            cancel_invitation(invitation_id, request.user)
        except GroupInvitation.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except GroupActionError as exc:
            return action_error(exc, status.HTTP_403_FORBIDDEN)
        return Response(status=status.HTTP_204_NO_CONTENT)


class GroupMemberListView(APIView):
    permission_classes = [IsEmailVerified]

    def get(self, request, conversation_id):
        conversation = accessible_conversation_or_404(request.user, conversation_id)
        if conversation.kind != Conversation.Kind.GROUP:
            return action_error("Cette conversation n’est pas un groupe.")
        members = conversation.memberships.filter(left_at__isnull=True).select_related("user").order_by("joined_at")
        return Response(MembershipSerializer(members, many=True).data)


class GroupMemberDetailView(APIView):
    permission_classes = [IsEmailVerified]

    def patch(self, request, conversation_id, user_id):
        serializer = UpdateRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            member = change_member_role(conversation_id, request.user, user_id, serializer.validated_data["role"])
        except (Conversation.DoesNotExist, GroupActionError) as exc:
            return action_error(exc, status.HTTP_403_FORBIDDEN)
        return Response(MembershipSerializer(member).data)

    def delete(self, request, conversation_id, user_id):
        try:
            remove_group_member(conversation_id, request.user, user_id)
        except (Conversation.DoesNotExist, GroupActionError) as exc:
            return action_error(exc, status.HTTP_403_FORBIDDEN)
        return Response(status=status.HTTP_204_NO_CONTENT)


class GroupTransferOwnerView(APIView):
    permission_classes = [IsEmailVerified]

    def post(self, request, conversation_id):
        serializer = TransferOwnerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            conversation = transfer_group_ownership(
                conversation_id, request.user, serializer.validated_data["user_id"]
            )
        except (Conversation.DoesNotExist, GroupActionError) as exc:
            return action_error(exc, status.HTTP_403_FORBIDDEN)
        return Response(ConversationSerializer(conversation, context={"request": request}).data)


class GroupLeaveView(APIView):
    permission_classes = [IsEmailVerified]

    def post(self, request, conversation_id):
        serializer = LeaveGroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            leave_group(conversation_id, request.user, **serializer.validated_data)
        except (Conversation.DoesNotExist, GroupActionError) as exc:
            return action_error(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReadCursorView(APIView):
    permission_classes = [IsEmailVerified]

    def post(self, request, conversation_id):
        serializer = ReadCursorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            membership = advance_read_cursor(
                conversation_id, request.user, serializer.validated_data["message_id"]
            )
        except (Conversation.DoesNotExist, GroupActionError) as exc:
            return action_error(exc)
        return Response({"message_id": membership.last_read_message_id})


class ConversationPreferencesView(APIView):
    permission_classes = [IsEmailVerified]

    def patch(self, request, conversation_id):
        serializer = ConversationPreferencesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conversation = accessible_conversation_or_404(request.user, conversation_id)
        membership = get_object_or_404(
            ConversationMembership, conversation=conversation, user=request.user, left_at__isnull=True
        )
        membership.muted = serializer.validated_data["muted"]
        membership.save(update_fields=("muted", "updated_at"))
        return Response({"muted": membership.muted})
