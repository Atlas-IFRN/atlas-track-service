from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('tracks', '0006_track_metadata_and_skills'),
    ]

    operations = [
        migrations.AddField(
            model_name='content',
            name='visibility',
            field=models.CharField(
                choices=[
                    ('enrolled', 'Visível para matriculados'),
                    ('draft', 'Rascunho'),
                ],
                default='enrolled',
                max_length=20,
            ),
        ),
    ]
