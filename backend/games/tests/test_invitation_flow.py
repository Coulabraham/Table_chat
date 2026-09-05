import pytest
from rest_framework.test import APIClient

from accounts.models import User
from awale.models import AwaleGameState
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

    client.force_authenticate(alice)
    assert client.get(f"/api/games/{game.id}/").status_code == 200


@pytest.mark.django_db(transaction=True)
def test_awale_invitation_creates_the_shared_awale_state():
    alice = User.objects.create_user(email="alice-awale-flow@example.test", display_name="Alice Awalé", password="motdepasse")
    camille = User.objects.create_user(email="camille-awale-flow@example.test", display_name="Camille Awalé", password="motdepasse")
    Friendship.objects.create(requester=alice, addressee=camille, status=Friendship.Status.ACCEPTED)
    client = APIClient()
    client.force_authenticate(alice)
    response = client.post("/api/games/invitations/", {
        "recipient_id": camille.id,
        "game_type": "awale",
        "configuration": {"sender_role": "player0", "ruleset": "abapa_tablechat_v1"},
    }, format="json")
    assert response.status_code == 201
    client.force_authenticate(camille)
    response = client.post(f"/api/games/invitations/{response.data['id']}/accept/")
    assert response.status_code == 200
    assert response.data["game_type"] == "awale"
    game = Game.objects.get(pk=response.data["game_id"])
    assert set(game.participants.values_list("role", flat=True)) == {"player0", "player1"}
    state = AwaleGameState.objects.get(game=game)
    assert state.pits == [4] * 12
    assert sum(state.pits) + sum(state.scores) == 48
    assert Conversation.objects.get(game=game).memberships.count() == 2
    client.force_authenticate(camille)
    assert client.get(f"/api/games/{game.id}/").status_code == 200
