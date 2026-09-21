from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import LoginSerializer, MeSerializer, PublicUserSerializer, RegisterSerializer
from .throttles import AuthRateThrottle
from .models import User


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
        login(request, user)
        return Response(MeSerializer(user).data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        login(request, serializer.validated_data["user"])
        return Response(MeSerializer(serializer.validated_data["user"]).data)


class LogoutView(APIView):
    def post(self, request):
        user_id = request.user.pk
        logout(request)
        async_to_sync(get_channel_layer().group_send)(f"user_{user_id}", {"type": "session.revoked"})
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
    def get(self, request):
        query = request.query_params.get("public_id", "").strip().lower()
        if len(query) < 3:
            return Response([])
        users = User.objects.filter(public_id=query, is_active=True).exclude(pk=request.user.pk)[:5]
        return Response(PublicUserSerializer(users, many=True).data)
