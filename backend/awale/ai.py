import random
import time

from .engine import apply_move, legal_moves


LEVELS = {
    "beginner": {"time": 0.08, "depth": 3, "mistake": 0.3},
    "intermediate": {"time": 0.3, "depth": 6, "mistake": 0.0},
    "advanced": {"time": 0.9, "depth": 9, "mistake": 0.0},
}


class SearchTimeout(Exception):
    pass


def _terminal_value(outcome, root):
    if not outcome:
        return None
    if outcome["result"] == "1/2-1/2":
        return 0
    winner = 0 if outcome["result"] == "1-0" else 1
    return 100000 if winner == root else -100000


def _evaluate(state, root):
    opponent = 1 - root
    score = (state["scores"][root] - state["scores"][opponent]) * 100
    own_seeds = sum(state["pits"][0:6] if root == 0 else state["pits"][6:12])
    opponent_seeds = sum(state["pits"][6:12] if root == 0 else state["pits"][0:6])
    mobility = len(legal_moves(state))
    mobility = mobility if state["current_player"] == root else -mobility
    return score + own_seeds - opponent_seeds + mobility * 2


def _search(state, depth, alpha, beta, root, deadline):
    if time.monotonic() >= deadline:
        raise SearchTimeout
    if depth == 0:
        return _evaluate(state, root)
    moves = legal_moves(state)
    if not moves:
        return _evaluate(state, root)
    maximizing = state["current_player"] == root
    value = -float("inf") if maximizing else float("inf")
    for pit in moves:
        child, _, outcome = apply_move(state, pit)
        terminal = _terminal_value(outcome, root)
        candidate = terminal if terminal is not None else _search(child, depth - 1, alpha, beta, root, deadline)
        if maximizing:
            value = max(value, candidate)
            alpha = max(alpha, value)
        else:
            value = min(value, candidate)
            beta = min(beta, value)
        if beta <= alpha:
            break
    return value


def choose_move(state, level="beginner"):
    settings = LEVELS.get(level, LEVELS["beginner"])
    moves = legal_moves(state)
    if not moves:
        raise ValueError("Aucun coup légal.")
    root = state["current_player"]
    deadline = time.monotonic() + settings["time"]
    best_move = moves[0]
    completed_scores = []
    for depth in range(1, settings["depth"] + 1):
        scores = []
        try:
            for pit in moves:
                child, _, outcome = apply_move(state, pit)
                terminal = _terminal_value(outcome, root)
                score = terminal if terminal is not None else _search(child, depth - 1, -float("inf"), float("inf"), root, deadline)
                scores.append((score, pit))
        except SearchTimeout:
            break
        completed_scores = sorted(scores, reverse=True)
        best_move = completed_scores[0][1]
    if settings["mistake"] and len(moves) > 1 and random.random() < settings["mistake"]:
        alternatives = [pit for _, pit in completed_scores[1:]] if completed_scores else moves[1:]
        if alternatives:
            return random.choice(alternatives)
    return best_move

