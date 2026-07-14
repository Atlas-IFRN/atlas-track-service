from django.db import migrations, models


def migrate_articles_to_markdown(apps, schema_editor):
    Content = apps.get_model('tracks', 'Content')
    for article in Content.objects.filter(content_type='ARTICLE').iterator():
        article.content = article.description or ''
        article.content_url = None
        article.save(update_fields=['content', 'content_url'])


class Migration(migrations.Migration):
    dependencies = [
        ('tracks', '0007_content_visibility'),
    ]

    operations = [
        migrations.AddField(
            model_name='content',
            name='content',
            field=models.TextField(
                blank=True,
                default='',
                help_text='Corpo em Markdown quando o tipo for ARTICLE',
            ),
        ),
        migrations.RunPython(
            migrate_articles_to_markdown,
            migrations.RunPython.noop,
        ),
    ]
