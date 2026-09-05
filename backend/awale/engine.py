import copy
import json


RULESET = "abapa_tablechat_v1"
TOTAL_SEEDS = 48


class AwaleRuleError(ValueError):
    pass


def _camp(player):
    return range(0, 6) if player == 0 else range(6, 12)


def _opponent_camp(player):
    return _camp(1 - player)


def position_key(state):
    return json.dumps(
        [state["ruleset"], state["pits"], state["scores"], state["current_player"]],
        separators=(",", ":"),
    )


def initial_state():
    state = {
        "ruleset": RULESET,
        "pits": [4] * 12,
        "scores": [0, 0],
        "current_player": 0,
        "revision": 0,
        "last_move": {},
        "position_counts": {},
    }
    state["position_counts"][position_key(state)] = 1
    return state


def _validate_state(state):
    pits = state.get("pits", [])
    scores = state.get("scores", [])
    if len(pits) != 12 or len(scores) != 2:
        raise AwaleRuleError("État d’Awalé invalide.")
    values = [*pits, *scores]
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in values):
        raise AwaleRuleError("Les graines doivent être des entiers positifs ou nuls.")
    if sum(values) != TOTAL_SEEDS:
        raise AwaleRuleError("L’invariant des 48 graines n’est pas respecté.")
    if state.get("current_player") not in {0, 1} or state.get("ruleset") != RULESET:
        raise AwaleRuleError("État d’Awalé invalide.")


def _sow_pits(pits, pit):
    result = list(pits)
    seeds = result[pit]
    result[pit] = 0
    cursor = pit
    path = []
    while seeds:
        cursor = (cursor + 1) % 12
        if cursor == pit:
            continue
        result[cursor] += 1
        path.append(cursor)
        seeds -= 1
    return result, path


def sow(state, pit):
    _validate_state(state)
    if not isinstance(pit, int) or isinstance(pit, bool) or pit not in range(12):
        raise AwaleRuleError("Trou hors limites.")
    if state["pits"][pit] == 0:
        raise AwaleRuleError("Ce trou est vide.")
    result = copy.deepcopy(state)
    result["pits"], path = _sow_pits(state["pits"], pit)
    return result, path


def legal_moves(state):
    _validate_state(state)
    player = state["current_player"]
    candidates = [pit for pit in _camp(player) if state["pits"][pit] > 0]
    opponent = list(_opponent_camp(player))
    if sum(state["pits"][pit] for pit in opponent) > 0:
        return candidates
    return [
        pit for pit in candidates
        if sum(_sow_pits(state["pits"], pit)[0][index] for index in opponent) > 0
    ]


def capture_candidates(state, last_pit):
    _validate_state(state)
    opponent = set(_opponent_camp(state["current_player"]))
    if last_pit not in opponent or state["pits"][last_pit] not in {2, 3}:
        return []
    captures = []
    cursor = last_pit
    while cursor in opponent and state["pits"][cursor] in {2, 3}:
        captures.append(cursor)
        cursor = (cursor - 1) % 12
    return captures


def finalize_game(state, reason):
    _validate_state(state)
    result = copy.deepcopy(state)
    if reason in {"no_legal_move", "threefold_repetition"}:
        result["scores"][0] += sum(result["pits"][0:6])
        result["scores"][1] += sum(result["pits"][6:12])
        result["pits"] = [0] * 12
    if result["scores"][0] > result["scores"][1]:
        game_result = "1-0"
    elif result["scores"][1] > result["scores"][0]:
        game_result = "0-1"
    else:
        game_result = "1/2-1/2"
    _validate_state(result)
    return result, {"result": game_result, "end_reason": reason}


def apply_move(state, pit):
    _validate_state(state)
    moves = legal_moves(state)
    if pit not in moves:
        if not isinstance(pit, int) or isinstance(pit, bool) or pit not in range(12):
            raise AwaleRuleError("Trou hors limites.")
        if pit not in _camp(state["current_player"]):
            raise AwaleRuleError("Choisissez un trou de votre camp.")
        if state["pits"][pit] == 0:
            raise AwaleRuleError("Ce trou est vide.")
        raise AwaleRuleError("Vous devez nourrir votre adversaire.")

    result, path = sow(state, pit)
    candidates = capture_candidates(result, path[-1])
    opponent = list(_opponent_camp(state["current_player"]))
    remaining = sum(result["pits"][index] for index in opponent if index not in candidates)
    capture_cancelled = bool(candidates and remaining == 0)
    captures = [] if capture_cancelled else candidates
    captured_seeds = sum(result["pits"][index] for index in captures)
    for index in captures:
        result["pits"][index] = 0
    result["scores"][state["current_player"]] += captured_seeds
    result["revision"] = state.get("revision", 0) + 1
    events = {
        "pit": pit,
        "path": path,
        "captures": captures,
        "capture_candidates": candidates,
        "capture_cancelled": capture_cancelled,
        "captured_seeds": captured_seeds,
    }
    result["last_move"] = events

    outcome = None
    if result["scores"][0] >= 25 or result["scores"][1] >= 25:
        winner = 0 if result["scores"][0] >= 25 else 1
        outcome = {"result": "1-0" if winner == 0 else "0-1", "end_reason": "majority"}
    elif result["scores"] == [24, 24]:
        outcome = {"result": "1/2-1/2", "end_reason": "24-24"}
    else:
        result["current_player"] = 1 - state["current_player"]
        key = position_key(result)
        counts = copy.deepcopy(state.get("position_counts", {}))
        counts[key] = counts.get(key, 0) + 1
        result["position_counts"] = counts
        if not legal_moves(result):
            result, outcome = finalize_game(result, "no_legal_move")
        elif counts[key] >= 3:
            result, outcome = finalize_game(result, "threefold_repetition")

    _validate_state(result)
    return result, events, outcome

