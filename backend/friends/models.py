from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Friendship(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        ACCEPTED = "accepted", "Acceptée"
        DECLINED = "declined", "Refusée"
        CANCELLED = "cancelled", "Annulée"

    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="friend_requests_sent")
    addressee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="friend_requests_received")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=~Q(requester=models.F("addressee")), name="friendship_no_self"),
            models.UniqueConstraint(fields=("requester", "addressee"), name="friendship_directed_unique"),
        ]
        indexes = [models.Index(fields=("addressee", "status")), models.Index(fields=("requester", "status"))]

    def clean(self):
        if self.requester_id == self.addressee_id:
            raise ValidationError("Vous ne pouvez pas vous ajouter vous-même.")
        reverse = Friendship.objects.filter(requester=self.addressee, addressee=self.requester).exclude(pk=self.pk)
        if reverse.filter(status__in=[self.Status.PENDING, self.Status.ACCEPTED]).exists():
            raise ValidationError("Une relation existe déjà entre ces utilisateurs.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

