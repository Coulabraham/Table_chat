import pytest

from accounts.models import User
from chess_game.lesson_services import play_lesson_move, reveal_hint, start_lesson, undo_lesson_move
from chess_game.models import Lesson


@pytest.mark.django_db(transaction=True)
def test_guided_lesson_gives_feedback_plays_reply_and_resumes():
    user = User.objects.create_user(email="student@example.test", display_name="Élève", password="motdepasse")
    lesson = Lesson.objects.create(
        title="Fourchette guidée",
        instruction="Gagnez la dame.",
        initial_fen="8/3q1k2/8/8/8/5N2/8/4K3 w - - 0 1",
        side_to_move="white",
        objective="Exploiter une fourchette",
        difficulty="Intermédiaire",
        accepted_lines=[["f3e5", "f7e6", "e5d7"]],
        hint="Cherchez un échec.",
        hints=["Cherchez un échec.", "Le cavalier vise d7."],
        coach_messages={"intro": "Repérez les deux cibles.", "success": "Le roi fuit ; gagnez la dame.", "retry": "Cherchez une double attaque.", "complete": "Fourchette réussie."},
        explanation="La dame est gagnée.",
    )
    session = start_lesson(user, lesson)
    assert session["current_ply"] == 0

    wrong = play_lesson_move(user, lesson, "f3g5")
    assert not wrong["correct"]
    assert wrong["fen"] == lesson.initial_fen

    first_hint = reveal_hint(user, lesson)
    second_hint = reveal_hint(user, lesson)
    assert first_hint["hint"] != second_hint["hint"]

    first = play_lesson_move(user, lesson, "f3e5")
    assert first["correct"] and not first["completed"]
    assert first["opponent_move"] == "f7e6"
    assert first["current_ply"] == 2

    resumed = start_lesson(user, lesson)
    assert resumed["fen"] == first["fen"]
    restored = undo_lesson_move(user, lesson)
    assert restored["fen"] == lesson.initial_fen

    play_lesson_move(user, lesson, "f3e5")
    finished = play_lesson_move(user, lesson, "e5d7")
    assert finished["correct"] and finished["completed"]
