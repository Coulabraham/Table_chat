import uuid

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User, UserBlock
from chat.models import Conversation, ConversationMembership, GroupInvitation, Message


@pytest.fixture
def group_users(db):
    users = {}
    for name in ("owner", "admin", "member", "outsider"):
        users[name] = User.objects.create_user(
            f"{name}-group@example.test",
            f"{name}_group",
            name.title(),
            "long-password-123",
            email_verified_at=timezone.now(),
        )
    return users


@pytest.fixture
def group_clients(group_users):
    clients = {}
    for name, user in group_users.items():
        client = APIClient()
        client.force_login(user)
        clients[name] = client
    return clients


def create_group(client, name="Les amis"):
    response = client.post("/api/groups/", {"name": name, "description": "Notre groupe"}, format="json")
    assert response.status_code == 201
    return response.data["id"]


def invite_and_accept(owner_client, invitee_client, conversation_id, public_id):
    invitation = owner_client.post(
        f"/api/conversations/{conversation_id}/invitations/", {"public_id": public_id}, format="json"
    )
    assert invitation.status_code == 201
    accepted = invitee_client.post(f"/api/group-invitations/{invitation.data['id']}/accept/", {}, format="json")
    assert accepted.status_code == 200
    return invitation.data["id"]


def send(client, conversation_id, content):
    return client.post(
        f"/api/conversations/{conversation_id}/messages/",
        {"client_id": str(uuid.uuid4()), "content": content},
        format="json",
    )


@pytest.mark.django_db(transaction=True)
def test_group_creation_invitation_and_pending_access(group_users, group_clients):
    cid = create_group(group_clients["owner"])
    invitation = group_clients["owner"].post(
        f"/api/conversations/{cid}/invitations/",
        {"public_id": group_users["member"].public_id},
        format="json",
    )
    assert invitation.status_code == 201
    assert group_clients["member"].get(f"/api/conversations/{cid}/").status_code == 404
    inbox = group_clients["member"].get("/api/group-invitations/")
    assert inbox.status_code == 200 and inbox.data[0]["conversation"]["name"] == "Les amis"
    assert group_clients["outsider"].get(f"/api/conversations/{cid}/members/").status_code == 404
    assert group_clients["member"].post(
        f"/api/group-invitations/{invitation.data['id']}/accept/", {}, format="json"
    ).status_code == 200
    detail = group_clients["member"].get(f"/api/conversations/{cid}/")
    assert detail.status_code == 200 and detail.data["my_role"] == "member"


@pytest.mark.django_db(transaction=True)
def test_invitation_decline_cancel_expiry_and_duplicate(group_users, group_clients, settings):
    cid = create_group(group_clients["owner"])
    first = group_clients["owner"].post(
        f"/api/conversations/{cid}/invitations/", {"public_id": "member_group"}, format="json"
    )
    duplicate = group_clients["owner"].post(
        f"/api/conversations/{cid}/invitations/", {"public_id": "member_group"}, format="json"
    )
    assert duplicate.status_code == 400
    assert group_clients["member"].post(
        f"/api/group-invitations/{first.data['id']}/decline/", {}, format="json"
    ).data["status"] == "declined"
    assert group_clients["member"].post(
        f"/api/group-invitations/{first.data['id']}/accept/", {}, format="json"
    ).status_code == 400
    second = group_clients["owner"].post(
        f"/api/conversations/{cid}/invitations/", {"public_id": "member_group"}, format="json"
    )
    assert group_clients["owner"].delete(f"/api/group-invitations/{second.data['id']}/").status_code == 204
    third = group_clients["owner"].post(
        f"/api/conversations/{cid}/invitations/", {"public_id": "member_group"}, format="json"
    )
    GroupInvitation.objects.filter(pk=third.data["id"]).update(expires_at=timezone.now())
    expired = group_clients["member"].post(
        f"/api/group-invitations/{third.data['id']}/accept/", {}, format="json"
    )
    assert expired.status_code == 400
    assert GroupInvitation.objects.get(pk=third.data["id"]).status == GroupInvitation.Status.EXPIRED


@pytest.mark.django_db(transaction=True)
def test_history_bounds_removal_and_rejoin(group_users, group_clients):
    cid = create_group(group_clients["owner"])
    before = send(group_clients["owner"], cid, "secret avant arrivée")
    assert before.status_code == 201
    invite_and_accept(group_clients["owner"], group_clients["member"], cid, "member_group")
    after = send(group_clients["owner"], cid, "visible après arrivée")
    history = group_clients["member"].get(f"/api/conversations/{cid}/messages/")
    assert [item["content"] for item in history.data["results"]] == ["visible après arrivée"]
    assert group_clients["owner"].delete(
        f"/api/conversations/{cid}/members/{group_users['member'].id}/"
    ).status_code == 204
    assert group_clients["member"].get(f"/api/conversations/{cid}/messages/").status_code == 404
    send(group_clients["owner"], cid, "pendant absence")
    invite_and_accept(group_clients["owner"], group_clients["member"], cid, "member_group")
    send(group_clients["owner"], cid, "après retour")
    returned = group_clients["member"].get(f"/api/conversations/{cid}/messages/")
    assert [item["content"] for item in returned.data["results"]] == ["après retour"]
    assert ConversationMembership.objects.filter(conversation_id=cid, user=group_users["member"]).count() == 2


