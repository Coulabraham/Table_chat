from django.urls import path
from .views import FriendshipActionView, FriendshipListCreateView

urlpatterns = [
    path("", FriendshipListCreateView.as_view()),
    path("<int:pk>/<str:action>/", FriendshipActionView.as_view()),
]
