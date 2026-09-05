from celery import shared_task

from .ai import choose_move
from .models import AwaleGameState
from .services import apply_ai_move, engine_state


@shared_task(soft_time_limit=2, time_limit=3)
def play_ai_turn(game_id, expected_revision):
    state = AwaleGameState.objects.select_related("game").get(game_id=game_id)
    if state.revision != expected_revision:
        return {"status": "obsolete"}
    pit = choose_move(engine_state(state), state.game.configuration.get("level", "beginner"))
    return apply_ai_move(game_id=game_id, pit=pit, expected_revision=expected_revision)

