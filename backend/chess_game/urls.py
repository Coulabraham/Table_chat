from django.urls import path
from .views import AiTurnView, EngineView, LessonAttemptView, LessonDetailView, LessonHintView, LessonListView, LessonStartView, LessonUndoView, MoveView, StateView

urlpatterns = [
    path("games/<uuid:game_id>/state/", StateView.as_view()),
    path("games/<uuid:game_id>/moves/", MoveView.as_view()),
    path("games/<uuid:game_id>/ai-turn/", AiTurnView.as_view()),
    path("engine/", EngineView.as_view()),
    path("lessons/", LessonListView.as_view()),
    path("lessons/<int:pk>/", LessonDetailView.as_view()),
    path("lessons/<int:pk>/attempt/", LessonAttemptView.as_view()),
    path("lessons/<int:pk>/start/", LessonStartView.as_view()),
    path("lessons/<int:pk>/hint/", LessonHintView.as_view()),
    path("lessons/<int:pk>/undo/", LessonUndoView.as_view()),
]