@pytest.mark.django_db(transaction=True)
def test_roles_permissions_transfer_and_leave(group_users, group_clients):
    cid = create_group(group_clients["owner"])
    invite_and_accept(group_clients["owner"], group_clients["admin"], cid, "admin_group")
    invite_and_accept(group_clients["owner"], group_clients["member"], cid, "member_group")
    promoted = group_clients["owner"].patch(
        f"/api/conversations/{cid}/members/{group_users['admin'].id}/", {"role": "admin"}, format="json"
    )
    assert promoted.status_code == 200
    assert group_clients["member"].post(
        f"/api/conversations/{cid}/invitations/", {"public_id": "outsider_group"}, format="json"
    ).status_code == 400
    assert group_clients["admin"].post(
        f"/api/conversations/{cid}/invitations/", {"public_id": "outsider_group"}, format="json"
    ).status_code == 201
    assert group_clients["admin"].delete(
        f"/api/conversations/{cid}/members/{group_users['owner'].id}/"
    ).status_code == 403
    transferred = group_clients["owner"].post(
        f"/api/conversations/{cid}/transfer-owner/", {"user_id": group_users["admin"].id}, format="json"
    )
    assert transferred.status_code == 200 and transferred.data["owner"]["id"] == group_users["admin"].id
    assert group_clients["owner"].post(f"/api/conversations/{cid}/leave/", {}, format="json").status_code == 204
    assert group_clients["owner"].get(f"/api/conversations/{cid}/").status_code == 404


@pytest.mark.django_db(transaction=True)
def test_block_prevents_invite_but_not_common_group_messages(group_users, group_clients):
    cid = create_group(group_clients["owner"])
    invite_and_accept(group_clients["owner"], group_clients["member"], cid, "member_group")
    UserBlock.objects.create(blocker=group_users["owner"], blocked=group_users["member"])
    message = send(group_clients["member"], cid, "toujours visible dans le groupe")
    assert message.status_code == 201
    assert group_clients["owner"].get(f"/api/conversations/{cid}/messages/").data["results"][0]["content"] == "toujours visible dans le groupe"
    other = create_group(group_clients["owner"], "Autre groupe")
    denied = group_clients["owner"].post(
        f"/api/conversations/{other}/invitations/", {"public_id": "member_group"}, format="json"
    )
    assert denied.status_code == 400 and "bloqu" not in str(denied.data).lower()


@pytest.mark.django_db(transaction=True)
def test_unread_cursor_is_monotonic_scoped_and_excludes_own_messages(group_users, group_clients):
    cid = create_group(group_clients["owner"])
    invite_and_accept(group_clients["owner"], group_clients["member"], cid, "member_group")
    first = send(group_clients["owner"], cid, "un")
    second = send(group_clients["owner"], cid, "deux")
    send(group_clients["member"], cid, "mon message")
    listed = group_clients["member"].get("/api/conversations/").data[0]
    assert listed["unread_count"] == 2
    second_device = APIClient()
    second_device.force_login(group_users["member"])
    assert second_device.post(
        f"/api/conversations/{cid}/read/", {"message_id": second.data["id"]}, format="json"
    ).status_code == 200
    assert group_clients["member"].post(
        f"/api/conversations/{cid}/read/", {"message_id": first.data["id"]}, format="json"
    ).data["message_id"] == second.data["id"]
    assert group_clients["member"].get("/api/conversations/").data[0]["unread_count"] == 0
    other = create_group(group_clients["outsider"], "Hors contexte")
    wrong_message = send(group_clients["outsider"], other, "ailleurs")
    assert group_clients["member"].post(
        f"/api/conversations/{cid}/read/", {"message_id": wrong_message.data["id"]}, format="json"
    ).status_code == 400


@pytest.mark.django_db(transaction=True)
def test_private_conversation_contract_is_preserved(group_clients):
    response = group_clients["owner"].post(
        "/api/conversations/", {"contact_public_id": "member_group"}, format="json"
    )
    assert response.status_code == 200 and response.data["kind"] == Conversation.Kind.PRIVATE
    assert response.data["other_user"]["public_id"] == "member_group"
    cid = response.data["id"]
    assert send(group_clients["owner"], cid, "message privé").status_code == 201
    assert group_clients["member"].get(f"/api/conversations/{cid}/messages/").status_code == 200
