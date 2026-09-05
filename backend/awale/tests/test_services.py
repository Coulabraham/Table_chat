import uuid

import pytest
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from accounts.models import User
from awale.models import AwaleGameState, AwaleMove
from awale.services import apply_ai_move, apply_player_move
from games.models import Game, GameParticipant


@pytest.fixture
def awale_match(db):
    first = User.objects.create_user(email="first-awale@example.test", display_name="Joueur Awalé 1", password="motdepasse")
    second = User.objects.create_user(email="second-awale@example.test", display_name="Joueur Awalé 2", password="motdepasse")
    outsider = User.objects.create_user(email="outside-awale@example.test", display_name="Spectateur Awalé", password="motdepasse")
    game = Game.objects.create(game_type=Game.Type.AWALE, mode=Game.Mode.HUMAN, status=Game.Status.IN_PROGRESS)
    GameParticipant.objects.create(game=game, user=first, role="player0")
    GameParticipant.objects.create(game=game, user=second, role="player1")
    AwaleGameState.create_for_game(game)
    return game, first, second, outsider


@pytest.mark.django_db(transaction=True)
def test_move_is_persisted_and_duplicate_is_idempotent(awale_match):
    game, first, _, _ = awale_match
    request_id = uuid.uuid4()
    response = apply_player_move(game_id=game.id, user=first, pit=0, request_id=request_id, expected_revision=0)
    duplicate = apply_player_move(game_id=game.id, user=first, pit=0, request_id=request_id, expected_revision=0)
    assert duplicate == response
    assert response["revision"] == 1
    assert len(response["history"]) == 1
    assert AwaleMove.objects.filter(state__game=game).count() == 1


@pytest.mark.django_db(transaction=True)
def test_turn_revision_and_participation_are_server_controlled(awale_match):
    game, first, second, outsider = awale_match
    with pytest.raises(ValidationError, match="tour"):
        apply_player_move(game_id=game.id, user=second, pit=6, request_id=uuid.uuid4(), expected_revision=0)
    with pytest.raises(PermissionDenied):
        apply_player_move(game_id=game.id, user=outsider, pit=0, request_id=uuid.uuid4(), expected_revision=0)
    apply_player_move(game_id=game.id, user=first, pit=0, request_id=uuid.uuid4(), expected_revision=0)
    with pytest.raises(ValidationError):
        apply_player_move(game_id=game.id, user=second, pit=6, request_id=uuid.uuid4(), expected_revision=0)


@pytest.mark.django_db(transaction=True)
def test_obsolete_ai_result_is_rejected(db):
    user = User.objects.create_user(email="ai-awale@example.test", display_name="Contre IA Awalé", password="motdepasse")
    game = Game.objects.create(game_type=Game.Type.AWALE, mode=Game.Mode.AI, status=Game.Status.IN_PROGRESS)
    GameParticipant.objects.create(game=game, user=user, role="player0")
    AwaleGameState.create_for_game(game)
    apply_player_move(game_id=game.id, user=user, pit=0, request_id=uuid.uuid4(), expected_revision=0)
    with pytest.raises(ValidationError, match="obsolète"):
        apply_ai_move(game_id=game.id, pit=6, expected_revision=0)


@pytest.mark.django_db(transaction=True)
def test_complete_ai_api_flow(db):
    user = User.objects.create_user(email="api-ai-awale@example.test", display_name="API Awalé", password="motdepasse")
    client = APIClient()
    client.force_authenticate(user)
    response = client.post("/api/games/", {
        "mode": "ai",
        "game_type": "awale",
        "configuration": {"side": "player0", "level": "beginner"},
    }, format="json")
    assert response.status_code == 201
    game_id = response.data["id"]
    response = client.post(f"/api/awale/games/{game_id}/moves/", {
        "pit": 0,
        "revision": 0,
        "request_id": str(uuid.uuid4()),
    }, format="json")
    assert response.status_code == 200
    response = client.post(f"/api/awale/games/{game_id}/ai-turn/")
    assert response.status_code == 200
    assert response.data["revision"] == 2
    assert len(response.data["history"]) == 2
