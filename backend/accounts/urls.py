from django.urls import path

from .views import CsrfView, HealthView, LoginView, LogoutView, MeView, RegisterView, UserSearchView

urlpatterns = [
    path("health/", HealthView.as_view()),
    path("auth/csrf/", CsrfView.as_view()),
    path("auth/register/", RegisterView.as_view()),
    path("auth/login/", LoginView.as_view()),
    path("auth/logout/", LogoutView.as_view()),
    path("me/", MeView.as_view()),
    path("users/search/", UserSearchView.as_view()),
]
