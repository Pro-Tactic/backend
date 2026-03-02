from datetime import date

from django.db import migrations, models


def copy_year_to_date(apps, schema_editor):
    Clube = apps.get_model("backend", "Clube")
    for clube in Clube.objects.all():
        ano = getattr(clube, "ano_fundacao", None)
        if ano:
            clube.data_criacao = date(int(ano), 1, 1)
        else:
            clube.data_criacao = date(1900, 1, 1)
        clube.save(update_fields=["data_criacao"])


class Migration(migrations.Migration):

    dependencies = [
        ("backend", "0017_jogador_data_nascimento_altura_cm"),
    ]

    operations = [
        migrations.AddField(
            model_name="clube",
            name="data_criacao",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.RunPython(copy_year_to_date, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="clube",
            name="ano_fundacao",
        ),
        migrations.AlterField(
            model_name="clube",
            name="data_criacao",
            field=models.DateField(),
        ),
    ]
