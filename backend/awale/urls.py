from django.urls import path

from .views import AiTurnView, LessonListView, MoveView, StateView

urlpatterns = [
    path("lessons/", LessonListView.as_view()),
    path("games/<uuid:game_id>/state/", StateView.as_view()),
    path("games/<uuid:game_id>/moves/", MoveView.as_view()),
    path("games/<uuid:game_id>/ai-turn/", AiTurnView.as_view()),
]
