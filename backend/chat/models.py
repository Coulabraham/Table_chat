import uuid
from django.conf import settings
from django.db import models


class Conversation(models.Model):
    class Kind(models.TextChoices):
        PRIVATE = "private", "Privée"
        GAME = "game", "Partie"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    game = models.OneToOneField("games.Game", null=True, blank=True, on_delete=models.SET_NULL, related_name="conversation")
    created_at = models.DateTimeField(auto_now_add=True)


class ConversationParticipant(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversation_memberships")
    last_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("conversation", "user"), name="conversation_user_unique")]


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="chat_messages")
    content = models.CharField(max_length=1000)
    client_id = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [models.UniqueConstraint(fields=("conversation", "author", "client_id"), name="message_client_dedup")]
        indexes = [models.Index(fields=("conversation", "created_at"))]

