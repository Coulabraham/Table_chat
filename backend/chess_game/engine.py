from django.conf import settings
from stockfish import Stockfish

LEVELS = {
    "decouverte": {"depth": 2, "skill": 0, "time_ms": 150},
    "club": {"depth": 8, "skill": 6, "time_ms": 500},
    "confirme": {"depth": 14, "skill": 12, "time_ms": 1200},
    "expert": {"depth": 18, "skill": 18, "time_ms": 2500},
}


def best_move(fen, level):
    config = LEVELS.get(level)
    if not config:
        raise ValueError("Niveau inconnu")
    engine = Stockfish(path=settings.STOCKFISH_PATH, depth=config["depth"], parameters={"Skill Level": config["skill"], "Threads": 1, "Hash": 32})
    engine.set_fen_position(fen)
    return engine.get_best_move_time(config["time_ms"])

