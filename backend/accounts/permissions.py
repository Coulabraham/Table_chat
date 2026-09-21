from rest_framework.permissions import BasePermission


class IsEmailVerified(BasePermission):
    message = "Vérifiez votre adresse email pour utiliser la messagerie."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.email_verified_at)
