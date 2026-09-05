import uuid
import chess
from django.utils import timezone
from rest_framework import generics
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from games.models import GameParticipant
from .engine import LEVELS, best_move
from .lesson_services import play_lesson_move, reveal_hint, start_lesson, undo_lesson_move
from .models import ChessState, Lesson
from .serializers import ChessStateSerializer, LessonSerializer
from .services import apply_engine_move, apply_move


class EngineThrottle(UserRateThrottle):
    scope = "engine"


class StateView(generics.RetrieveAPIView):
    serializer_class = ChessStateSerializer
    lookup_field = "game_id"

    def get_queryset(self):
        return ChessState.objects.filter(game__participants__user=self.request.user).select_related("game")


class MoveView(APIView):
    def post(self, request, game_id):
        data = apply_move(game_id=game_id, user=request.user, uci=request.data.get("uci", ""), request_id=request.data.get("request_id") or uuid.uuid4(), expected_revision=request.data.get("revision"))
        return Response(data)


class EngineView(APIView):
    throttle_classes = [EngineThrottle]

    def post(self, request):
        fen = request.data.get("fen", "")
        level = request.data.get("level", "confirme")
        try:
            chess.Board(fen)
            move = best_move(fen, level)
        except (ValueError, RuntimeError) as exc:
            raise ValidationError("Analyse impossible ou moteur indisponible.") from exc
        return Response({"move": move, "level": level, "settings": LEVELS[level]})


class AiTurnView(APIView):
    throttle_classes = [EngineThrottle]

    def post(self, request, game_id):
        state = ChessState.objects.filter(game_id=game_id, game__participants__user=request.user).select_related("game").first()
        if not state:
            raise PermissionDenied()
        level = state.game.configuration.get("level", "decouverte")
        browser_move = request.data.get("uci")
        if browser_move and level in {"decouverte", "club"}:
            return Response(apply_engine_move(game_id=game_id, uci=browser_move))
        try:
            move = best_move(state.fen, level)
        except (ValueError, RuntimeError) as exc:
            raise ValidationError("Le moteur n’a pas pu jouer dans le délai prévu.") from exc
        return Response(apply_engine_move(game_id=game_id, uci=move))


class LessonListView(generics.ListAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer


class LessonDetailView(generics.RetrieveAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer


class LessonAttemptView(APIView):
    def post(self, request, pk):
        lesson = Lesson.objects.get(pk=pk)
        return Response(play_lesson_move(request.user, lesson, request.data.get("uci", "")))


class LessonStartView(APIView):
    def post(self, request, pk):
        lesson = Lesson.objects.get(pk=pk)
        return Response(start_lesson(request.user, lesson, reset=bool(request.data.get("reset"))))


class LessonHintView(APIView):
    def post(self, request, pk):
        return Response(reveal_hint(request.user, Lesson.objects.get(pk=pk)))


class LessonUndoView(APIView):
    def post(self, request, pk):
        return Response(undo_lesson_move(request.user, Lesson.objects.get(pk=pk)))
