from rest_framework import serializers

from .models import ChallengeSubmission, Content, Module, Track, UserContentProgress, UserModuleProgress, UserTrack


class ContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Content
        fields = '__all__'


class ModuleSerializer(serializers.ModelSerializer):
    contents = ContentSerializer(many=True, read_only=True)

    class Meta:
        model = Module
        fields = '__all__'


class TrackSerializer(serializers.ModelSerializer):
    modules = ModuleSerializer(many=True, read_only=True)

    class Meta:
        model = Track
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class UserContentProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserContentProgress
        fields = '__all__'
        read_only_fields = ['completed_at']


class UserModuleProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserModuleProgress
        fields = '__all__'
        read_only_fields = ['completed_at', 'progress_pct']


class UserTrackSerializer(serializers.ModelSerializer):
    module_progress = UserModuleProgressSerializer(many=True, read_only=True)
    content_progress = UserContentProgressSerializer(many=True, read_only=True)

    class Meta:
        model = UserTrack
        fields = [
            'id',
            'user_id',
            'track',
            'status',
            'enrolled_at',
            'completed_at',
            'module_progress',
            'content_progress',
        ]
        read_only_fields = ['enrolled_at', 'completed_at']


class ChallengeSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChallengeSubmission
        fields = '__all__'
        read_only_fields = ['ai_status', 'ai_feedback', 'ai_score', 'submitted_at', 'evaluated_at']
