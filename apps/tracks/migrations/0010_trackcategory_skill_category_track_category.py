import re
import unicodedata
import uuid

import django.db.models.deletion
from django.db import migrations, models


TRACK_CATEGORIES = (
    ('Backend', 'backend', 10),
    ('Frontend', 'frontend', 20),
    ('Inteligência Artificial', 'ai', 30),
    ('CI/CD', 'cicd', 40),
    ('DevOps', 'devops', 50),
)

SKILL_CATEGORIES = {
    'LANGUAGE': {
        'bash', 'c', 'c-plus-plus', 'dart', 'elixir', 'go', 'java',
        'javascript', 'kotlin', 'lua', 'php', 'python', 'r', 'ruby',
        'rust', 'scala', 'swift', 'typescript',
    },
    'FRAMEWORK': {
        'angular', 'bootstrap', 'django', 'dotnet', 'express', 'fastapi',
        'flask', 'flutter', 'laravel', 'nestjs', 'nextjs', 'nodejs',
        'react', 'react-native', 'ruby-on-rails', 'spring', 'svelte',
        'tailwindcss', 'vue',
    },
    'DATABASE': {
        'elasticsearch', 'firebase', 'mongodb', 'mysql', 'postgres',
        'postgresql', 'redis', 'sqlite', 'supabase',
    },
    'DATA_AI': {
        'jupyter', 'numpy', 'pandas', 'pytorch', 'scikit-learn',
        'tensorflow',
    },
    'INFRA': {
        'ansible', 'apache', 'apache-kafka', 'cloudflare', 'docker',
        'github-actions', 'google-cloud', 'jenkins', 'kubernetes', 'linux',
        'netlify', 'nginx', 'raspberry-pi', 'terraform', 'vercel',
    },
}


def normalize(value):
    normalized = unicodedata.normalize('NFD', value or '')
    return ''.join(
        character for character in normalized
        if unicodedata.category(character) != 'Mn'
    ).lower()


def classify_skill(slug):
    normalized_slug = normalize(slug).strip()
    for category, slugs in SKILL_CATEGORIES.items():
        if normalized_slug in slugs:
            return category
    return 'TOOL'


def classify_track(track):
    skills = track.skills.all()
    searchable_text = normalize(' '.join([
        track.title,
        track.description,
        *[f'{skill.name} {skill.slug}' for skill in skills],
    ]))

    if re.search(r'\b(ia|ai|ml|llm|nlp)\b|machine learning|pytorch|tensorflow|scikit', searchable_text):
        return 'ai'
    if re.search(r'frontend|front-end|react|javascript|typescript|html|css|vite', searchable_text):
        return 'frontend'
    if re.search(r'ci/cd|cicd|pipeline|jenkins|github actions|sonarqube|deploy', searchable_text):
        return 'cicd'
    if re.search(r'devops|cloud|kubernetes|terraform|aws|linux|observabilidade', searchable_text):
        return 'devops'
    return 'backend'


def seed_categories_and_classify_existing_data(apps, schema_editor):
    TrackCategory = apps.get_model('tracks', 'TrackCategory')
    Skill = apps.get_model('tracks', 'Skill')
    Track = apps.get_model('tracks', 'Track')

    categories = {}
    for name, slug, display_order in TRACK_CATEGORIES:
        category, _ = TrackCategory.objects.update_or_create(
            slug=slug,
            defaults={
                'name': name,
                'display_order': display_order,
                'is_active': True,
            },
        )
        categories[slug] = category

    for skill in Skill.objects.all():
        skill.category = classify_skill(skill.slug)
        skill.save(update_fields=['category'])

    for track in Track.objects.prefetch_related('skills').all():
        track.category = categories[classify_track(track)]
        track.save(update_fields=['category'])


class Migration(migrations.Migration):

    dependencies = [
        ('tracks', '0009_remove_repository_content_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='TrackCategory',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=60, unique=True)),
                ('slug', models.SlugField(max_length=60, unique=True)),
                ('is_active', models.BooleanField(default=True)),
                ('display_order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name_plural': 'track categories',
                'ordering': ['display_order', 'name'],
            },
        ),
        migrations.AddField(
            model_name='skill',
            name='category',
            field=models.CharField(
                choices=[
                    ('LANGUAGE', 'Linguagem'),
                    ('FRAMEWORK', 'Framework'),
                    ('DATABASE', 'Banco de dados'),
                    ('DATA_AI', 'Dados e IA'),
                    ('INFRA', 'Infraestrutura'),
                    ('TOOL', 'Ferramenta'),
                ],
                default='TOOL',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='track',
            name='category',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='tracks',
                to='tracks.trackcategory',
            ),
        ),
        migrations.RunPython(
            seed_categories_and_classify_existing_data,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name='track',
            name='category',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='tracks',
                to='tracks.trackcategory',
            ),
        ),
    ]
