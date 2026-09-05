from rest_framework import serializers
from .lesson_services import serialize_session
from .models import ChessState, Lesson, LessonProgress


class ChessStateSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source="game.status", read_only=True)
    result = serializers.CharField(source="game.result", read_only=True)
    end_reason = serializers.CharField(source="game.end_reason", read_only=True)

    class Meta:
        model = ChessState
        fields = ("game_id", "initial_fen", "fen", "moves", "pgn", "revision", "clock", "status", "result", "end_reason")


class LessonSerializer(serializers.ModelSerializer):
    progress = serializers.SerializerMethodField()
    next_lesson_id = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = ("id", "title", "instruction", "initial_fen", "side_to_move", "objective", "difficulty", "hints", "explanation", "coach_messages", "order", "progress", "next_lesson_id")

    def get_progress(self, obj):
        request = self.context.get("request")
        if not request:
            return None
        progress = LessonProgress.objects.filter(user=request.user, lesson=obj).first()
        return serialize_session(progress, obj) if progress else None

    def get_next_lesson_id(self, obj):
        return Lesson.objects.filter(order__gt=obj.order).order_by("order").values_list("id", flat=True).first()
