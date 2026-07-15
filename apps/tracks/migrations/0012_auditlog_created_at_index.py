from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('tracks', '0011_alter_auditlog_table_name'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(
                fields=['-created_at'],
                name='track_audit_created_idx',
            ),
        ),
    ]
