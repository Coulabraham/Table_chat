import uuid

from rest_framework import generics
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from chess_game.models import Lesson
from chess_game.serializers import LessonSerializer
from .ai import choose_move
from .models import AwaleGameState
from .services import apply_ai_move, apply_player_move, engine_state, serialize_state


class AwaleThrottle(UserRateThrottle):
    scope = "engine"


class LessonListView(generics.ListAPIView):
    queryset = Lesson.objects.filter(game_type="awale")
    serializer_class = LessonSerializer


class StateView(generics.RetrieveAPIView):
    lookup_field = "game_id"

    def get_queryset(self):
        return AwaleGameState.objects.filter(game__participants__user=self.request.user).select_related("game")

    def retrieve(self, request, *args, **kwargs):
        return Response(serialize_state(self.get_object()))


class MoveView(APIView):
    def post(self, request, game_id):
        return Response(apply_player_move(
            game_id=game_id,
            user=request.user,
            pit=request.data.get("pit"),
            request_id=request.data.get("request_id") or uuid.uuid4(),
            expected_revision=request.data.get("revision"),
        ))


class AiTurnView(APIView):
    throttle_classes = [AwaleThrottle]

    def post(self, request, game_id):
        state = AwaleGameState.objects.filter(game_id=game_id, game__participants__user=request.user).select_related("game").first()
        if not state:
            raise PermissionDenied()
        revision = state.revision
        try:
            pit = choose_move(engine_state(state), state.game.configuration.get("level", "beginner"))
        except ValueError as exc:
            raise ValidationError("L’IA ne peut pas jouer.") from exc
        return Response(apply_ai_move(game_id=game_id, pit=pit, expected_revision=revision))
