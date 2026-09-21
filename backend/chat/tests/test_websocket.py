from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from django.test import Client
from django.utils import timezone
import uuid
import pytest

from accounts.models import User
from chat.models import Conversation
from chat.services import create_message, get_or_create_private_conversation
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
