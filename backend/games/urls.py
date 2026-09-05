from django.urls import path
from .views import GameActionView, GameDetailView, GameListCreateView, InvitationActionView, InvitationListCreateView

urlpatterns = [
    path("", GameListCreateView.as_view()),
    path("invitations/", InvitationListCreateView.as_view()),
    path("invitations/<uuid:pk>/<str:action>/", InvitationActionView.as_view()),
    path("<uuid:pk>/<str:action>/", GameActionView.as_view()),
    path("<uuid:pk>/", GameDetailView.as_view()),
]
