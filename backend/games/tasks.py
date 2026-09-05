from celery import shared_task
from django.utils import timezone
from .models import GameInvitation


@shared_task
def expire_invitations():
    return GameInvitation.objects.filter(status=GameInvitation.Status.PENDING, expires_at__lte=timezone.now()).update(status=GameInvitation.Status.EXPIRED)

