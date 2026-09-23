import uuid

import pytest
from django.utils import timezone

from accounts.models import User
from chat.models import DeliveryOutbox, Message
from chat.services import create_message, get_or_create_private_conversation, publish_pending_events


class RecordingChannelLayer:
    def __init__(self):
        self.fail = True
        self.events = []

    async def group_send(self, group, event):
        if self.fail:
            raise ConnectionError("simulated Redis outage")
        self.events.append((group, event))


@pytest.mark.django_db(transaction=True)
def test_outbox_recovers_after_redis_outage_without_duplicate_message(monkeypatch):
    alice = User.objects.create_user(
        "outbox-alice@example.test", "outbox_alice", "Alice", "long-password-123",
        email_verified_at=timezone.now(),
    )
    bob = User.objects.create_user(
        "outbox-bob@example.test", "outbox_bob", "Bob", "long-password-123",
        email_verified_at=timezone.now(),
    )
    conversation = get_or_create_private_conversation(alice, bob)
    layer = RecordingChannelLayer()
    monkeypatch.setattr("chat.services.get_channel_layer", lambda: layer)
    client_id = uuid.uuid4()

    first, created = create_message(
        conversation,
        alice,
        client_id=client_id,
        content="Persisté pendant la panne",
    )
    assert created is True
    outbox = DeliveryOutbox.objects.get(message=first)
    assert outbox.delivered_at is None
    assert outbox.attempts == 1
    assert outbox.last_error == "ConnectionError"

    duplicate, created = create_message(
        conversation,
        alice,
        client_id=client_id,
        content="Persisté pendant la panne",
    )
    assert created is False and duplicate.pk == first.pk
    assert Message.objects.filter(author=alice, client_id=client_id).count() == 1

    layer.fail = False
    DeliveryOutbox.objects.filter(pk=outbox.pk).update(
        next_attempt_at=timezone.now() - timezone.timedelta(seconds=1)
    )
    result = publish_pending_events(conversation_id=conversation.pk)

    outbox.refresh_from_db()
    assert result == {"attempted": 1, "delivered": 1}
    assert outbox.delivered_at is not None
    assert len(layer.events) == 1
    assert layer.events[0][1]["message"]["id"] == first.pk
