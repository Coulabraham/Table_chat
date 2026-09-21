import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="Conversation",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("user_high", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="conversations_as_high", to=settings.AUTH_USER_MODEL)),
                ("user_low", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="conversations_as_low", to=settings.AUTH_USER_MODEL)),
            ],
            options={"constraints": [models.UniqueConstraint(fields=("user_low", "user_high"), name="unique_private_pair"), models.CheckConstraint(condition=Q(("user_low_id__lt", F("user_high_id"))), name="private_pair_ordered_distinct")]},
        ),
        migrations.CreateModel(
            name="Message",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("client_id", models.UUIDField()),
                ("content", models.CharField(max_length=4000)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("author", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="messages", to=settings.AUTH_USER_MODEL)),
                ("conversation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="chat.conversation")),
            ],
            options={"ordering": ("id",), "constraints": [models.UniqueConstraint(fields=("author", "client_id"), name="unique_author_client_message")], "indexes": [models.Index(fields=["conversation", "id"], name="chat_conv_sequence_idx")]},
        ),
        migrations.CreateModel(
            name="DeliveryOutbox",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("delivered_at", models.DateTimeField(blank=True, null=True)),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("last_error", models.CharField(blank=True, max_length=200)),
                ("next_attempt_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("message", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="outbox", to="chat.message")),
            ],
        ),
    ]
