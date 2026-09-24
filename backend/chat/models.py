import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, Q


class Conversation(models.Model):
    class Kind(models.TextChoices):
        PRIVATE = "private", "Privée"
        GROUP = "group", "Groupe"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.PRIVATE, db_index=True)
    user_low = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations_as_low", null=True, blank=True
    )
    user_high = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations_as_high", null=True, blank=True
    )
    name = models.CharField(max_length=80, blank=True)
    description = models.CharField(max_length=500, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="groups_owned", null=True, blank=True
    )
    archived_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user_low", "user_high"), condition=Q(kind="private"), name="unique_private_pair"
            ),
            models.CheckConstraint(
                condition=(
                    Q(kind="private", user_low__isnull=False, user_high__isnull=False, owner__isnull=True)
                    | Q(kind="group", user_low__isnull=True, user_high__isnull=True, owner__isnull=False)
                ),
                name="conversation_kind_shape",
            ),
            models.CheckConstraint(
                condition=Q(kind="group") | Q(user_low_id__lt=F("user_high_id")),
                name="private_pair_ordered_distinct",
            ),
        ]

    def includes(self, user):
        if not user.is_authenticated:
            return False
        if self.kind == self.Kind.PRIVATE:
            return user.pk in (self.user_low_id, self.user_high_id)
        return self.memberships.filter(user=user, left_at__isnull=True).exists()

    def other_user(self, user):
        if self.kind != self.Kind.PRIVATE:
            return None
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


class ConversationMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Propriétaire"
        ADMIN = "admin", "Administrateur"
        MEMBER = "member", "Membre"

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversation_memberships")
    role = models.CharField(max_length=12, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True, db_index=True)
    joined_after_message_id = models.BigIntegerField(default=0)
    left_after_message_id = models.BigIntegerField(null=True, blank=True)
    last_read_message = models.ForeignKey(
        Message, on_delete=models.SET_NULL, related_name="+", null=True, blank=True
    )
    muted = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("conversation", "user"), condition=Q(left_at__isnull=True), name="unique_active_membership"
            ),
            models.UniqueConstraint(
                fields=("conversation",),
                condition=Q(role="owner", left_at__isnull=True),
                name="unique_active_group_owner",
            ),
        ]
        indexes = [models.Index(fields=("user", "left_at"), name="chat_member_active_idx")]


class GroupInvitation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        ACCEPTED = "accepted", "Acceptée"
        DECLINED = "declined", "Refusée"
        CANCELLED = "cancelled", "Annulée"
        EXPIRED = "expired", "Expirée"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="invitations")
    inviter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="group_invitations_sent")
    invitee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="group_invitations_received")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("conversation", "invitee"),
                condition=Q(status="pending"),
                name="unique_pending_group_invite",
            )
        ]
        ordering = ("-created_at",)


class DeliveryOutbox(models.Model):
    message = models.OneToOneField(Message, on_delete=models.CASCADE, related_name="outbox")
    delivered_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.CharField(max_length=200, blank=True)
    next_attempt_at = models.DateTimeField(auto_now_add=True, db_index=True)
