from rest_framework.permissions import BasePermission

from .access import can_use_private_messaging


class IsEmailVerified(BasePermission):
    message = "Vérifiez votre adresse email pour utiliser la messagerie."

    def has_permission(self, request, view):
        return can_use_private_messaging(request.user)
