from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from .models import (
    ChallengeSubmission,
    Content,
    Module,
    Skill,
    Track,
    UserContentProgress,
    UserModuleProgress,
    UserTrack,
)
from .services import get_track_user_progress


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['id', 'name', 'slug', 'created_at']
        read_only_fields = ['id', 'created_at']


class ContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Content
        fields = '__all__'


class ModuleListSerializer(serializers.ModelSerializer):
    contents_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Module
        fields = ['id', 'title', 'description', 'display_order', 'contents_count', 'created_at']


def _get_modules_count(track):
    annotated_value = getattr(track, 'modules_count', None)
    if annotated_value is not None:
        return annotated_value
    return track.modules.count()


def _get_total_duration_minutes(track):
    annotated_value = getattr(track, 'total_duration_minutes', None)
    if annotated_value is not None:
        return annotated_value or 0

    total = 0
    for module in track.modules.all():
        for content in module.contents.all():
            total += content.duration_minutes or 0
    return total


def _get_challenges_count(track):
    annotated_value = getattr(track, 'challenges_count', None)
    if annotated_value is not None:
        return annotated_value

    return Content.objects.filter(module__track=track, content_type='CHALLENGE').count()


def _serialize_latest_evaluation(track, request):
    user = getattr(request, 'user', None)
    authenticated = bool(user and user.is_authenticated)
    user_id = user.id if authenticated else None
    role = getattr(user, 'role', None) if authenticated else None

    queryset = ChallengeSubmission.objects.filter(
        challenge__module__track=track,
        ai_status='EVALUATED',
    ).select_related('challenge', 'challenge__module')

    if role == 'TEACHER':
        queryset = queryset.filter(challenge__module__track__creator_id=user_id)
    elif user_id:
        queryset = queryset.filter(user_track__user_id=user_id)
    else:
        return None

    submission = queryset.order_by('-evaluated_at', '-submitted_at').first()
    if not submission:
        return None

    score = int(submission.ai_score or 0)
    criteria = submission.ai_criteries if isinstance(submission.ai_criteries, list) else []
    checks = []

    for criterion in criteria:
        if not isinstance(criterion, dict):
            continue

        label = criterion.get('label') or criterion.get('name') or criterion.get('id') or 'Criterio'
        present = criterion.get('present')
        if present is None:
            present = criterion.get('passed', criterion.get('ok', False))

        checks.append({
            'label': str(label),
            'status': 'success' if bool(present) else 'danger',
        })

    attended = sum(1 for check in checks if check['status'] == 'success')
    pending = sum(1 for check in checks if check['status'] == 'danger')

    return {
        'score': score,
        'status': 'Aprovado' if score >= 70 else 'Pendente',
        'challenge': submission.challenge.title,
        'module': submission.challenge.module.title,
        'attended': attended,
        'pending': pending,
        'criteria': len(checks),
        'checks': checks,
    }


class TrackListSerializer(serializers.ModelSerializer):
    skills = SkillSerializer(many=True, read_only=True)
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    modules_count = serializers.SerializerMethodField()
    total_duration_minutes = serializers.SerializerMethodField()
    challenges_count = serializers.SerializerMethodField()
    user_progress = serializers.SerializerMethodField()
    latest_evaluation = serializers.SerializerMethodField()
    is_new = serializers.SerializerMethodField()

    class Meta:
        model = Track
        fields = [
            'id',
            'title',
            'description',
            'level',
            'level_display',
            'duration_weeks',
            'skills',
            'outcomes',
            'prerequisites',
            'status',
            'modules_count',
            'total_duration_minutes',
            'challenges_count',
            'user_progress',
            'latest_evaluation',
            'is_new',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_modules_count(self, obj):
        return _get_modules_count(obj)

    def get_total_duration_minutes(self, obj):
        return _get_total_duration_minutes(obj)

    def get_challenges_count(self, obj):
        return _get_challenges_count(obj)

    def get_user_progress(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        authenticated = bool(user and user.is_authenticated)
        return get_track_user_progress(
            track=obj,
            user_id=user.id if authenticated else None,
            role=getattr(user, 'role', None) if authenticated else None,
        )

    def get_latest_evaluation(self, obj):
        return _serialize_latest_evaluation(obj, self.context.get('request'))

    def get_is_new(self, obj):
        if not obj.created_at:
            return False
        return obj.created_at >= timezone.now() - timedelta(days=14)


class ModuleSerializer(serializers.ModelSerializer):
    contents = ContentSerializer(many=True, read_only=True)

    class Meta:
        model = Module
        fields = '__all__'


class TrackSerializer(serializers.ModelSerializer):
    modules = ModuleSerializer(many=True, read_only=True)
    skills = SkillSerializer(many=True, read_only=True)
    skill_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Skill.objects.all(),
        source='skills',
        write_only=True,
        required=False,
    )
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    modules_count = serializers.SerializerMethodField()
    total_duration_minutes = serializers.SerializerMethodField()
    challenges_count = serializers.SerializerMethodField()
    user_progress = serializers.SerializerMethodField()
    latest_evaluation = serializers.SerializerMethodField()
    is_new = serializers.SerializerMethodField()

    class Meta:
        model = Track
        fields = [
            'id',
            'creator_id',
            'title',
            'description',
            'level',
            'level_display',
            'duration_weeks',
            'skills',
            'skill_ids',
            'outcomes',
            'prerequisites',
            'status',
            'modules',
            'modules_count',
            'total_duration_minutes',
            'challenges_count',
            'user_progress',
            'latest_evaluation',
            'is_new',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'creator_id',
            'created_at',
            'updated_at',
            'modules_count',
            'total_duration_minutes',
            'challenges_count',
            'user_progress',
            'latest_evaluation',
            'is_new',
        ]

    def get_modules_count(self, obj):
        return _get_modules_count(obj)

    def get_total_duration_minutes(self, obj):
        return _get_total_duration_minutes(obj)

    def get_challenges_count(self, obj):
        return _get_challenges_count(obj)

    def get_user_progress(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        authenticated = bool(user and user.is_authenticated)
        return get_track_user_progress(
            track=obj,
            user_id=user.id if authenticated else None,
            role=getattr(user, 'role', None) if authenticated else None,
        )

    def get_latest_evaluation(self, obj):
        return _serialize_latest_evaluation(obj, self.context.get('request'))

    def get_is_new(self, obj):
        if not obj.created_at:
            return False
        return obj.created_at >= timezone.now() - timedelta(days=14)


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
        read_only_fields = ['user_id', 'enrolled_at', 'completed_at']

    def validate(self, attrs):
        request = self.context.get('request')

        # Apenas executa se tiver um request autenticado (evita quebrar no painel Admin ou testes soltos)
        if request and getattr(request, 'user', None) and request.user.is_authenticated:
            user_id = request.user.id
            user_role = request.user.role

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
        read_only_fields = [
            'ai_status',
            'ai_feedback',
            'ai_score',
            'ai_criteries',
            'submitted_at',
            'evaluated_at',
        ]
