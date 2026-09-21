from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import User, UserBlock
from .models import Conversation, DeliveryOutbox, Message
from .serializers import MessageSerializer


class MessagingBlockedError(Exception):
    pass


def get_or_create_private_conversation(user, contact):
    low, high = sorted((user, contact), key=lambda item: item.pk)
    try:
        with transaction.atomic():
            conversation, _ = Conversation.objects.get_or_create(user_low=low, user_high=high)
            return conversation
    except IntegrityError:
        return Conversation.objects.get(user_low=low, user_high=high)


def publish_message(message_id):
    message = Message.objects.select_related("conversation").get(pk=message_id)
    payload = MessageSerializer(message).data
    # DRF's HTTP renderer knows how to encode UUID values, while Channels'
    # JSON consumer deliberately uses the standard encoder.
    payload["conversation_id"] = str(message.conversation_id)
    outbox, _ = DeliveryOutbox.objects.get_or_create(message=message)
    try:
        async_to_sync(get_channel_layer().group_send)(
            f"conversation_{message.conversation_id}",
            {"type": "chat.message", "message": payload},
        )
    except Exception as exc:
        outbox.attempts += 1
        outbox.last_error = type(exc).__name__[:200]
        outbox.next_attempt_at = timezone.now() + timezone.timedelta(seconds=min(300, 2 ** min(outbox.attempts, 8)))
        outbox.save(update_fields=("attempts", "last_error", "next_attempt_at"))
        return False
    outbox.attempts += 1
    outbox.delivered_at = timezone.now()
    outbox.last_error = ""
    outbox.save(update_fields=("attempts", "delivered_at", "last_error"))
    return True


def create_message(conversation, author, *, client_id, content):
    with transaction.atomic():
        participant_ids = sorted((conversation.user_low_id, conversation.user_high_id))
        list(User.objects.select_for_update().filter(pk__in=participant_ids).order_by("pk"))
        if UserBlock.objects.filter(
            Q(blocker_id=participant_ids[0], blocked_id=participant_ids[1])
            | Q(blocker_id=participant_ids[1], blocked_id=participant_ids[0])
        ).exists():
            raise MessagingBlockedError
        existing = Message.objects.filter(author=author, client_id=client_id).first()
        if existing is not None:
            if existing.conversation_id != conversation.pk:
                raise IntegrityError("client_id already used in another conversation")
            return existing, False
        try:
            # The inner savepoint lets a simultaneous unique-key conflict roll
            # back cleanly before the winning row is read below.
            with transaction.atomic():
                message = Message.objects.create(
                    conversation=conversation,
                    author=author,
                    client_id=client_id,
                    content=content,
                )
        except IntegrityError:
            message = Message.objects.get(author=author, client_id=client_id)
            if message.conversation_id != conversation.pk:
                raise
            return message, False
        Conversation.objects.filter(pk=conversation.pk).update(updated_at=message.created_at)
        DeliveryOutbox.objects.create(message=message)
        transaction.on_commit(lambda: publish_message(message.pk))
    return message, True
