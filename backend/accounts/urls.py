from django.urls import path

from .views import (
    CsrfView,
    HealthView,
    LoginView,
    LogoutView,
    MeView,
    OtherSessionsRevokeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    ResendVerificationView,
    SessionListView,
    SessionRevokeView,
    UserBlockDeleteView,
    UserBlockListCreateView,
    UserSearchView,
    VerifyEmailView,
)

urlpatterns = [
    path("health/", HealthView.as_view()),
    path("auth/csrf/", CsrfView.as_view()),
    path("auth/register/", RegisterView.as_view()),
    path("auth/login/", LoginView.as_view()),
    path("auth/logout/", LogoutView.as_view()),
    path("auth/email/verify/", VerifyEmailView.as_view()),
    path("auth/email/resend/", ResendVerificationView.as_view()),
    path("auth/password-reset/request/", PasswordResetRequestView.as_view()),
    path("auth/password-reset/confirm/", PasswordResetConfirmView.as_view()),
    path("me/", MeView.as_view()),
    path("sessions/", SessionListView.as_view()),
    path("sessions/others/", OtherSessionsRevokeView.as_view()),
    path("sessions/<uuid:session_id>/", SessionRevokeView.as_view()),
    path("blocks/", UserBlockListCreateView.as_view()),
    path("blocks/<str:public_id>/", UserBlockDeleteView.as_view()),
    path("users/search/", UserSearchView.as_view()),
]
