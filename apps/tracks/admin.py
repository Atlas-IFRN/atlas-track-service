from django.contrib import admin

from .models import ChallengeSubmission, Module, Track, TrackChallenge, UserModuleProgress, UserTrack

# Registrando os models de forma simples
admin.site.register(Track)
admin.site.register(Module)
admin.site.register(TrackChallenge)
admin.site.register(UserTrack)
admin.site.register(UserModuleProgress)
admin.site.register(ChallengeSubmission)
