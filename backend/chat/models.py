import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, Q


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_low = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations_as_low")
    user_high = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations_as_high")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("user_low", "user_high"), name="unique_private_pair"),
            models.CheckConstraint(condition=Q(user_low_id__lt=F("user_high_id")), name="private_pair_ordered_distinct"),
        ]

    def includes(self, user):
        return user.is_authenticated and user.pk in (self.user_low_id, self.user_high_id)

    def other_user(self, user):
        return self.user_high if user.pk == self.user_low_id else self.user_low


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="messages")
    client_id = models.UUIDField()
    content = models.CharField(max_length=4000)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("id",)
        constraints = [models.UniqueConstraint(fields=("author", "client_id"), name="unique_author_client_message")]
        indexes = [models.Index(fields=("conversation", "id"), name="chat_conv_sequence_idx")]


class DeliveryOutbox(models.Model):
    message = models.OneToOneField(Message, on_delete=models.CASCADE, related_name="outbox")
    delivered_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.CharField(max_length=200, blank=True)
    next_attempt_at = models.DateTimeField(auto_now_add=True, db_index=True)

