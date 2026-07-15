from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('tracks', '0010_trackcategory_skill_category_track_category'),
    ]

    operations = [
        migrations.AlterField(
            model_name='auditlog',
            name='table_name',
            field=models.CharField(
                choices=[
                    ('track_category', 'Track Category'),
                    ('skill', 'Skill'),
                    ('track', 'Track'),
                    ('module', 'Module'),
                    ('content', 'Content'),
                    ('user_track', 'User Track'),
                    ('user_module_progress', 'User Module Progress'),
                    ('user_content_progress', 'User Content Progress'),
                    ('challenge_submission', 'Challenge Submission'),
                ],
                max_length=100,
            ),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(
                fields=['user_id', '-created_at'],
                name='track_audit_user_time_idx',
            ),
        ),
    ]
