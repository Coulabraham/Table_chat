import copy

import pytest

from awale.engine import (
    AwaleRuleError,
    apply_move,
    capture_candidates,
    finalize_game,
    initial_state,
    legal_moves,
    position_key,
    sow,
)


def make_state(pits, current_player=0, scores=None):
    remaining = 48 - sum(pits)
    scores = scores or [min(24, remaining), remaining - min(24, remaining)]
    state = {
        "ruleset": "abapa_tablechat_v1",
        "pits": pits,
        "scores": scores,
        "current_player": current_player,
        "revision": 0,
        "last_move": {},
        "position_counts": {},
    }
    state["position_counts"] = {position_key(state): 1}
    return state


def test_initial_position_and_first_six_moves():
    state = initial_state()
    assert state["pits"] == [4] * 12
    assert state["scores"] == [0, 0]
    assert legal_moves(state) == [0, 1, 2, 3, 4, 5]
    moved, events, outcome = apply_move(state, 0)
    assert moved["pits"] == [0, 5, 5, 5, 5, 4, 4, 4, 4, 4, 4, 4]
    assert events["path"] == [1, 2, 3, 4]
    assert outcome is None
    assert state == initial_state()


@pytest.mark.parametrize("pit", [-1, 6, 12])
def test_rejects_out_of_bounds_and_opponent_pits(pit):
    with pytest.raises(AwaleRuleError):
        apply_move(initial_state(), pit)


def test_rejects_an_empty_pit_and_skips_origin_on_long_sow():
    empty = make_state([0, 8, 8, 8, 8, 8, 4, 1, 1, 1, 0, 0])
    with pytest.raises(AwaleRuleError, match="vide"):
        apply_move(empty, 0)
    long = make_state([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 14])
    moved, path = sow(long, 11)
    assert len(path) == 14
    assert 11 not in path
    assert moved["pits"][0] == 2


def test_simple_multiple_and_interrupted_captures():
    simple = make_state([8, 7, 7, 7, 7, 1, 1, 4, 1, 1, 1, 1])
    moved, events, _ = apply_move(simple, 5)
    assert events["captures"] == [6]
    assert moved["scores"][0] == simple["scores"][0] + 2

    multiple = make_state([6, 6, 6, 6, 6, 3, 1, 1, 1, 4, 1, 1])
    moved, events, _ = apply_move(multiple, 5)
    assert events["captures"] == [8, 7, 6]
    assert events["captured_seeds"] == 6

    interrupted = make_state([6, 6, 6, 6, 6, 3, 1, 4, 1, 1, 1, 1])
    sown, path = sow(interrupted, 5)
    assert capture_candidates(sown, path[-1]) == [8]


def test_capture_that_would_starve_opponent_is_cancelled():
    state = make_state([9, 9, 9, 9, 9, 1, 1, 0, 0, 0, 0, 0])
    moved, events, _ = apply_move(state, 5)
    assert events["capture_candidates"] == [6]
    assert events["capture_cancelled"] is True
    assert events["captures"] == []
    assert moved["pits"][6] == 2


def test_feeding_is_required_and_detects_when_impossible():
    state = make_state([0, 0, 0, 0, 1, 47, 0, 0, 0, 0, 0, 0])
    assert legal_moves(state) == [5]
    with pytest.raises(AwaleRuleError, match="nourrir"):
        apply_move(state, 4)
    impossible = make_state([1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    assert legal_moves(impossible) == []


def test_majority_final_count_and_draw():
    majority = make_state([0, 0, 0, 0, 0, 1, 1, 4, 0, 0, 0, 0], scores=[24, 18])
    moved, _, outcome = apply_move(majority, 5)
    assert moved["scores"][0] == 26
    assert outcome == {"result": "1-0", "end_reason": "majority"}
    assert sum(moved["pits"]) + sum(moved["scores"]) == 48

    counted, outcome = finalize_game(make_state([1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]), "no_legal_move")
    assert counted["pits"] == [0] * 12
    assert sum(counted["scores"]) == 48
    assert outcome["result"] == "1-0"

    drawn, outcome = finalize_game(make_state([0] * 12, scores=[24, 24]), "threefold_repetition")
    assert drawn["scores"] == [24, 24]
    assert outcome["result"] == "1/2-1/2"


def test_third_position_occurrence_triggers_final_count():
    state = initial_state()
    preview, _, _ = apply_move(state, 0)
    key = position_key(preview)
    state = copy.deepcopy(state)
    state["position_counts"][key] = 2
    moved, _, outcome = apply_move(state, 0)
    assert outcome["end_reason"] == "threefold_repetition"
    assert moved["pits"] == [0] * 12
    assert sum(moved["scores"]) == 48


def test_seed_invariant_survives_a_sequence():
    state = initial_state()
    for _ in range(100):
        moves = legal_moves(state)
        if not moves:
            break
        state, _, outcome = apply_move(state, moves[0])
        assert sum(state["pits"]) + sum(state["scores"]) == 48
        if outcome:
            break

