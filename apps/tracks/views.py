from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import (
    Track, Module, Content, UserTrack, 
    UserModuleProgress, UserContentProgress, ChallengeSubmission
)
from .serializers import (
    TrackSerializer, ModuleSerializer, ContentSerializer, 
    UserTrackSerializer, UserModuleProgressSerializer, 
    UserContentProgressSerializer, ChallengeSubmissionSerializer
)

class BaseProtectedViewSet(viewsets.ModelViewSet):
    """
    Classe base que garante que todos os ViewSets herdem a proteção do SimpleJWT.
    Rejeita qualquer requisição sem o header 'Authorization: Bearer <token>'
    """
    permission_classes = [IsAuthenticated]

class TrackViewSet(BaseProtectedViewSet):
    queryset = Track.objects.all()
    serializer_class = TrackSerializer

class ModuleViewSet(BaseProtectedViewSet):
    queryset = Module.objects.all()
    serializer_class = ModuleSerializer

class ContentViewSet(BaseProtectedViewSet):
    queryset = Content.objects.all()
    serializer_class = ContentSerializer

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