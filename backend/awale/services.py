from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from games.models import Game, GameParticipant
from .engine import AwaleRuleError, apply_move as apply_rules, legal_moves
from .models import AwaleGameState, AwaleMove, ProcessedAwaleMove


def engine_state(state):
    return {
        "ruleset": state.ruleset,
        "pits": list(state.pits),
        "scores": list(state.scores),
        "current_player": state.current_player,
        "revision": state.revision,
        "last_move": dict(state.last_move),
        "position_counts": dict(state.position_counts),
    }


def serialize_state(state):
    raw = engine_state(state)
    history = [
        {
            "move_number": move.move_number,
            "player": move.player,
            "pit": move.pit,
            "path": move.sowing_path,
            "captures": move.captures,
            "capture_cancelled": move.capture_cancelled,
            "author": move.author.display_name if move.author else "TableChat IA",
            "state_after": move.state_after,
        }
        for move in state.moves.select_related("author").all()
    ]
    return {
        "game_id": str(state.game_id),
        **raw,
        "legal_moves": legal_moves(raw) if state.game.status == Game.Status.IN_PROGRESS else [],
        "history": history,
        "status": state.game.status,
        "result": state.game.result,
        "end_reason": state.game.end_reason,
    }


def _save_transition(state, next_state, outcome, *, pit, player, events, author):
    state.pits = next_state["pits"]
    state.scores = next_state["scores"]
    state.current_player = next_state["current_player"]
    state.revision = next_state["revision"]
    state.last_move = next_state["last_move"]
    state.position_counts = next_state["position_counts"]
    state.save()
    AwaleMove.objects.create(
        state=state,
        move_number=state.revision,
        author=author,
        player=player,
        pit=pit,
        sowing_path=events["path"],
        captures=events["captures"],
        capture_cancelled=events["capture_cancelled"],
        state_after={
            "pits": next_state["pits"],
            "scores": next_state["scores"],
            "current_player": next_state["current_player"],
            "revision": next_state["revision"],
        },
    )
    if outcome:
        state.game.status = Game.Status.FINISHED
        state.game.result = outcome["result"]
        state.game.end_reason = outcome["end_reason"]
        state.game.finished_at = timezone.now()
        state.game.save(update_fields=("status", "result", "end_reason", "finished_at"))


@transaction.atomic
def apply_player_move(*, game_id, user, pit, request_id, expected_revision):
    state = AwaleGameState.objects.select_for_update().select_related("game").get(game_id=game_id)
    duplicate = ProcessedAwaleMove.objects.filter(state=state, user=user, request_id=request_id).first()
    if duplicate:
        return duplicate.response
    participant = GameParticipant.objects.filter(game_id=game_id, user=user).first()
    if not participant:
        raise PermissionDenied("Vous ne participez pas à cette partie.")
    if state.game.game_type != Game.Type.AWALE or state.game.status != Game.Status.IN_PROGRESS:
        raise ValidationError("La partie n’est pas active.")
    if state.revision != expected_revision:
        raise ValidationError({"revision": "État périmé : resynchronisation nécessaire.", "state": serialize_state(state)})
    expected_role = f"player{state.current_player}"
    if participant.role != expected_role:
        raise ValidationError("Ce n’est pas votre tour.")
    try:
        pit = int(pit)
        next_state, events, outcome = apply_rules(engine_state(state), pit)
    except (AwaleRuleError, TypeError, ValueError) as exc:
        raise ValidationError(str(exc)) from exc
    _save_transition(state, next_state, outcome, pit=pit, player=state.current_player, events=events, author=user)
    response = serialize_state(state)
    ProcessedAwaleMove.objects.create(state=state, user=user, request_id=request_id, response=response)
    return response


@transaction.atomic
def apply_ai_move(*, game_id, pit, expected_revision):
    state = AwaleGameState.objects.select_for_update().select_related("game").get(game_id=game_id)
    if state.game.mode != Game.Mode.AI or state.game.status != Game.Status.IN_PROGRESS:
        raise ValidationError("Cette partie ne peut pas recevoir de coup IA.")
    if state.revision != expected_revision:
        raise ValidationError("Le résultat de l’IA est devenu obsolète.")
    participant = state.game.participants.get()
    engine_player = 1 if participant.role == "player0" else 0
    if state.current_player != engine_player:
        raise ValidationError("Ce n’est pas au moteur de jouer.")
    try:
        next_state, events, outcome = apply_rules(engine_state(state), int(pit))
    except (AwaleRuleError, TypeError, ValueError) as exc:
        raise ValidationError("Le moteur a proposé un coup illégal.") from exc
    _save_transition(state, next_state, outcome, pit=int(pit), player=engine_player, events=events, author=None)
    return serialize_state(state)
