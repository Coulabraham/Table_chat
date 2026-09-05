from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("games", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="game",
            name="game_type",
            field=models.CharField(
                choices=[("chess", "Échecs"), ("awale", "Awalé")],
                default="chess",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="gameinvitation",
            name="game_type",
            field=models.CharField(
                choices=[("chess", "Échecs"), ("awale", "Awalé")],
                default="chess",
                max_length=30,
            ),
        ),
    ]
