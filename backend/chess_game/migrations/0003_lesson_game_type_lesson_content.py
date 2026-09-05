from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("chess_game", "0002_lesson_coach_messages_lesson_hints_and_more")]

    operations = [
        migrations.AddField(
            model_name="lesson",
            name="game_type",
            field=models.CharField(choices=[("chess", "Échecs"), ("awale", "Awalé")], default="chess", max_length=30),
        ),
        migrations.AddField(
            model_name="lesson",
            name="content",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
