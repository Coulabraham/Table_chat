from django.conf import settings
from django.db import models

from .engine import initial_state


class AwaleGameState(models.Model):
    game = models.OneToOneField("games.Game", on_delete=models.CASCADE, related_name="awale_state")
    ruleset = models.CharField(max_length=40, default="abapa_tablechat_v1", editable=False)
    pits = models.JSONField(default=list)
    scores = models.JSONField(default=list)
    current_player = models.PositiveSmallIntegerField(default=0)
    revision = models.PositiveIntegerField(default=0)
    last_move = models.JSONField(default=dict, blank=True)
    position_counts = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def create_for_game(cls, game):
        state = initial_state()
        return cls.objects.create(game=game, **state)


class AwaleMove(models.Model):
    state = models.ForeignKey(AwaleGameState, on_delete=models.CASCADE, related_name="moves")
    move_number = models.PositiveIntegerField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    player = models.PositiveSmallIntegerField()
    pit = models.PositiveSmallIntegerField()
    sowing_path = models.JSONField(default=list)
    captures = models.JSONField(default=list)
    capture_cancelled = models.BooleanField(default=False)
    state_after = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("move_number",)
        constraints = [models.UniqueConstraint(fields=("state", "move_number"), name="awale_move_number_unique")]


class ProcessedAwaleMove(models.Model):
    state = models.ForeignKey(AwaleGameState, on_delete=models.CASCADE, related_name="processed_moves")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    request_id = models.UUIDField()
    response = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("state", "user", "request_id"), name="awale_request_dedup")]

