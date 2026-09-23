import uuid

import pytest
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from chat.models import Conversation, Message


@pytest.fixture
def users(db):
    return [User.objects.create_user(f"{name}@example.test", name, name.title(), "long-password-123", email_verified_at=timezone.now()) for name in ("alice","bob","mallory")]


@pytest.fixture
def clients(users):
    result=[]
    for user in users:
        client=APIClient();client.force_login(user);result.append(client)
    return result


@pytest.mark.django_db(transaction=True)
def test_complete_private_message_flow_is_persistent_and_idempotent(users, clients):
    alice,bob,_=users;alice_client,bob_client,_=clients
    created=alice_client.post("/api/conversations/", {"contact_public_id":"bob"}, format="json")
    assert created.status_code==200
    conversation_id=created.data["id"]
    assert bob_client.get("/api/conversations/").data[0]["id"]==conversation_id
    client_id=str(uuid.uuid4())
    payload={"client_id":client_id,"content":"Bonjour Bob"}
    first=alice_client.post(f"/api/conversations/{conversation_id}/messages/",payload,format="json")
    second=alice_client.post(f"/api/conversations/{conversation_id}/messages/",payload,format="json")
    assert first.status_code==201 and second.status_code==200
    assert first.data["id"]==second.data["id"]
    assert Message.objects.count()==1
    history=bob_client.get(f"/api/conversations/{conversation_id}/messages/")
    assert history.data["results"][0]["content"]=="Bonjour Bob"
    bob_reply=bob_client.post(f"/api/conversations/{conversation_id}/messages/",{"client_id":str(uuid.uuid4()),"content":"Bonjour Alice"},format="json")
    assert bob_reply.status_code==201
    assert [m["content"] for m in alice_client.get(f"/api/conversations/{conversation_id}/messages/").data["results"]]==["Bonjour Bob","Bonjour Alice"]


@pytest.mark.django_db
def test_outsider_cannot_read_write_or_inspect_conversation(users, clients):
    alice,bob,mallory=users;alice_client,_,mallory_client=clients
    conversation_id=alice_client.post("/api/conversations/",{"contact_public_id":"bob"},format="json").data["id"]
    assert mallory_client.get(f"/api/conversations/{conversation_id}/").status_code==404
    assert mallory_client.get(f"/api/conversations/{conversation_id}/messages/").status_code==404
    assert mallory_client.post(f"/api/conversations/{conversation_id}/messages/",{"client_id":str(uuid.uuid4()),"content":"intrusion"},format="json").status_code==404
    assert Message.objects.count()==0


@pytest.mark.django_db
def test_one_canonical_conversation_per_pair(users, clients):
    alice,bob,_=users;alice_client,bob_client,_=clients
    one=alice_client.post("/api/conversations/",{"contact_public_id":"bob"},format="json").data["id"]
    two=bob_client.post("/api/conversations/",{"contact_public_id":"alice"},format="json").data["id"]
    assert one==two and Conversation.objects.count()==1


@pytest.mark.django_db
def test_cursor_catchup_is_ordered_and_limited_to_participant(users, clients):
    alice,bob,_=users;alice_client,bob_client,_=clients
    cid=alice_client.post("/api/conversations/",{"contact_public_id":"bob"},format="json").data["id"]
    ids=[]
    for content in ("un","deux","trois"):
        ids.append(alice_client.post(f"/api/conversations/{cid}/messages/",{"client_id":str(uuid.uuid4()),"content":content},format="json").data["id"])
    caught=bob_client.get(f"/api/conversations/{cid}/messages/?after={ids[0]}").data["results"]
    assert [item["content"] for item in caught]==["deux","trois"]


@pytest.mark.django_db
def test_logged_out_session_cannot_send(users):
    alice,bob,_=users;client=APIClient();client.force_login(alice)
    cid=client.post("/api/conversations/",{"contact_public_id":"bob"},format="json").data["id"]
    client.post("/api/auth/logout/")
    response=client.post(f"/api/conversations/{cid}/messages/",{"client_id":str(uuid.uuid4()),"content":"nope"},format="json")
    assert response.status_code in (401,403)


@pytest.mark.django_db
def test_message_content_validation(users, clients):
    _,_,_=users;alice_client,_,_=clients
    cid=alice_client.post("/api/conversations/",{"contact_public_id":"bob"},format="json").data["id"]
    for content in ("   ", "x"*4001):
        response=alice_client.post(f"/api/conversations/{cid}/messages/",{"client_id":str(uuid.uuid4()),"content":content},format="json")
        assert response.status_code==400


@pytest.mark.django_db(transaction=True)
def test_block_preserves_history_and_prevents_messages_in_both_directions(users, clients):
    alice,bob,_=users;alice_client,bob_client,_=clients
    cid=alice_client.post("/api/conversations/",{"contact_public_id":"bob"},format="json").data["id"]
    first=alice_client.post(f"/api/conversations/{cid}/messages/",{"client_id":str(uuid.uuid4()),"content":"avant blocage"},format="json")
    assert first.status_code==201
    blocked=alice_client.post("/api/blocks/",{"public_id":"bob"},format="json")
    assert blocked.status_code==201
    for client in (alice_client,bob_client):
        denied=client.post(f"/api/conversations/{cid}/messages/",{"client_id":str(uuid.uuid4()),"content":"refusé"},format="json")
        assert denied.status_code==403
        assert "bloqu" not in str(denied.data).lower()
    history=bob_client.get(f"/api/conversations/{cid}/messages/")
    assert [item["content"] for item in history.data["results"]]==["avant blocage"]
    assert alice_client.delete("/api/blocks/bob/").status_code==204
    assert bob_client.post(f"/api/conversations/{cid}/messages/",{"client_id":str(uuid.uuid4()),"content":"après déblocage"},format="json").status_code==201


@pytest.mark.django_db
def test_unverified_account_cannot_use_private_messaging():
    alice=User.objects.create_user("alice-unverified@example.test","alice_unverified","Alice","long-password-123")
    client=APIClient();client.force_login(alice)
    assert client.get("/api/users/search/?public_id=someone").status_code==403
    assert client.get("/api/conversations/").status_code==403


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("verified", "verification_required", "expected_status"),
    (
        (True, True, 200),
        (True, False, 200),
        (False, True, 403),
        (False, False, 200),
    ),
)
def test_http_messaging_uses_deployment_email_policy(verified, verification_required, expected_status):
    user = User.objects.create_user(
        f"policy-{verified}-{verification_required}@example.test",
        f"policy_{int(verified)}_{int(verification_required)}",
        "Policy",
        "long-password-123",
        email_verified_at=timezone.now() if verified else None,
    )
    client = APIClient(); client.force_login(user)
    with override_settings(REQUIRE_EMAIL_VERIFICATION=verification_required):
        assert client.get("/api/conversations/").status_code == expected_status
