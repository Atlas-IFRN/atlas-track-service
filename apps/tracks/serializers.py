from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import (
    AuditLog,
    ChallengeSubmission,
    Content,
    Module,
    Skill,
    Track,
    TrackCategory,
    UserContentProgress,
    UserModuleProgress,
    UserTrack,
)
from .services import get_track_user_progress


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = [
            'id',
            'table_name',
            'action',
            'record_id',
            'user_id',
            'payload',
            'created_at',
        ]
        read_only_fields = fields


class TrackCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackCategory
        fields = ['id', 'name', 'slug', 'is_active', 'display_order']
        read_only_fields = fields


class SkillSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(
        source='get_category_display',
        read_only=True,
    )

    class Meta:
        model = Skill
        fields = [
            'id',
            'name',
            'slug',
            'category',
            'category_display',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class TrackSearchSerializer(serializers.ModelSerializer):
    """Payload enxuto para a busca global (dropdown do cabeçalho).

    Sem as anotações/contadores caros do TrackListSerializer — só o necessário
    para exibir uma linha de resultado e navegar até /trilhas/{id}.
    """

    level_display = serializers.CharField(source='get_level_display', read_only=True)
    skills = serializers.SlugRelatedField(slug_field='name', many=True, read_only=True)
    category = TrackCategorySerializer(read_only=True)

    class Meta:
        model = Track
        fields = ['id', 'title', 'category', 'level', 'level_display', 'skills']


class ContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Content
        fields = '__all__'

    def validate(self, attrs):
        content_type = attrs.get(
            'content_type',
            getattr(self.instance, 'content_type', None),
        )

        if content_type == 'ARTICLE':
            attrs['content_url'] = None
        return attrs


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
    category = TrackCategorySerializer(read_only=True)
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
            'category',
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
    contents = serializers.SerializerMethodField()

    class Meta:
        model = Module
        fields = '__all__'

    def get_contents(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        authenticated = bool(user and user.is_authenticated)
        user_id = user.id if authenticated else None
        contents = obj.contents.all()

        if str(obj.track.creator_id) != str(user_id):
            contents = contents.filter(visibility='enrolled')

        return ContentSerializer(contents, many=True, context=self.context).data


class TrackSerializer(serializers.ModelSerializer):
    modules = serializers.SerializerMethodField()
    category = TrackCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=TrackCategory.objects.filter(is_active=True),
        source='category',
        write_only=True,
    )
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
            'category',
            'category_id',
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
            'status',
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

    def get_modules(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        authenticated = bool(user and user.is_authenticated)
        user_id = user.id if authenticated else None
        role = getattr(user, 'role', None) if authenticated else None

        can_view_modules = role == 'TEACHER'
        if user_id and str(obj.creator_id) == str(user_id):
            can_view_modules = True
        if user_id and UserTrack.objects.filter(
            user_id=user_id,
            track=obj,
            status__in=['IN_PROGRESS', 'COMPLETED'],
        ).exists():
            can_view_modules = True

        if not can_view_modules:
            return []

        return ModuleSerializer(
            obj.modules.all(),
            many=True,
            context=self.context,
        ).data

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

            track = attrs.get('track')
            if not self.instance and track and track.status != 'PUBLISHED':
                raise serializers.ValidationError(
                    {"track": "Inscrição bloqueada. A trilha deve estar publicada."}
                )

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

    def create(self, validated_data):
        """Cria uma matrícula ou reativa uma inscrição abandonada.

        ``UserTrack`` é único por aluno e trilha. Reutilizar o registro com
        status ``DROPPED`` permite que o aluno volte à trilha sem apagar o
        progresso que ele já havia alcançado.
        """
        user_id = validated_data['user_id']
        track = validated_data['track']

        with transaction.atomic():
            dropped_enrollment = (
                UserTrack.objects.select_for_update()
                .filter(user_id=user_id, track=track, status='DROPPED')
                .first()
            )
            if dropped_enrollment:
                dropped_enrollment.status = 'IN_PROGRESS'
                dropped_enrollment.enrolled_at = timezone.now()
                dropped_enrollment.completed_at = None
                dropped_enrollment.save(
                    update_fields=['status', 'enrolled_at', 'completed_at']
                )
                return dropped_enrollment

            return super().create(validated_data)


class CompletedTrackSerializer(serializers.ModelSerializer):
    track_id = serializers.UUIDField(source='track.id', read_only=True)
    track_title = serializers.CharField(source='track.title', read_only=True)

    class Meta:
        model = UserTrack
        fields = ['track_id', 'track_title', 'completed_at']
        read_only_fields = fields


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

    def validate(self, attrs):
        request = self.context.get('request')
        user_track = attrs.get('user_track') or getattr(self.instance, 'user_track', None)
        challenge = attrs.get('challenge') or getattr(self.instance, 'challenge', None)

        if not request or not request.user.is_authenticated:
            return attrs

        if not user_track or str(user_track.user_id) != str(request.user.id):
            raise serializers.ValidationError({
                'user_track': 'A matrícula deve pertencer ao aluno autenticado.'
            })

        if user_track.status != 'IN_PROGRESS':
            raise serializers.ValidationError({
                'user_track': 'A matrícula não está em andamento.'
            })

        if not challenge or challenge.content_type != 'CHALLENGE':
            raise serializers.ValidationError({
                'challenge': 'O conteúdo informado não é um desafio.'
            })

        if challenge.module.track_id != user_track.track_id:
            raise serializers.ValidationError({
                'challenge': 'O desafio não pertence à trilha desta matrícula.'
            })

        previous_module = (
            Module.objects.filter(
                track=challenge.module.track,
                display_order__lt=challenge.module.display_order,
            )
            .order_by('-display_order', '-created_at')
            .first()
        )
        if previous_module and not UserModuleProgress.objects.filter(
            user_track=user_track,
            module=previous_module,
            status='COMPLETED',
        ).exists():
            raise serializers.ValidationError({
                'challenge': 'Conclua o módulo anterior antes de enviar este desafio.'
            })

        return attrs
