from rest_framework import serializers
from .models import (
    Track, Module, Content, UserTrack, 
    UserModuleProgress, UserContentProgress, ChallengeSubmission
)

class ContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Content
        fields = '__all__'

class ModuleSerializer(serializers.ModelSerializer):
    # Aninha os conteúdos apenas para leitura, facilitando a vida do Front-end
    contents = ContentSerializer(many=True, read_only=True)

    class Meta:
        model = Module
        fields = '__all__'

class TrackSerializer(serializers.ModelSerializer):
    # Aninha os módulos apenas para leitura
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
            'id', 'user_id', 'track', 'status', 
            'enrolled_at', 'completed_at', 
            'module_progress', 'content_progress'
        ]
        read_only_fields = ['enrolled_at', 'completed_at']

    def validate(self, data):
        is_creation = self.instance is None
        
        track = data.get('track', getattr(self.instance, 'track', None))
        user_id = data.get('user_id', getattr(self.instance, 'user_id', None))

        if is_creation:
            # Regra de Negócio 1: Elegibilidade (Trilha precisa estar publicada)
            if track and track.status != 'PUBLISHED':
                raise serializers.ValidationError(
                    {"track": "Inscrição bloqueada. A trilha deve estar no status PUBLISHED."}
                )

            # Regra de Negócio 2: Inscrição Única (Evita duplicação ativa)
            existing_enrollment = UserTrack.objects.filter(
                user_id=user_id, 
                track=track, 
                status__in=['IN_PROGRESS', 'COMPLETED']
            ).exists()

            if existing_enrollment:
                raise serializers.ValidationError(
                    {"user_id": "Este usuário já possui uma inscrição ativa ou concluída nesta trilha."}
                )

        return data

class ChallengeSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChallengeSubmission
        fields = '__all__'
        read_only_fields = ['ai_status', 'ai_feedback', 'ai_score', 'submitted_at', 'evaluated_at']