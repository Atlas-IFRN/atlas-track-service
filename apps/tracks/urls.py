from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TrackViewSet, ModuleViewSet, ContentViewSet, 
    UserTrackViewSet, UserModuleProgressViewSet, 
    UserContentProgressViewSet, ChallengeSubmissionViewSet
)

router = DefaultRouter()
router.register(r'tracks', TrackViewSet, basename='track')
router.register(r'modules', ModuleViewSet, basename='module')
router.register(r'contents', ContentViewSet, basename='content')
router.register(r'user-tracks', UserTrackViewSet, basename='user-track')
router.register(r'module-progress', UserModuleProgressViewSet, basename='module-progress')
router.register(r'content-progress', UserContentProgressViewSet, basename='content-progress')
router.register(r'submissions', ChallengeSubmissionViewSet, basename='submission')

urlpatterns = [
    path('', include(router.urls)),
]