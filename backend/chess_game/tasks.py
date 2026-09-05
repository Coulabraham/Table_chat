from celery import shared_task
from .engine import best_move


@shared_task(time_limit=8, soft_time_limit=6)
def analyse_position(fen, level="confirme"):
    return {"move": best_move(fen, level)}

