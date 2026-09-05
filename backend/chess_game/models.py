import chess
from django.conf import settings
from django.db import models


class ChessState(models.Model):
    game = models.OneToOneField("games.Game", on_delete=models.CASCADE, related_name="chess_state")
    initial_fen = models.CharField(max_length=100, default=chess.STARTING_FEN)
    fen = models.CharField(max_length=100, default=chess.STARTING_FEN)
    moves = models.JSONField(default=list)
    pgn = models.TextField(blank=True)
    revision = models.PositiveIntegerField(default=0)
    clock = models.JSONField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class ProcessedMove(models.Model):
    state = models.ForeignKey(ChessState, on_delete=models.CASCADE, related_name="processed_moves")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    request_id = models.UUIDField()
    response = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("state", "user", "request_id"), name="move_request_dedup")]


class Lesson(models.Model):
    title = models.CharField(max_length=120)
    instruction = models.CharField(max_length=300)
    initial_fen = models.CharField(max_length=100)
    side_to_move = models.CharField(max_length=5, choices=[("white", "Blancs"), ("black", "Noirs")])
    objective = models.CharField(max_length=100)
    difficulty = models.CharField(max_length=30)
    accepted_lines = models.JSONField(default=list)
    hint = models.CharField(max_length=300)
    hints = models.JSONField(default=list, blank=True)
    coach_messages = models.JSONField(default=dict, blank=True)
    explanation = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("order", "id")


class LessonProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lesson_progress")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="progress")
    completed = models.BooleanField(default=False)
    attempts = models.PositiveIntegerField(default=0)
    hint_used = models.BooleanField(default=False)
    hint_stage = models.PositiveIntegerField(default=0)
    current_fen = models.CharField(max_length=100, blank=True)
    current_ply = models.PositiveIntegerField(default=0)
    active_lines = models.JSONField(default=list, blank=True)
    history = models.JSONField(default=list, blank=True)
    last_feedback = models.CharField(max_length=500, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("user", "lesson"), name="lesson_progress_unique")]
