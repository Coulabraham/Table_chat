from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.sessions.models import Session
from django.test import Client
from django.test import override_settings
from django.utils import timezone
import uuid
import pytest

from accounts.models import User, UserBlock
from chat.models import Conversation, ConversationMembership
from chat.services import create_group, create_message, get_or_create_private_conversation
from tablechat.asgi import application


@sync_to_async
def make_fixture():
    alice = User.objects.create_user("alice-ws@example.test", "alice_ws", "Alice", "long-password-123", email_verified_at=timezone.now())
    bob = User.objects.create_user("bob-ws@example.test", "bob_ws", "Bob", "long-password-123", email_verified_at=timezone.now())
    mallory = User.objects.create_user("mallory-ws@example.test", "mallory_ws", "Mallory", "long-password-123", email_verified_at=timezone.now())
    conversation = get_or_create_private_conversation(alice, bob)
    cookies = {}
    for name, user in (("alice", alice), ("mallory", mallory)):
        client = Client(); client.force_login(user)
        cookies[name] = client.cookies["sessionid"].value
    return conversation.id, cookies


def ws_headers(session_id):
    return [(b"cookie", f"sessionid={session_id}".encode()), (b"origin", b"http://testserver")]


@sync_to_async
def send_alice_message(conversation_id):
    conversation = Conversation.objects.get(pk=conversation_id)
    alice = User.objects.get(public_id="alice_ws")
    return create_message(conversation, alice, client_id=uuid.uuid4(), content="Message temps réel")[0].id


@sync_to_async
def logout_session(session_id):
    client = Client()
    client.cookies["sessionid"] = session_id
    return client.post("/api/auth/logout/").status_code


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_websocket_accepts_participant_and_rejects_outsider():
    conversation_id, cookies = await make_fixture()
    participant = WebsocketCommunicator(application, f"/ws/conversations/{conversation_id}/", headers=ws_headers(cookies["alice"]))
    connected, _ = await participant.connect()
    assert connected is True
    assert (await participant.receive_json_from())["type"] == "ready"
    message_id = await send_alice_message(conversation_id)
    event = await participant.receive_json_from()
    assert event["type"] == "message.created"
    assert event["message"]["id"] == message_id
    assert event["message"]["conversation_id"] == str(conversation_id)

    outsider = WebsocketCommunicator(application, f"/ws/conversations/{conversation_id}/", headers=ws_headers(cookies["mallory"]))
    connected, close_code = await outsider.connect()
    assert connected is False and close_code == 4403
    assert await logout_session(cookies["alice"]) == 204
    close_event = await participant.receive_output()
    assert close_event["type"] == "websocket.close" and close_event["code"] == 4401


@sync_to_async
def block_bob():
    client = Client()
    alice = User.objects.get(public_id="alice_ws")
    client.force_login(alice)
    return client.post("/api/blocks/", '{"public_id":"bob_ws"}', content_type="application/json").status_code


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_block_closes_already_open_websocket():
    conversation_id, cookies = await make_fixture()
    participant = WebsocketCommunicator(application, f"/ws/conversations/{conversation_id}/", headers=ws_headers(cookies["alice"]))
    connected, _ = await participant.connect()
    assert connected is True
    assert (await participant.receive_json_from())["type"] == "ready"
    assert await block_bob() == 201
    close_event = await participant.receive_output()
    assert close_event["type"] == "websocket.close" and close_event["code"] == 4403


@sync_to_async
def make_two_sessions_fixture():
    alice = User.objects.create_user("alice-sessions@example.test", "alice_sessions", "Alice", "long-password-123", email_verified_at=timezone.now())
    bob = User.objects.create_user("bob-sessions@example.test", "bob_sessions", "Bob", "long-password-123", email_verified_at=timezone.now())
    conversation = get_or_create_private_conversation(alice, bob)
    socket_client = Client(); socket_client.force_login(alice); socket_client.get("/api/me/", HTTP_USER_AGENT="Socket device")
    controller = Client(); controller.force_login(alice); controller.get("/api/me/", HTTP_USER_AGENT="Controller device")
    target = alice.account_sessions.get(session_id=socket_client.cookies["sessionid"].value)
    return conversation.id, socket_client.cookies["sessionid"].value, controller.cookies["sessionid"].value, target.id


@sync_to_async
def revoke_other_session(controller_session_id, target_id):
    client = Client(); client.cookies["sessionid"] = controller_session_id
    return client.delete(f"/api/sessions/{target_id}/").status_code


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_revoking_another_session_closes_its_websocket():
    conversation_id, socket_session, controller_session, target_id = await make_two_sessions_fixture()
    participant = WebsocketCommunicator(application, f"/ws/conversations/{conversation_id}/", headers=ws_headers(socket_session))
    connected, _ = await participant.connect()
    assert connected is True
    assert (await participant.receive_json_from())["type"] == "ready"
    assert await revoke_other_session(controller_session, target_id) == 204
    close_event = await participant.receive_output()
    assert close_event["type"] == "websocket.close" and close_event["code"] == 4401


