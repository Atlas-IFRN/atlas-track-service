import uuid
from types import SimpleNamespace

from django.test import TestCase
from rest_framework.test import APIClient

from .audit import clear_current_actor_id, set_current_actor_id
from .models import AuditLog, Track, TrackCategory


class TrackAuditSignalsTests(TestCase):
    def setUp(self):
        self.user_id = uuid.uuid4()
        set_current_actor_id(self.user_id)
        self.category = TrackCategory.objects.get(slug='backend')
        AuditLog.objects.all().delete()

    def tearDown(self):
        clear_current_actor_id()

    def test_create_update_and_delete_are_audited_with_actor(self):
        track = Track.objects.create(
            creator_id=self.user_id,
            title='Trilha auditada',
            description='Descrição',
            category=self.category,
        )
        track.title = 'Trilha atualizada'
        track.save()
        track_id = track.id
        track.delete()

        logs = AuditLog.objects.filter(table_name='track', record_id=track_id)
        self.assertEqual(
            set(logs.values_list('action', flat=True)),
            {'CREATE', 'UPDATE', 'DELETE'},
        )
        self.assertFalse(logs.exclude(user_id=self.user_id).exists())
        update_log = logs.get(action='UPDATE')
        self.assertEqual(update_log.payload['before']['title'], 'Trilha auditada')
        self.assertEqual(update_log.payload['after']['title'], 'Trilha atualizada')


class AuditLogAccessTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_only_teacher_can_list_audit_logs(self):
        student = SimpleNamespace(id=uuid.uuid4(), is_authenticated=True, role='STUDENT')
        teacher = SimpleNamespace(id=uuid.uuid4(), is_authenticated=True, role='TEACHER')

        self.client.force_authenticate(student)
        self.assertEqual(self.client.get('/api/track/audit-logs/').status_code, 403)

        self.client.force_authenticate(teacher)
        self.assertEqual(self.client.get('/api/track/audit-logs/').status_code, 200)
