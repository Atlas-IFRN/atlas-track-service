from django.contrib import admin
from .models import (
    Track, Module, Content, UserTrack, 
    UserModuleProgress, UserContentProgress, ChallengeSubmission
)

@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('title', 'description')

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'track', 'display_order')
    list_filter = ('track',)

@admin.register(Content)
class ContentAdmin(admin.ModelAdmin):
    list_display = ('title', 'module', 'content_type', 'display_order')
    list_filter = ('content_type', 'module__track')

@admin.register(UserTrack)
class UserTrackAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_id', 'track', 'status', 'enrolled_at')
    list_filter = ('status', 'track')

@admin.register(ChallengeSubmission)
class ChallengeSubmissionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_track', 'ai_status', 'submitted_at')
    list_filter = ('ai_status',)

admin.site.register(UserModuleProgress)
admin.site.register(UserContentProgress)