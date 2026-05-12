from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Track, UserTrack
from .serializers import TrackSerializer, UserTrackSerializer

# Create your views here.


class TrackViewSet(viewsets.ModelViewSet):
    """
    CRUD para gestão das Trilhas.
    Requer autenticação JWT válida (via SUAP).
    """

    queryset = Track.objects.all()
    serializer_class = TrackSerializer
    permission_classes = [IsAuthenticated]


class UserTrackViewSet(viewsets.ModelViewSet):
    """
    CRUD para gestão das Inscrições dos Usuários nas Trilhas.
    Requer autenticação JWT válida.
    """

    queryset = UserTrack.objects.all().order_by('-enrolled_at')
    serializer_class = UserTrackSerializer
    permission_classes = [IsAuthenticated]
