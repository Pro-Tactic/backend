from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("backend", "0016_alter_clube_id_alter_competicao_id_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="jogador",
            name="idade",
        ),
        migrations.AddField(
            model_name="jogador",
            name="data_nascimento",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="jogador",
            name="altura",
            field=models.FloatField(help_text="Altura em cm"),
        ),
    ]
