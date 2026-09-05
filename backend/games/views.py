import logging
import random

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
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

logger = logging.getLogger(__name__)


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
        game_type = self.request.data.get("game_type", Game.Type.CHESS)
        if game_type == Game.Type.CHESS:
            role = config.get("color", "white")
            if role == "random":
                role = random.choice(["white", "black"])
            config = {**config, "color": role}
        elif game_type == Game.Type.AWALE:
            role = config.get("side", "player0")
            if role == "random":
                role = random.choice(["player0", "player1"])
            if role not in {"player0", "player1"}:
                raise ValidationError("Camp d’Awalé invalide.")
            config = {**config, "side": role, "ruleset": "abapa_tablechat_v1"}
        else:
            raise ValidationError("Type de jeu inconnu.")
        game = serializer.save(game_type=game_type, mode=Game.Mode.AI, status=Game.Status.IN_PROGRESS, started_at=timezone.now(), configuration=config)
        GameParticipant.objects.create(game=game, user=self.request.user, role=role)
        if game_type == Game.Type.CHESS:
            from chess_game.models import ChessState
            ChessState.objects.create(game=game)
        else:
            from awale.models import AwaleGameState
            AwaleGameState.create_for_game(game)


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
            first_role = "white" if game.game_type == Game.Type.CHESS else "player0"
            game.result = "0-1" if participant.role == first_role else "1-0"
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
            game = Game.objects.create(game_type=invitation.game_type, mode=Game.Mode.HUMAN, status=Game.Status.IN_PROGRESS, configuration=invitation.configuration, started_at=timezone.now())
            if invitation.game_type == Game.Type.AWALE:
                sender_color = invitation.configuration.get("sender_role", "player0")
                valid_roles = {"player0", "player1"}
                if sender_color not in valid_roles:
                    sender_color = "player0"
                other_color = "player1" if sender_color == "player0" else "player0"
            else:
                sender_color = invitation.configuration.get("sender_color", "white")
                other_color = "black" if sender_color == "white" else "white"
            GameParticipant.objects.bulk_create([
                GameParticipant(game=game, user=invitation.sender, role=sender_color),
                GameParticipant(game=game, user=invitation.recipient, role=other_color),
            ])
            from chat.models import Conversation, ConversationParticipant
            if invitation.game_type == Game.Type.AWALE:
                from awale.models import AwaleGameState
                AwaleGameState.create_for_game(game)
            else:
                from chess_game.models import ChessState
                ChessState.objects.create(game=game)
            conversation = Conversation.objects.create(kind=Conversation.Kind.GAME, game=game)
            ConversationParticipant.objects.bulk_create([
                ConversationParticipant(conversation=conversation, user=invitation.sender),
                ConversationParticipant(conversation=conversation, user=invitation.recipient),
            ])
            invitation.game = game
            invitation.status = GameInvitation.Status.ACCEPTED
            payload = {
                "type": "game.ready",
                "game_id": str(game.id),
                "game_type": game.game_type,
                "invitation_id": str(invitation.id),
            }
            participant_ids = (invitation.sender_id, invitation.recipient_id)

            def notify_participants():
                channel_layer = get_channel_layer()
                for user_id in participant_ids:
                    try:
                        async_to_sync(channel_layer.group_send)(f"user_{user_id}", {"type": "game_ready", "payload": payload})
                    except Exception:
                        logger.exception("Notification temps réel indisponible pour l’utilisateur %s", user_id)

            transaction.on_commit(notify_participants)
        elif action in {"decline", "cancel"}:
            expected = invitation.recipient if action == "decline" else invitation.sender
            if request.user != expected:
                raise PermissionDenied()
            invitation.status = GameInvitation.Status.DECLINED if action == "decline" else GameInvitation.Status.CANCELLED
        else:
            raise ValidationError("Action inconnue.")
        invitation.save()
        return Response(InvitationSerializer(invitation).data)
