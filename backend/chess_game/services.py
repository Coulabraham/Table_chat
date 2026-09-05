import chess
import chess.pgn
from io import StringIO

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from games.models import Game, GameParticipant
from .models import ChessState, ProcessedMove


def serialize_state(state):
    return {
        "game_id": str(state.game_id),
        "fen": state.fen,
        "initial_fen": state.initial_fen,
        "moves": state.moves,
        "pgn": state.pgn,
        "revision": state.revision,
        "status": state.game.status,
        "result": state.game.result,
        "end_reason": state.game.end_reason,
    }


def board_to_pgn(initial_fen, moves):
    board = chess.Board(initial_fen)
    game = chess.pgn.Game()
    game.setup(board)
    node = game
    for item in moves:
        move = chess.Move.from_uci(item["uci"])
        node = node.add_variation(move)
        board.push(move)
    return str(game)


@transaction.atomic
def apply_move(*, game_id, user, uci, request_id, expected_revision):
    state = ChessState.objects.select_for_update().select_related("game").get(game_id=game_id)
    duplicate = ProcessedMove.objects.filter(state=state, user=user, request_id=request_id).first()
    if duplicate:
        return duplicate.response
    try:
        participant = GameParticipant.objects.get(game_id=game_id, user=user)
    except GameParticipant.DoesNotExist as exc:
        raise PermissionDenied("Vous ne participez pas à cette partie.") from exc
    if state.game.status != Game.Status.IN_PROGRESS:
        raise ValidationError("La partie n’est pas active.")
    if state.revision != expected_revision:
        raise ValidationError({"revision": "État périmé : resynchronisation nécessaire.", "state": serialize_state(state)})
    board = chess.Board(state.fen)
    expected_role = "white" if board.turn == chess.WHITE else "black"
    if participant.role != expected_role:
        raise ValidationError("Ce n’est pas votre tour.")
    try:
        move = chess.Move.from_uci(uci)
    except ValueError as exc:
        raise ValidationError("Format de coup invalide.") from exc
    if move not in board.legal_moves:
        raise ValidationError("Ce coup est illégal.")
    san = board.san(move)
    board.push(move)
    state.moves = [*state.moves, {"ply": len(state.moves) + 1, "uci": uci, "san": san}]
    state.fen = board.fen()
    state.revision += 1
    state.pgn = board_to_pgn(state.initial_fen, state.moves)
    if board.is_game_over(claim_draw=False):
        outcome = board.outcome(claim_draw=False)
        state.game.status = Game.Status.FINISHED
        state.game.result = outcome.result() if outcome else "*"
        state.game.end_reason = outcome.termination.name.lower() if outcome else ""
        state.game.finished_at = timezone.now()
        state.game.save(update_fields=("status", "result", "end_reason", "finished_at"))
    state.save()
    response = serialize_state(state)
    ProcessedMove.objects.create(state=state, user=user, request_id=request_id, response=response)
    return response


@transaction.atomic
def apply_engine_move(*, game_id, uci):
    state = ChessState.objects.select_for_update().select_related("game").get(game_id=game_id)
    if state.game.mode != Game.Mode.AI or state.game.status != Game.Status.IN_PROGRESS:
        raise ValidationError("Cette partie ne peut pas recevoir de coup IA.")
    player = state.game.participants.get()
    board = chess.Board(state.fen)
    engine_role = "black" if player.role == "white" else "white"
    expected_role = "white" if board.turn == chess.WHITE else "black"
    if expected_role != engine_role:
        raise ValidationError("Ce n’est pas au moteur de jouer.")
    move = chess.Move.from_uci(uci)
    if move not in board.legal_moves:
        raise ValidationError("Le moteur a proposé un coup illégal.")
    san = board.san(move)
    board.push(move)
    state.moves = [*state.moves, {"ply": len(state.moves) + 1, "uci": uci, "san": san}]
    state.fen = board.fen()
    state.revision += 1
    state.pgn = board_to_pgn(state.initial_fen, state.moves)
    if board.is_game_over(claim_draw=False):
        outcome = board.outcome(claim_draw=False)
        state.game.status = Game.Status.FINISHED
        state.game.result = outcome.result() if outcome else "*"
        state.game.end_reason = outcome.termination.name.lower() if outcome else ""
        state.game.finished_at = timezone.now()
        state.game.save()
    state.save()
    return serialize_state(state)
