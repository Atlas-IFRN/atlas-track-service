from rest_framework import viewsets

from .models import ChallengeSubmission, Content, Module, Track, UserContentProgress, UserModuleProgress, UserTrack
from .permissions import IsTeacherOrReadOnly
from .serializers import (
    ChallengeSubmissionSerializer,
    ContentSerializer,
    ModuleSerializer,
    TrackSerializer,
    UserContentProgressSerializer,
    UserModuleProgressSerializer,
    UserTrackSerializer,
)


class BaseProtectedViewSet(viewsets.ModelViewSet):
    """
    Classe base que garante que todos os ViewSets herdem a proteção do SimpleJWT.
    Rejeita qualquer requisição sem o header 'Authorization: Bearer <token>'
    """

    # permission_classes = [IsAuthenticated]


class TrackViewSet(BaseProtectedViewSet):
    queryset = Track.objects.all()
    serializer_class = TrackSerializer
    permission_classes = [IsTeacherOrReadOnly]


class ModuleViewSet(BaseProtectedViewSet):
    queryset = Module.objects.all()
    serializer_class = ModuleSerializer
    permission_classes = [IsTeacherOrReadOnly]


class ContentViewSet(BaseProtectedViewSet):
    queryset = Content.objects.all()
    serializer_class = ContentSerializer
    permission_classes = [IsTeacherOrReadOnly]


class UserTrackViewSet(BaseProtectedViewSet):
    queryset = UserTrack.objects.all()
    serializer_class = UserTrackSerializer


class UserModuleProgressViewSet(BaseProtectedViewSet):
    queryset = UserModuleProgress.objects.all()
    serializer_class = UserModuleProgressSerializer


class UserContentProgressViewSet(BaseProtectedViewSet):
    queryset = UserContentProgress.objects.all()
    serializer_class = UserContentProgressSerializer


class ChallengeSubmissionViewSet(BaseProtectedViewSet):
    queryset = ChallengeSubmission.objects.all()
    serializer_class = ChallengeSubmissionSerializer
