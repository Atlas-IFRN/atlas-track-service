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

    def validate(self, attrs):
        request = self.context.get('request')

        # Apenas executa se tiver um request com Auth (evita quebrar no painel Admin ou testes soltos)
        if request and request.auth:
            user_id = request.auth.get('user_id')
            user_role = request.auth.get('role')

            # PERMISSÃO: Professor não pode se matricular
            if user_role == 'TEACHER':
                raise serializers.ValidationError({"detail": "Professores não podem se matricular em trilhas."})

            # REGRA 4: Limite de Matrículas
            # Só fazemos essa checagem se for uma criação nova de matrícula
            if not self.instance:
                active_enrollments = UserTrack.objects.filter(user_id=user_id, status='IN_PROGRESS').count()

                if active_enrollments >= 3:
                    raise serializers.ValidationError(
                        {
                            "detail": "Você atingiu o limite de 3 trilhas em andamento. Conclua ou abandone uma para iniciar outra."
                        }
                    )

        return attrs


class ChallengeSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChallengeSubmission
        fields = '__all__'
        read_only_fields = ['ai_status', 'ai_feedback', 'ai_score', 'submitted_at', 'evaluated_at']
