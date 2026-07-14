import uuid
from types import SimpleNamespace
from uuid import uuid4

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Module, Track, UserTrack
from .serializers import UserTrackSerializer
from .services.progress import get_track_user_progress


class UserTrackEnrollmentLimitTests(TestCase):
    def setUp(self):
        self.user_id = uuid.uuid4()
        self.creator_id = uuid.uuid4()
        self.request = SimpleNamespace(
            user=SimpleNamespace(
                id=self.user_id,
                role='STUDENT',
                is_authenticated=True,
            )
        )

    def create_published_track(self, title):
        track = Track.objects.create(
            creator_id=self.creator_id,
            title=title,
            description='Descrição da trilha',
        )
        Track.objects.filter(pk=track.pk).update(status='PUBLISHED')
        track.refresh_from_db()
        return track

    def test_blocks_fourth_in_progress_enrollment(self):
        tracks = [self.create_published_track(f'Trilha {index}') for index in range(4)]
        for track in tracks[:3]:
            UserTrack.objects.create(user_id=self.user_id, track=track)

        serializer = UserTrackSerializer(
            data={'track': str(tracks[3].id)},
            context={'request': self.request},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('detail', serializer.errors)

    def test_completed_enrollment_releases_one_slot(self):
        tracks = [self.create_published_track(f'Trilha {index}') for index in range(4)]
        enrollments = [
            UserTrack.objects.create(user_id=self.user_id, track=track)
            for track in tracks[:3]
        ]
        enrollments[0].status = 'COMPLETED'
        enrollments[0].save(update_fields=['status'])

        serializer = UserTrackSerializer(
            data={'track': str(tracks[3].id)},
            context={'request': self.request},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_completed_status_is_exposed_in_track_progress(self):
        track = self.create_published_track('Trilha concluída')
        UserTrack.objects.create(
            user_id=self.user_id,
            track=track,
            status='COMPLETED',
        )

        progress = get_track_user_progress(track, self.user_id, role='STUDENT')

        self.assertTrue(progress['enrolled'])
        self.assertEqual(progress['status'], 'COMPLETED')


class CompletedTracksApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.student_id = uuid4()
        cls.other_student_id = uuid4()
        cls.teacher_id = uuid4()

        cls.completed_track = cls.create_published_track(
            title='Fundamentos de Python',
        )
        cls.in_progress_track = cls.create_published_track(
            title='Desenvolvimento Web',
        )

        cls.completion_date = timezone.now()
        UserTrack.objects.create(
            user_id=cls.other_student_id,
            track=cls.completed_track,
            status='COMPLETED',
            completed_at=cls.completion_date,
        )
        UserTrack.objects.create(
            user_id=cls.other_student_id,
            track=cls.in_progress_track,
            status='IN_PROGRESS',
        )

    @classmethod
    def create_published_track(cls, title):
        track = Track.objects.create(
            creator_id=cls.teacher_id,
            title=title,
            description=f'Descrição de {title}',
        )
        Module.objects.create(
            track=track,
            title='Módulo inicial',
            description='Conteúdo introdutório',
        )
        track.status = 'PUBLISHED'
        track.save()
        return track

    def authenticate(self, user_id, role='STUDENT'):
        self.client.force_authenticate(
            user=SimpleNamespace(
                id=user_id,
                role=role,
                is_authenticated=True,
            )
        )

    def test_completed_action_exposes_only_public_completion_fields(self):
        self.authenticate(self.student_id)

        response = self.client.get(
            '/api/track/user-tracks/completed/',
            {'user_uuid': str(self.other_student_id)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]['track_id'],
            str(self.completed_track.id),
        )
        self.assertEqual(
            response.data[0]['track_title'],
            self.completed_track.title,
        )
        self.assertEqual(
            set(response.data[0]),
            {'track_id', 'track_title', 'completed_at'},
        )

    def test_student_cannot_list_another_students_enrollment_details(self):
        self.authenticate(self.student_id)

        response = self.client.get(
            '/api/track/user-tracks/',
            {'user_uuid': str(self.other_student_id)},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_completed_action_rejects_invalid_user_uuid(self):
        self.authenticate(self.student_id)

        response = self.client.get(
            '/api/track/user-tracks/completed/',
            {'user_uuid': 'invalid'},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
