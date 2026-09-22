from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.auth import login, logout
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from chat.models import Conversation

from .models import AccountSession, User, UserBlock
from .permissions import IsEmailVerified
from .serializers import (
    AccountSessionSerializer,
    CreateUserBlockSerializer,
    LoginSerializer,
    MeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PublicUserSerializer,
    RegisterSerializer,
    TokenSerializer,
    UserBlockSerializer,
)
from .services import (
    InvalidAccountToken,
    notify_revoked_sessions,
    request_password_reset,
    reset_password,
    send_verification_email,
    sync_account_sessions,
    track_request_session,
    verify_email,
)
from .throttles import AuthRateThrottle, EmailActionThrottle


class CsrfView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class HealthView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({"status": "ok"})


@method_decorator(csrf_protect, name="dispatch")
class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        if not settings.REQUIRE_EMAIL_VERIFICATION:
            user.email_verified_at = timezone.now()
            user.save(update_fields=("email_verified_at",))
        login(request, user)
        track_request_session(request)
        data = MeSerializer(user).data
        data["verification_email_sent"] = (
            send_verification_email(user) if settings.REQUIRE_EMAIL_VERIFICATION else False
        )
        return Response(data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        login(request, serializer.validated_data["user"])
        track_request_session(request)
        return Response(MeSerializer(serializer.validated_data["user"]).data)


class LogoutView(APIView):
    def post(self, request):
        session_key = request.session.session_key
        logout(request)
        if session_key:
            notify_revoked_sessions([session_key])
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    def get(self, request):
        return Response(MeSerializer(request.user).data)

    def patch(self, request):
        serializer = MeSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class UserSearchView(APIView):
    permission_classes = [IsEmailVerified]

    def get(self, request):
        query = request.query_params.get("public_id", "").strip().lower()
        if len(query) < 3:
            return Response([])
        users = User.objects.filter(public_id=query, is_active=True)
        if settings.REQUIRE_EMAIL_VERIFICATION:
            users = users.filter(email_verified_at__isnull=False)
        users = users.exclude(pk=request.user.pk)[:5]
        return Response(PublicUserSerializer(users, many=True).data)


@method_decorator(csrf_protect, name="dispatch")
class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [EmailActionThrottle]

    def post(self, request):
        serializer = TokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = verify_email(serializer.validated_data["token"])
        except InvalidAccountToken:
            return Response(
                {"error": {"status": 400, "details": "Lien invalide, expiré ou déjà utilisé."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"detail": "Adresse email vérifiée.", "user": MeSerializer(user).data})


@method_decorator(csrf_protect, name="dispatch")
class ResendVerificationView(APIView):
    throttle_classes = [EmailActionThrottle]

    def post(self, request):
        if request.user.email_verified_at:
            return Response({"detail": "Cette adresse est déjà vérifiée."})
        sent = send_verification_email(request.user)
        if not sent:
            return Response(
                {"error": {"status": 503, "details": "L’email n’a pas pu être déposé. Réessayez plus tard."}},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"detail": "Un nouveau lien de vérification a été envoyé."})


@method_decorator(csrf_protect, name="dispatch")
class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [EmailActionThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_password_reset(serializer.validated_data["email"])
        return Response(
            {"detail": "Si cette adresse correspond à un compte, un lien temporaire a été envoyé."},
            status=status.HTTP_202_ACCEPTED,
        )


@method_decorator(csrf_protect, name="dispatch")
class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [EmailActionThrottle]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            reset_password(serializer.validated_data["token"], serializer.validated_data["new_password"])
        except InvalidAccountToken:
            return Response(
                {"error": {"status": 400, "details": "Lien invalide, expiré ou déjà utilisé."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except DjangoValidationError as exc:
            return Response(
                {"error": {"status": 400, "details": list(exc.messages)}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"detail": "Mot de passe modifié. Toutes les sessions existantes ont été déconnectées."})


class SessionListView(APIView):
    def get(self, request):
        AccountSession.objects.filter(user=request.user, session__expire_date__lte=timezone.now()).delete()
        sync_account_sessions(request.user)
        track_request_session(request)
        sessions = request.user.account_sessions.select_related("session")
        return Response(AccountSessionSerializer(sessions, many=True, context={"request": request}).data)


class SessionRevokeView(APIView):
    def delete(self, request, session_id):
        record = get_object_or_404(AccountSession, pk=session_id, user=request.user)
        if record.session_id == request.session.session_key:
            return Response(
                {"error": {"status": 400, "details": "Utilisez Déconnexion pour fermer la session actuelle."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        key = record.session_id
        record.session.delete()
        notify_revoked_sessions([key])
        return Response(status=status.HTTP_204_NO_CONTENT)


class OtherSessionsRevokeView(APIView):
    def delete(self, request):
        current_key = request.session.session_key
        sync_account_sessions(request.user)
        records = list(request.user.account_sessions.exclude(session_id=current_key))
        keys = [record.session_id for record in records]
        if keys:
            from django.contrib.sessions.models import Session

            Session.objects.filter(session_key__in=keys).delete()
            notify_revoked_sessions(keys)
        return Response({"revoked": len(keys)})


class UserBlockListCreateView(APIView):
    def get(self, request):
        blocks = request.user.blocks_created.select_related("blocked")
        return Response(UserBlockSerializer(blocks, many=True).data)

    def post(self, request):
        serializer = CreateUserBlockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target = get_object_or_404(User, public_id=serializer.validated_data["public_id"].lower(), is_active=True)
        if target.pk == request.user.pk:
            return Response(
                {"error": {"status": 400, "details": "Vous ne pouvez pas bloquer votre propre compte."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            list(User.objects.select_for_update().filter(pk__in=sorted((request.user.pk, target.pk))))
            block, _ = UserBlock.objects.get_or_create(blocker=request.user, blocked=target)
        conversation = Conversation.objects.filter(
            user_low_id=min(request.user.pk, target.pk), user_high_id=max(request.user.pk, target.pk)
        ).first()
        if conversation:
            async_to_sync(get_channel_layer().group_send)(
                f"conversation_{conversation.pk}", {"type": "access.changed"}
            )
        return Response(UserBlockSerializer(block).data, status=status.HTTP_201_CREATED)


class UserBlockDeleteView(APIView):
    def delete(self, request, public_id):
        block = get_object_or_404(UserBlock, blocker=request.user, blocked__public_id=public_id.lower())
        block.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
