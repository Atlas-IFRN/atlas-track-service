from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('tracks', '0009_remove_repository_content_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='content',
            name='technical_requirements',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Requisitos técnicos do CHALLENGE em uma lista de textos',
            ),
        ),
    ]
