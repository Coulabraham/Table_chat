from django.urls import path
from .views import CsrfView, LoginView, LogoutView, MeView, RegisterView, UserSearchView

urlpatterns = [
    path("csrf/", CsrfView.as_view()),
    path("register/", RegisterView.as_view()),
    path("login/", LoginView.as_view()),
    path("logout/", LogoutView.as_view()),
    path("me/", MeView.as_view()),
    path("users/", UserSearchView.as_view()),
]

