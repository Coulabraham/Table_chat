import uuid

import pytest
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts.models import User
from chess_game.models import ChessState
from chess_game.services import apply_move
from games.models import Game, GameParticipant


@pytest.fixture
def match(db):
    white = User.objects.create_user(email="white@example.test", display_name="Blanc", password="motdepasse")
    black = User.objects.create_user(email="black@example.test", display_name="Noir", password="motdepasse")
    outsider = User.objects.create_user(email="third@example.test", display_name="Tiers", password="motdepasse")
    game = Game.objects.create(mode=Game.Mode.HUMAN, status=Game.Status.IN_PROGRESS)
    GameParticipant.objects.create(game=game, user=white, role="white")
    GameParticipant.objects.create(game=game, user=black, role="black")
    ChessState.objects.create(game=game)
    return game, white, black, outsider


@pytest.mark.django_db(transaction=True)
def test_legal_move_is_saved_and_deduplicated(match):
    game, white, _, _ = match
    request_id = uuid.uuid4()
    first = apply_move(game_id=game.id, user=white, uci="e2e4", request_id=request_id, expected_revision=0)
    duplicate = apply_move(game_id=game.id, user=white, uci="e2e4", request_id=request_id, expected_revision=0)
    assert first == duplicate
    assert first["revision"] == 1
    assert first["moves"][0]["san"] == "e4"


@pytest.mark.django_db(transaction=True)
def test_illegal_out_of_turn_and_third_party_are_rejected(match):
    game, white, black, outsider = match
    with pytest.raises(ValidationError):
        apply_move(game_id=game.id, user=white, uci="e2e5", request_id=uuid.uuid4(), expected_revision=0)
    with pytest.raises(ValidationError):
        apply_move(game_id=game.id, user=black, uci="e7e5", request_id=uuid.uuid4(), expected_revision=0)
    with pytest.raises(PermissionDenied):
        apply_move(game_id=game.id, user=outsider, uci="e2e4", request_id=uuid.uuid4(), expected_revision=0)


@pytest.mark.django_db(transaction=True)
def test_castling_and_en_passant_are_supported(match):
    game, white, black, _ = match
    state = ChessState.objects.get(game=game)
    state.fen = "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"
    state.initial_fen = state.fen
    state.save()
    result = apply_move(game_id=game.id, user=white, uci="e1g1", request_id=uuid.uuid4(), expected_revision=0)
    assert result["moves"][0]["san"] == "O-O"

    state.fen = "8/8/8/3pP3/8/8/8/K6k w - d6 0 1"
    state.initial_fen = state.fen
    state.moves = []
    state.revision = 0
    state.save()
    result = apply_move(game_id=game.id, user=white, uci="e5d6", request_id=uuid.uuid4(), expected_revision=0)
    assert result["moves"][0]["san"].startswith("exd6")


@pytest.mark.django_db(transaction=True)
def test_checkmate_immediately_finishes_the_game(match):
    game, white, black, _ = match
    sequence = [
        (white, "f2f3"),
        (black, "e7e5"),
        (white, "g2g4"),
        (black, "d8h4"),
    ]
    result = None
    for revision, (player, uci) in enumerate(sequence):
        result = apply_move(game_id=game.id, user=player, uci=uci, request_id=uuid.uuid4(), expected_revision=revision)
    assert result is not None
    assert result["status"] == Game.Status.FINISHED
    assert result["result"] == "0-1"
    assert result["end_reason"] == "checkmate"
