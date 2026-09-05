import random

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from friends.models import Friendship
from .models import Game, GameInvitation, GameParticipant
from .serializers import GameSerializer, InvitationSerializer


class GameListCreateView(generics.ListCreateAPIView):
    serializer_class = GameSerializer

    def get_queryset(self):
        return Game.objects.filter(participants__user=self.request.user).prefetch_related("participants__user").order_by("-created_at")

    @transaction.atomic
    def perform_create(self, serializer):
        mode = self.request.data.get("mode")
        if mode != Game.Mode.AI:
            raise ValidationError("Une partie humaine se crée en acceptant une invitation.")
        config = self.request.data.get("configuration", {})
        color = config.get("color", "white")
        if color == "random":
            color = random.choice(["white", "black"])
        game = serializer.save(mode=Game.Mode.AI, status=Game.Status.IN_PROGRESS, started_at=timezone.now(), configuration={**config, "color": color})
        GameParticipant.objects.create(game=game, user=self.request.user, role=color)
        from chess_game.models import ChessState
        ChessState.objects.create(game=game)


class GameDetailView(generics.RetrieveAPIView):
    serializer_class = GameSerializer

    def get_queryset(self):
        return Game.objects.filter(participants__user=self.request.user).prefetch_related("participants__user")


class GameActionView(APIView):
    @transaction.atomic
    def post(self, request, pk, action):
        game = Game.objects.select_for_update().filter(pk=pk, participants__user=request.user).first()
        if not game:
            raise PermissionDenied()
        if game.status != Game.Status.IN_PROGRESS:
            raise ValidationError("La partie n’est pas active.")
        if action == "resign":
            participant = game.participants.get(user=request.user)
            game.result = "0-1" if participant.role == "white" else "1-0"
            game.end_reason = "abandon"
            game.status = Game.Status.FINISHED
            game.finished_at = timezone.now()
        elif action == "draw":
            # En V1 l’adversaire confirme la proposition via la même action.
            proposer = game.configuration.get("draw_offered_by")
            if proposer and proposer != request.user.id:
                game.result = "1/2-1/2"
                game.end_reason = "accord mutuel"
                game.status = Game.Status.FINISHED
                game.finished_at = timezone.now()
            else:
                game.configuration = {**game.configuration, "draw_offered_by": request.user.id}
        else:
            raise ValidationError("Action inconnue.")
        game.save()
        return Response(GameSerializer(game).data)


class InvitationListCreateView(generics.ListCreateAPIView):
    serializer_class = InvitationSerializer

    def get_queryset(self):
        return GameInvitation.objects.filter(Q(sender=self.request.user) | Q(recipient=self.request.user)).select_related("sender", "recipient", "game").order_by("-created_at")

    def perform_create(self, serializer):
        target = serializer.validated_data["recipient"]
        are_friends = Friendship.objects.filter(
            Q(requester=self.request.user, addressee=target) | Q(requester=target, addressee=self.request.user),
            status=Friendship.Status.ACCEPTED,
        ).exists()
        if not are_friends:
            raise ValidationError("Vous pouvez uniquement inviter un ami.")
        serializer.save()


class InvitationActionView(APIView):
    @transaction.atomic
    def post(self, request, pk, action):
        invitation = GameInvitation.objects.select_for_update().get(pk=pk)
        if invitation.status != GameInvitation.Status.PENDING or invitation.expires_at <= timezone.now():
            raise ValidationError("Cette invitation n’est plus disponible.")
        if action == "accept":
            if invitation.recipient != request.user:
                raise PermissionDenied()
            game = Game.objects.create(mode=Game.Mode.HUMAN, status=Game.Status.IN_PROGRESS, configuration=invitation.configuration, started_at=timezone.now())
            sender_color = invitation.configuration.get("sender_color", "white")
            GameParticipant.objects.bulk_create([
                GameParticipant(game=game, user=invitation.sender, role=sender_color),
                GameParticipant(game=game, user=invitation.recipient, role="black" if sender_color == "white" else "white"),
            ])
            from chess_game.models import ChessState
            from chat.models import Conversation, ConversationParticipant
            ChessState.objects.create(game=game)
            conversation = Conversation.objects.create(kind=Conversation.Kind.GAME, game=game)
            ConversationParticipant.objects.bulk_create([
                ConversationParticipant(conversation=conversation, user=invitation.sender),
                ConversationParticipant(conversation=conversation, user=invitation.recipient),
            ])
            invitation.game = game
            invitation.status = GameInvitation.Status.ACCEPTED
        elif action in {"decline", "cancel"}:
            expected = invitation.recipient if action == "decline" else invitation.sender
            if request.user != expected:
                raise PermissionDenied()
            invitation.status = GameInvitation.Status.DECLINED if action == "decline" else GameInvitation.Status.CANCELLED
        else:
            raise ValidationError("Action inconnue.")
        invitation.save()
        return Response(InvitationSerializer(invitation).data)
