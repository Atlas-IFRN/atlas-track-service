from django.contrib import admin
from .models import (
    Skill, Track, Module, Content, UserTrack,
    UserModuleProgress, UserContentProgress, ChallengeSubmission, AuditLog
)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ('title', 'level', 'duration_weeks', 'status', 'created_at')
    list_filter = ('status', 'level', 'skills')
    filter_horizontal = ('skills',)
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


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'table_name', 'action', 'record_id', 'user_id', 'created_at')
    list_filter = ('table_name', 'action', 'created_at')
    search_fields = ('record_id', 'user_id')
    readonly_fields = ('id', 'table_name', 'action', 'record_id', 'user_id', 'payload', 'created_at')
    ordering = ('-created_at',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
