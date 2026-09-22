from django.conf import settings
from rest_framework.permissions import BasePermission


class IsEmailVerified(BasePermission):
    message = "Vérifiez votre adresse email pour utiliser la messagerie."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (not settings.REQUIRE_EMAIL_VERIFICATION or request.user.email_verified_at)
        )
