import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracks', '0005_ai_criteries_and_challenge_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='Skill',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=80, unique=True)),
                ('slug', models.SlugField(max_length=90, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='track',
            name='duration_weeks',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='track',
            name='level',
            field=models.CharField(
                choices=[
                    ('BEGINNER', 'Iniciante'),
                    ('INTERMEDIATE', 'Intermediario'),
                    ('ADVANCED', 'Avancado'),
                ],
                default='BEGINNER',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='track',
            name='outcomes',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='track',
            name='prerequisites',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='track',
            name='skills',
            field=models.ManyToManyField(blank=True, related_name='tracks', to='tracks.skill'),
        ),
    ]
