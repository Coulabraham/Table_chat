from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from .models import Conversation, Message
from .serializers import CreateConversationSerializer, CreateMessageSerializer, ConversationSerializer, MessageSerializer
from .services import create_message, get_or_create_private_conversation
from .throttles import MessageRateThrottle


def user_conversations(user):
    return Conversation.objects.select_related("user_low", "user_high").filter(Q(user_low=user) | Q(user_high=user))


class ConversationListCreateView(APIView):
    def get(self, request):
        conversations = user_conversations(request.user).order_by("-updated_at")[:100]
        return Response(ConversationSerializer(conversations, many=True, context={"request": request}).data)

    def post(self, request):
        serializer = CreateConversationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contact = get_object_or_404(User, public_id=serializer.validated_data["contact_public_id"].lower(), is_active=True)
        if contact.pk == request.user.pk:
            return Response({"error": {"status": 400, "details": "Impossible de discuter avec vous-même."}}, status=400)
        conversation = get_or_create_private_conversation(request.user, contact)
        return Response(ConversationSerializer(conversation, context={"request": request}).data, status=status.HTTP_200_OK)


class ConversationDetailView(APIView):
    def get(self, request, conversation_id):
        conversation = get_object_or_404(user_conversations(request.user), pk=conversation_id)
        return Response(ConversationSerializer(conversation, context={"request": request}).data)


class MessageListCreateView(APIView):
    throttle_classes = [MessageRateThrottle]

    def get(self, request, conversation_id):
        conversation = get_object_or_404(user_conversations(request.user), pk=conversation_id)
        queryset = Message.objects.filter(conversation=conversation).select_related("author")
        after = request.query_params.get("after")
        before = request.query_params.get("before")
        if after:
            try:
                queryset = queryset.filter(id__gt=int(after)).order_by("id")[:100]
            except ValueError:
                return Response({"error": {"status": 400, "details": "Curseur invalide."}}, status=400)
            messages = list(queryset)
            return Response({"results": MessageSerializer(messages, many=True).data, "next_before": None})
        if before:
            try:
                queryset = queryset.filter(id__lt=int(before))
            except ValueError:
                return Response({"error": {"status": 400, "details": "Curseur invalide."}}, status=400)
        newest_first = list(queryset.order_by("-id")[:50])
        messages = list(reversed(newest_first))
        next_before = messages[0].id if len(messages) == 50 else None
        return Response({"results": MessageSerializer(messages, many=True).data, "next_before": next_before})

    def post(self, request, conversation_id):
        conversation = get_object_or_404(user_conversations(request.user), pk=conversation_id)
        serializer = CreateMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message, created = create_message(conversation, request.user, **serializer.validated_data)
        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

