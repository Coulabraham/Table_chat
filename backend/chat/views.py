from django.db import transaction
from django.utils import timezone
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from friends.models import Friendship
from django.db.models import Q
from .models import Conversation, ConversationParticipant, Message
from .serializers import ConversationSerializer, MessageSerializer


class ConversationListCreateView(generics.ListCreateAPIView):
    serializer_class = ConversationSerializer

    def get_queryset(self):
        return Conversation.objects.filter(memberships__user=self.request.user).prefetch_related("memberships__user", "messages")

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        target_id = request.data.get("user_id")
        if not Friendship.objects.filter(Q(requester_id=request.user.id, addressee_id=target_id) | Q(requester_id=target_id, addressee_id=request.user.id), status="accepted").exists():
            raise ValidationError("Cette conversation est réservée à vos amis.")
        existing = Conversation.objects.filter(kind=Conversation.Kind.PRIVATE, memberships__user=request.user).filter(memberships__user_id=target_id).first()
        if existing:
            return Response(self.get_serializer(existing).data)
        conversation = Conversation.objects.create(kind=Conversation.Kind.PRIVATE)
        ConversationParticipant.objects.bulk_create([
            ConversationParticipant(conversation=conversation, user=request.user),
            ConversationParticipant(conversation=conversation, user_id=target_id),
        ])
        return Response(self.get_serializer(conversation).data, status=201)


class MessageListCreateView(generics.ListCreateAPIView):
    serializer_class = MessageSerializer

    def get_conversation(self):
        return Conversation.objects.get(pk=self.kwargs["conversation_id"], memberships__user=self.request.user)

    def get_queryset(self):
        return Message.objects.filter(conversation=self.get_conversation()).select_related("author")

    def perform_create(self, serializer):
        serializer.save(conversation=self.get_conversation(), author=self.request.user)


class MarkReadView(APIView):
    def post(self, request, conversation_id):
        membership = ConversationParticipant.objects.get(conversation_id=conversation_id, user=request.user)
        membership.last_read_at = timezone.now()
        membership.save(update_fields=("last_read_at",))
        return Response({"last_read_at": membership.last_read_at})
