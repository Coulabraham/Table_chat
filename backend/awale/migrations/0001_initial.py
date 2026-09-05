import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("games", "0002_gameinvitation_game_type"),
    ]

    operations = [
        migrations.CreateModel(
            name="AwaleGameState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ruleset", models.CharField(default="abapa_tablechat_v1", editable=False, max_length=40)),
                ("pits", models.JSONField(default=list)),
                ("scores", models.JSONField(default=list)),
                ("current_player", models.PositiveSmallIntegerField(default=0)),
                ("revision", models.PositiveIntegerField(default=0)),
                ("last_move", models.JSONField(blank=True, default=dict)),
                ("position_counts", models.JSONField(default=dict)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("game", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="awale_state", to="games.game")),
            ],
        ),
        migrations.CreateModel(
            name="AwaleMove",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("move_number", models.PositiveIntegerField()),
                ("player", models.PositiveSmallIntegerField()),
                ("pit", models.PositiveSmallIntegerField()),
                ("sowing_path", models.JSONField(default=list)),
                ("captures", models.JSONField(default=list)),
                ("capture_cancelled", models.BooleanField(default=False)),
                ("state_after", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("author", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("state", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="moves", to="awale.awalegamestate")),
            ],
            options={
                "ordering": ("move_number",),
                "constraints": [models.UniqueConstraint(fields=("state", "move_number"), name="awale_move_number_unique")],
            },
        ),
        migrations.CreateModel(
            name="ProcessedAwaleMove",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("request_id", models.UUIDField()),
                ("response", models.JSONField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("state", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="processed_moves", to="awale.awalegamestate")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "constraints": [models.UniqueConstraint(fields=("state", "user", "request_id"), name="awale_request_dedup")],
            },
        ),
    ]

