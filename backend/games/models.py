import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


def invitation_expiry():
    return timezone.now() + timedelta(hours=24)


class Game(models.Model):
    class Mode(models.TextChoices):
        HUMAN = "human", "Entre amis"
        AI = "ai", "Contre l’IA"

    class Status(models.TextChoices):
        WAITING = "waiting", "En attente"
        IN_PROGRESS = "in_progress", "En cours"
        FINISHED = "finished", "Terminée"
        CANCELLED = "cancelled", "Annulée"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    game_type = models.CharField(max_length=30, default="chess")
    mode = models.CharField(max_length=12, choices=Mode.choices)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.WAITING)
    configuration = models.JSONField(default=dict, blank=True)
    result = models.CharField(max_length=20, blank=True)
    end_reason = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=("status", "created_at")), models.Index(fields=("game_type", "mode"))]


class GameParticipant(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="game_participations")
    role = models.CharField(max_length=20)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("game", "user"), name="game_user_unique"),
            models.UniqueConstraint(fields=("game", "role"), name="game_role_unique"),
        ]


class GameInvitation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        ACCEPTED = "accepted", "Acceptée"
        DECLINED = "declined", "Refusée"
        CANCELLED = "cancelled", "Annulée"
        EXPIRED = "expired", "Expirée"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="game_invitations_sent")
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="game_invitations_received")
    configuration = models.JSONField(default=dict)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    game = models.OneToOneField(Game, null=True, blank=True, on_delete=models.SET_NULL, related_name="invitation")
    expires_at = models.DateTimeField(default=invitation_expiry)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=("recipient", "status", "expires_at"))]

