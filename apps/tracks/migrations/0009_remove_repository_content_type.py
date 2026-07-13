from django.db import migrations, models


def migrate_repositories_to_articles(apps, schema_editor):
    Content = apps.get_model('tracks', 'Content')
    for repository in Content.objects.filter(content_type='REPOSITORY').iterator():
        repository.content_type = 'ARTICLE'
        if not repository.content:
            repository.content = repository.description or ''
        repository.content_url = None
        repository.save(
            update_fields=['content_type', 'content', 'content_url'],
        )


class Migration(migrations.Migration):
    dependencies = [
        ('tracks', '0008_content_content'),
    ]

    operations = [
        migrations.RunPython(
            migrate_repositories_to_articles,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name='content',
            name='content_type',
            field=models.CharField(
                choices=[
                    ('VIDEO', 'Vídeo'),
                    ('ARTICLE', 'Artigo'),
                    ('CHALLENGE', 'Desafio'),
                ],
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='content',
            name='content_url',
            field=models.URLField(
                blank=True,
                help_text='URL do vídeo',
                null=True,
            ),
        ),
    ]
