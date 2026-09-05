import pytest
from rest_framework.test import APIClient

from accounts.models import User
from chat.models import Conversation
from chess_game.models import ChessState
from friends.models import Friendship
from games.models import Game, GameInvitation


@pytest.mark.django_db(transaction=True)
def test_friends_can_accept_an_invitation_and_get_a_complete_game():
    alice = User.objects.create_user(email="alice-flow@example.test", display_name="Alice flow", password="motdepasse")
    camille = User.objects.create_user(email="camille-flow@example.test", display_name="Camille flow", password="motdepasse")
    Friendship.objects.create(requester=alice, addressee=camille, status=Friendship.Status.ACCEPTED)

    client = APIClient()
    client.force_authenticate(alice)
    response = client.post("/api/games/invitations/", {"recipient_id": camille.id, "configuration": {"sender_color": "white"}}, format="json")
    assert response.status_code == 201
    invitation = GameInvitation.objects.get(pk=response.data["id"])

    client.force_authenticate(camille)
    response = client.post(f"/api/games/invitations/{invitation.id}/accept/")
    assert response.status_code == 200
    game = Game.objects.get(pk=response.data["game_id"])
    assert game.status == Game.Status.IN_PROGRESS
    assert set(game.participants.values_list("role", flat=True)) == {"white", "black"}
    assert ChessState.objects.filter(game=game, revision=0).exists()
    conversation = Conversation.objects.get(game=game)
    assert conversation.memberships.count() == 2