@sync_to_async
def make_policy_fixture(*, verified, blocked=False, session_state="valid"):
    marker = uuid.uuid4().hex[:8]
    alice = User.objects.create_user(
        f"alice-{marker}@example.test",
        f"alice_{marker}",
        "Alice",
        "long-password-123",
        email_verified_at=timezone.now() if verified else None,
    )
    bob = User.objects.create_user(
        f"bob-{marker}@example.test",
        f"bob_{marker}",
        "Bob",
        "long-password-123",
        email_verified_at=timezone.now(),
    )
    conversation = get_or_create_private_conversation(alice, bob)
    if blocked:
        UserBlock.objects.create(blocker=alice, blocked=bob)
    client = Client(); client.force_login(alice)
    session_id = client.cookies["sessionid"].value
    if session_state == "expired":
        Session.objects.filter(session_key=session_id).update(
            expire_date=timezone.now() - timezone.timedelta(seconds=1)
        )
    elif session_state == "revoked":
        Session.objects.filter(session_key=session_id).delete()
    return conversation.id, session_id


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ("verified", "verification_required", "expected_connected", "expected_code"),
    (
        (True, True, True, None),
        (True, False, True, None),
        (False, True, False, 4404),
        (False, False, True, None),
    ),
)
async def test_websocket_uses_same_deployment_email_policy(
    verified, verification_required, expected_connected, expected_code
):
    conversation_id, session_id = await make_policy_fixture(verified=verified)
    with override_settings(REQUIRE_EMAIL_VERIFICATION=verification_required):
        communicator = WebsocketCommunicator(
            application,
            f"/ws/conversations/{conversation_id}/",
            headers=ws_headers(session_id),
        )
        connected, close_code = await communicator.connect()
        assert connected is expected_connected
        assert close_code == expected_code
        if connected:
            assert (await communicator.receive_json_from())["type"] == "ready"
            await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_anonymous_websocket_is_rejected_as_unauthenticated():
    conversation_id, _ = await make_policy_fixture(verified=True)
    communicator = WebsocketCommunicator(
        application,
        f"/ws/conversations/{conversation_id}/",
        headers=[(b"origin", b"http://testserver")],
    )
    connected, close_code = await communicator.connect()
    assert connected is False and close_code == 4401


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("session_state", ("expired", "revoked"))
async def test_invalid_session_websocket_is_rejected(session_state):
    conversation_id, session_id = await make_policy_fixture(
        verified=True,
        session_state=session_state,
    )
    communicator = WebsocketCommunicator(
        application,
        f"/ws/conversations/{conversation_id}/",
        headers=ws_headers(session_id),
    )
    connected, close_code = await communicator.connect()
    assert connected is False and close_code == 4401


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_blocked_websocket_is_rejected_before_acceptance():
    conversation_id, session_id = await make_policy_fixture(verified=True, blocked=True)
    communicator = WebsocketCommunicator(
        application,
        f"/ws/conversations/{conversation_id}/",
        headers=ws_headers(session_id),
    )
    connected, close_code = await communicator.connect()
    assert connected is False and close_code == 4403


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_ping_retries_pending_outbox_without_permanent_worker(monkeypatch):
    conversation_id, session_id = await make_policy_fixture(verified=True)
    calls = []

    def record_retry(**kwargs):
        calls.append(kwargs)
        return {"attempted": 0, "delivered": 0}

    monkeypatch.setattr("chat.consumers.publish_pending_events", record_retry)
    communicator = WebsocketCommunicator(
        application,
        f"/ws/conversations/{conversation_id}/",
        headers=ws_headers(session_id),
    )
    connected, _ = await communicator.connect()
    assert connected is True
    assert (await communicator.receive_json_from())["type"] == "ready"

    await communicator.send_json_to({"type": "ping"})
    assert (await communicator.receive_json_from())["type"] == "pong"
    assert calls == [
        {"conversation_id": conversation_id},
        {"conversation_id": conversation_id},
    ]
    await communicator.disconnect()


@sync_to_async
def make_group_socket_fixture():
    marker = uuid.uuid4().hex[:8]
    users = []
    sessions = []
    for index in range(3):
        user = User.objects.create_user(
            f"group-ws-{marker}-{index}@example.test",
            f"group_ws_{marker}_{index}",
            f"Membre {index + 1}",
            "long-password-123",
            email_verified_at=timezone.now(),
        )
        client = Client(); client.force_login(user)
        users.append(user)
        sessions.append(client.cookies["sessionid"].value)
    conversation = create_group(users[0], name="Groupe temps réel")
    for user in users[1:]:
        ConversationMembership.objects.create(
            conversation=conversation,
            user=user,
            role=ConversationMembership.Role.MEMBER,
        )
    return conversation.id, [user.id for user in users], sessions


@sync_to_async
def send_group_message(conversation_id, author_id):
    conversation = Conversation.objects.get(pk=conversation_id)
    author = User.objects.get(pk=author_id)
    return create_message(conversation, author, client_id=uuid.uuid4(), content="Bonjour au groupe")[0].id


@sync_to_async
def remove_group_user(conversation_id, owner_id, target_id):
    owner = User.objects.get(pk=owner_id)
    client = Client(); client.force_login(owner)
    return client.delete(f"/api/conversations/{conversation_id}/members/{target_id}/").status_code


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_group_realtime_reaches_three_sessions_and_removal_closes_socket():
    conversation_id, user_ids, sessions = await make_group_socket_fixture()
    sockets = [
        WebsocketCommunicator(
            application,
            f"/ws/conversations/{conversation_id}/",
            headers=ws_headers(session_id),
        )
        for session_id in sessions
    ]
    for communicator in sockets:
        connected, _ = await communicator.connect()
        assert connected is True
        assert (await communicator.receive_json_from())["type"] == "ready"
    message_id = await send_group_message(conversation_id, user_ids[0])
    for communicator in sockets:
        event = await communicator.receive_json_from()
        assert event["type"] == "message.created"
        assert event["message"]["id"] == message_id
    assert await remove_group_user(conversation_id, user_ids[0], user_ids[2]) == 204
    close_event = await sockets[2].receive_output()
    assert close_event["type"] == "websocket.close" and close_event["code"] == 4403
    # Les autres membres reçoivent l'événement public, sans données d'invitation.
    for communicator in sockets[:2]:
        event = await communicator.receive_json_from()
        assert event["type"] == "member.removed"
        assert "invitee" not in event and "expires_at" not in event
        await communicator.disconnect()
