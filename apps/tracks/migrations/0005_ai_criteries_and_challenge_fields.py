from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracks', '0004_auditlog'),
    ]

    operations = [
        migrations.AddField(
            model_name='content',
            name='language',
            field=models.CharField(
                blank=True,
                help_text='Stack/linguagem esperada quando for CHALLENGE (ex.: python, javascript)',
                max_length=50,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='content',
            name='evaluation_criteria',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Critérios de avaliação para CHALLENGE no formato {label: peso}',
            ),
        ),
        migrations.AddField(
            model_name='challengesubmission',
            name='ai_criteries',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Resultado dos critérios avaliados pela IA (lista de checks com id/label/present/evidence/weight)',
            ),
        ),
    ]
