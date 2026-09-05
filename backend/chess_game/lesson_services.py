import chess

from django.db import transaction
from django.utils import timezone

from .models import Lesson, LessonProgress


def _messages(lesson):
    return {
        "intro": lesson.coach_messages.get("intro", lesson.instruction),
        "success": lesson.coach_messages.get("success", "Très bien. Observez maintenant la réponse adverse."),
        "retry": lesson.coach_messages.get("retry", "Ce coup est légal, mais il ne réalise pas encore l’idée de la leçon."),
        "complete": lesson.coach_messages.get("complete", lesson.explanation),
    }


def serialize_session(progress, lesson):
    return {
        "fen": progress.current_fen or lesson.initial_fen,
        "current_ply": progress.current_ply,
        "completed": progress.completed,
        "attempts": progress.attempts,
        "hint_stage": progress.hint_stage,
        "coach_message": progress.last_feedback or _messages(lesson)["intro"],
        "can_undo": bool(progress.history),
    }


def initialize_progress(progress, lesson, *, save=True):
    progress.current_fen = lesson.initial_fen
    progress.current_ply = 0
    progress.active_lines = list(range(len(lesson.accepted_lines)))
    progress.history = []
    progress.hint_stage = 0
    progress.last_feedback = _messages(lesson)["intro"]
    progress.completed = False
    progress.completed_at = None
    if save:
        progress.save()
    return progress


@transaction.atomic
def start_lesson(user, lesson, *, reset=False):
    progress, created = LessonProgress.objects.select_for_update().get_or_create(user=user, lesson=lesson)
    if created or reset or not progress.current_fen:
        initialize_progress(progress, lesson)
    return serialize_session(progress, lesson)


@transaction.atomic
def play_lesson_move(user, lesson, uci):
    progress, created = LessonProgress.objects.select_for_update().get_or_create(user=user, lesson=lesson)
    if created or not progress.current_fen:
        initialize_progress(progress, lesson, save=False)
    messages = _messages(lesson)
    board = chess.Board(progress.current_fen)
    try:
        move = chess.Move.from_uci(uci)
    except ValueError:
        move = None
    progress.attempts += 1
    if move is None or move not in board.legal_moves:
        progress.last_feedback = "Ce coup n’est pas légal dans cette position. Regardez quelles cases la pièce peut atteindre."
        progress.save()
        return {**serialize_session(progress, lesson), "correct": False, "opponent_move": None}

    active = progress.active_lines or list(range(len(lesson.accepted_lines)))
    matching = [index for index in active if len(lesson.accepted_lines[index]) > progress.current_ply and lesson.accepted_lines[index][progress.current_ply] == uci]
    if not matching:
        progress.last_feedback = messages["retry"]
        progress.save()
        return {**serialize_session(progress, lesson), "correct": False, "opponent_move": None}

    progress.history = [*progress.history, {
        "fen": progress.current_fen,
        "current_ply": progress.current_ply,
        "active_lines": active,
        "feedback": progress.last_feedback,
    }]
    board.push(move)
    current_ply = progress.current_ply + 1
    opponent_move = None

    # Le maître joue automatiquement la réponse prévue, comme dans une leçon guidée.
    lines_with_reply = [index for index in matching if len(lesson.accepted_lines[index]) > current_ply]
    if lines_with_reply:
        reply_uci = lesson.accepted_lines[lines_with_reply[0]][current_ply]
        reply = chess.Move.from_uci(reply_uci)
        if reply not in board.legal_moves:
            raise ValueError(f"Variante pédagogique invalide au coup {reply_uci}")
        board.push(reply)
        opponent_move = reply_uci
        matching = [index for index in lines_with_reply if lesson.accepted_lines[index][current_ply] == reply_uci]
        current_ply += 1

    completed = all(len(lesson.accepted_lines[index]) <= current_ply for index in matching)
    progress.current_fen = board.fen()
    progress.current_ply = current_ply
    progress.active_lines = matching
    progress.completed = completed
    progress.last_feedback = messages["complete"] if completed else messages["success"]
    if completed:
        progress.completed_at = timezone.now()
    progress.save()
    return {**serialize_session(progress, lesson), "correct": True, "opponent_move": opponent_move}


@transaction.atomic
def reveal_hint(user, lesson):
    progress, created = LessonProgress.objects.select_for_update().get_or_create(user=user, lesson=lesson)
    if created or not progress.current_fen:
        initialize_progress(progress, lesson, save=False)
    hints = lesson.hints or [lesson.hint]
    stage = min(progress.hint_stage, max(0, len(hints) - 1))
    progress.hint_used = True
    progress.hint_stage = min(progress.hint_stage + 1, len(hints))
    progress.save()
    return {"hint": hints[stage] if hints else "Observez les échecs, les prises et les menaces.", "hint_stage": progress.hint_stage, "has_more": progress.hint_stage < len(hints)}


@transaction.atomic
def undo_lesson_move(user, lesson):
    progress = LessonProgress.objects.select_for_update().get(user=user, lesson=lesson)
    if not progress.history:
        return serialize_session(progress, lesson)
    history = list(progress.history)
    snapshot = history.pop()
    progress.current_fen = snapshot["fen"]
    progress.current_ply = snapshot["current_ply"]
    progress.active_lines = snapshot["active_lines"]
    progress.last_feedback = "Reprenons juste avant votre dernier coup. Essayez une autre idée."
    progress.history = history
    progress.completed = False
    progress.completed_at = None
    progress.save()
    return serialize_session(progress, lesson)
