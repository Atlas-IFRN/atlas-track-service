from django.db.models import Count
from rest_framework import viewsets

from .models import ChallengeSubmission, Content, Module, Track, UserContentProgress, UserModuleProgress, UserTrack
from .permissions import IsAuthenticatedViaRPC, IsTeacherOrReadOnly
from .serializers import (
    ChallengeSubmissionSerializer,
    ContentSerializer,
    ModuleListSerializer,
    ModuleSerializer,
    TrackListSerializer,
    TrackSerializer,
    UserContentProgressSerializer,
    UserModuleProgressSerializer,
    UserTrackSerializer,
)


class TrackViewSet(viewsets.ModelViewSet):
    permission_classes = [IsTeacherOrReadOnly, IsAuthenticatedViaRPC]

    def get_queryset(self):
        return Track.objects.annotate(modules_count=Count('modules')).all()

    def get_serializer_class(self):
        # GET /api/tracks/ -> Usa o raso (com o count)
        if self.action == 'list':
            return TrackListSerializer
        # GET /api/tracks/{id}/ -> Usa o detalhado (com os módulos aninhados)
        return TrackSerializer


class ModuleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsTeacherOrReadOnly, IsAuthenticatedViaRPC]

    def get_queryset(self):
        # Conta os conteúdos de cada módulo
        queryset = Module.objects.annotate(contents_count=Count('contents')).all()

        track_id = self.request.query_params.get('track_id')
        if track_id:
            queryset = queryset.filter(track_id=track_id)

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return ModuleListSerializer
        return ModuleSerializer


class ContentViewSet(viewsets.ModelViewSet):
    serializer_class = ContentSerializer
    permission_classes = [IsTeacherOrReadOnly, IsAuthenticatedViaRPC]

    def get_queryset(self):
        queryset = Content.objects.all()

        module_id = self.request.query_params.get('module_id')
        if module_id:
            queryset = queryset.filter(module_id=module_id)

        return queryset


class UserTrackViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedViaRPC]
    serializer_class = UserTrackSerializer

    def get_queryset(self):
        target_user_uuid = self.request.query_params.get('user_uuid')
        if target_user_uuid:
            return UserTrack.objects.filter(user_id=target_user_uuid)

        if self.request.auth:
            logged_user_id = self.request.auth.get('user_id')
            return UserTrack.objects.filter(user_id=logged_user_id)

        return UserTrack.objects.none()


class UserModuleProgressViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedViaRPC]
    queryset = UserModuleProgress.objects.all()
    serializer_class = UserModuleProgressSerializer


class UserContentProgressViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedViaRPC]
    queryset = UserContentProgress.objects.all()
    serializer_class = UserContentProgressSerializer


class ChallengeSubmissionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedViaRPC]
    queryset = ChallengeSubmission.objects.all()
    serializer_class = ChallengeSubmissionSerializer
