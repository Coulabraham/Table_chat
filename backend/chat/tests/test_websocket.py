from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from django.test import Client
import uuid
import pytest

from accounts.models import User
from chat.models import Conversation
from chat.services import create_message, get_or_create_private_conversation
from tablechat.asgi import application


@sync_to_async
def make_fixture():
    alice = User.objects.create_user("alice-ws@example.test", "alice_ws", "Alice", "long-password-123")
    bob = User.objects.create_user("bob-ws@example.test", "bob_ws", "Bob", "long-password-123")
    mallory = User.objects.create_user("mallory-ws@example.test", "mallory_ws", "Mallory", "long-password-123")
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
