from django.db.models import Q
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Friendship
from .serializers import FriendshipSerializer


class FriendshipListCreateView(generics.ListCreateAPIView):
    serializer_class = FriendshipSerializer

    def get_queryset(self):
        return Friendship.objects.filter(Q(requester=self.request.user) | Q(addressee=self.request.user)).select_related("requester", "addressee")

    def perform_create(self, serializer):
        target = serializer.validated_data["addressee"]
        if target == self.request.user:
            raise ValidationError("Vous ne pouvez pas vous ajouter vous-même.")
        if Friendship.objects.filter(Q(requester=self.request.user, addressee=target) | Q(requester=target, addressee=self.request.user), status__in=["pending", "accepted"]).exists():
            raise ValidationError("Une relation ou demande existe déjà.")
        serializer.save()


class FriendshipActionView(APIView):
    def post(self, request, pk, action):
        relation = Friendship.objects.get(pk=pk)
        if action in {"accept", "decline"}:
            if relation.addressee != request.user or relation.status != Friendship.Status.PENDING:
                raise PermissionDenied()
            relation.status = Friendship.Status.ACCEPTED if action == "accept" else Friendship.Status.DECLINED
        elif action == "cancel":
            if relation.requester != request.user or relation.status != Friendship.Status.PENDING:
                raise PermissionDenied()
            relation.status = Friendship.Status.CANCELLED
        elif action == "remove":
            if request.user not in {relation.requester, relation.addressee} or relation.status != Friendship.Status.ACCEPTED:
                raise PermissionDenied()
            relation.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            raise ValidationError("Action inconnue.")
        relation.save(update_fields=("status", "updated_at"))
        return Response(FriendshipSerializer(relation).data)
