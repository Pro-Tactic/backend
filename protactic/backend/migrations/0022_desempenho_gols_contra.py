from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0021_clube_competicoes'),
    ]

    operations = [
        migrations.AddField(
            model_name='desempenho',
            name='gols_contra',
            field=models.IntegerField(db_column='gol_contra_desempenho', default=0),
        ),
    ]
