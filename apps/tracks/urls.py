from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TrackViewSet, UserTrackViewSet

router = DefaultRouter()
router.register(r'tracks', TrackViewSet, basename='track')
router.register(r'user-tracks', UserTrackViewSet, basename='usertrack')

urlpatterns = [
    # Inclui todas as rotas geradas pelo roteador
    path('', include(router.urls)),
]
