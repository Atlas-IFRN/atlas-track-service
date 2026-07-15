from uuid import UUID

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import filters, pagination, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
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
from .permissions import IsTeacherOrReadOnly
from .serializers import (
    ChallengeSubmissionSerializer,
    CompletedTrackSerializer,
    ContentSerializer,
    ModuleListSerializer,
    ModuleSerializer,
    SkillSerializer,
    TrackCategorySerializer,
    TrackListSerializer,
    TrackSearchSerializer,
    TrackSerializer,
    UserContentProgressSerializer,
    UserModuleProgressSerializer,
    UserTrackSerializer,
)
from .tasks import evaluate_challenge_submission
from .services import complete_content, uncomplete_content


NOT_FOUND_DETAIL = 'Não encontrado.'


class TrackPageNumberPagination(pagination.PageNumberPagination):
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 50


class TrackExceptionHandlerMixin:
    def handle_exception(self, exc):
        response = super().handle_exception(exc)

        if isinstance(exc, NotFound) and response is not None:
            code = getattr(exc.detail, 'code', 'not_found')
            response.data = {
                'detail': NOT_FOUND_DETAIL if code == 'not_found' else str(exc.detail),
                'code': code,
            }

        return response


def _ensure_track_owner(track: Track, request) -> None:
    """Bloqueia ação se o usuário logado não for o criador da trilha."""
    user_id = request.user.id
    if str(track.creator_id) != str(user_id):
        raise PermissionDenied("Apenas o criador da trilha pode executar esta ação.")


def _parse_user_uuid(value):
    try:
        return UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        raise ValidationError({
            'user_uuid': 'Informe um UUID de usuário válido.'
        }) from None


class TrackCategoryViewSet(
    TrackExceptionHandlerMixin,
    viewsets.ReadOnlyModelViewSet,
):
    permission_classes = [IsAuthenticated]
    serializer_class = TrackCategorySerializer
    queryset = TrackCategory.objects.filter(is_active=True)
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'slug']
    ordering_fields = ['display_order', 'name']
    ordering = ['display_order', 'name']


class SkillViewSet(TrackExceptionHandlerMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsTeacherOrReadOnly]
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'slug', 'category']
    ordering_fields = ['name', 'category', 'created_at']
    ordering = ['name']


class TrackViewSet(TrackExceptionHandlerMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsTeacherOrReadOnly]
    pagination_class = TrackPageNumberPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        'title',
        'description',
        'category__name',
        'category__slug',
        'skills__name',
        'skills__slug',
    ]
    ordering_fields = ['title', 'category__name', 'created_at', 'duration_weeks', 'level']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = (
            Track.objects.select_related('category')
            .prefetch_related('skills', 'modules__contents')
            .annotate(
                modules_count=Count('modules', distinct=True),
                total_duration_minutes=Sum('modules__contents__duration_minutes'),
                challenges_count=Count(
                    'modules__contents',
                    filter=Q(modules__contents__content_type='CHALLENGE'),
                    distinct=True,
                ),
            )
            .all()
        )

        role = self.request.user.role
        if role != 'TEACHER':
            queryset = queryset.filter(status='PUBLISHED')

        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)

        level = self.request.query_params.get('level')
        if level:
            queryset = queryset.filter(level=level)

        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)

        skills = self.request.query_params.get('skills') or self.request.query_params.get('skill')
        if skills:
            skill_values = [value.strip() for value in skills.split(',') if value.strip()]
            queryset = queryset.filter(
                Q(skills__slug__in=skill_values)
                | Q(skills__name__in=skill_values)
            ).distinct()

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return TrackListSerializer
        return TrackSerializer

    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        """Busca compacta de trilhas para a busca global do cabeçalho.

        Reaproveita o SearchFilter (search_fields) e a paginação da viewset, mas
        com um queryset leve (sem os contadores caros de get_queryset) e um
        serializer enxuto. Respeita a visibilidade: não-docente só vê PUBLISHED.
        """
        queryset = (
            Track.objects.select_related('category')
            .prefetch_related('skills')
            .order_by('-created_at')
        )
        if request.user.role != 'TEACHER':
            queryset = queryset.filter(status='PUBLISHED')
        queryset = self.filter_queryset(queryset)
        page = self.paginate_queryset(queryset)
        serializer = TrackSearchSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def perform_create(self, serializer):
        logged_user_id = self.request.user.id
        serializer.save(creator_id=logged_user_id)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Muda status para PUBLISHED. Valida ao menos 1 módulo com 1 conteúdo."""
        track = self.get_object()
        _ensure_track_owner(track, request)

        if not track.modules.exists():
            raise ValidationError({"status": "Trilha precisa de pelo menos um módulo para publicar."})
        if not Content.objects.filter(module__track=track).exists():
            raise ValidationError({"status": "Trilha precisa de pelo menos um conteúdo em algum módulo."})

        track.status = 'PUBLISHED'
        track.save()
        return Response(self.get_serializer(track).data)

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Muda status para ARCHIVED."""
        track = self.get_object()
        _ensure_track_owner(track, request)

        track.status = 'ARCHIVED'
        track.save()
        return Response(self.get_serializer(track).data)

    @action(detail=False, methods=['get'], url_path='me/teaching')
    def me_teaching(self, request):
        """Trilhas criadas pelo professor atual + contagem de inscritos."""
        if request.user.role != 'TEACHER':
            raise PermissionDenied("Apenas professores podem acessar este painel.")

        user_id = request.user.id
        queryset = (
            Track.objects.filter(creator_id=user_id)
            .annotate(modules_count=Count('modules', distinct=True), enrollments_count=Count('enrollments', distinct=True))
            .order_by('-created_at')
        )
        data = []
        for t in queryset:
            data.append({
                'id': str(t.id),
                'title': t.title,
                'status': t.status,
                'modules_count': t.modules_count,
                'enrollments_count': t.enrollments_count,
                'created_at': t.created_at,
                'updated_at': t.updated_at,
            })
        return Response(data)

    @action(detail=True, methods=['get'])
    def students(self, request, pk=None):
        """Alunos inscritos numa trilha com progresso. Apenas o dono."""
        track = self.get_object()
        _ensure_track_owner(track, request)

        total_modules = track.modules.count()
        results = []
        for ut in track.enrollments.all().prefetch_related('module_progress'):
            completed = ut.module_progress.filter(status='COMPLETED').count()
            progress_pct = (completed / total_modules * 100) if total_modules else 0
            results.append({
                'user_track_id': str(ut.id),
                'user_id': str(ut.user_id),
                'status': ut.status,
                'progress_pct': round(progress_pct, 2),
                'enrolled_at': ut.enrolled_at,
                'completed_at': ut.completed_at,
            })
        return Response(results)


class ModuleViewSet(TrackExceptionHandlerMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsTeacherOrReadOnly]

    def get_queryset(self):
        queryset = Module.objects.annotate(contents_count=Count('contents')).all()

        user = self.request.user
        user_id = user.id
        role = user.role
        if role == 'TEACHER':
            visibility = Q(track__status='PUBLISHED')
        else:
            visibility = Q(
                track__status='PUBLISHED',
                track__enrollments__user_id=user_id,
                track__enrollments__status__in=['IN_PROGRESS', 'COMPLETED'],
            )
        if user_id:
            visibility |= Q(track__creator_id=user_id)
        queryset = queryset.filter(visibility).distinct()

        track_id = self.request.query_params.get('track_id')
        if track_id:
            queryset = queryset.filter(track_id=track_id)

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return ModuleListSerializer
        return ModuleSerializer

    def perform_create(self, serializer):
        track = serializer.validated_data['track']
        _ensure_track_owner(track, self.request)
        serializer.save()

    def perform_update(self, serializer):
        requested_track = serializer.validated_data.get('track')
        if requested_track and requested_track.pk != serializer.instance.track_id:
            raise ValidationError({
                'track': 'Não é permitido mover um módulo para outra trilha.'
            })
        serializer.save()

    @action(detail=True, methods=['post'])
    def reorder(self, request, pk=None):
        """Body: {"display_order": int}. Apenas o dono da trilha."""
        module = self.get_object()
        _ensure_track_owner(module.track, request)

        new_order = request.data.get('display_order')
        if new_order is None:
            raise ValidationError({"display_order": "Campo obrigatório."})
        try:
            new_order = int(new_order)
        except (TypeError, ValueError):
            raise ValidationError({"display_order": "Deve ser inteiro."})
        if new_order < 1:
            raise ValidationError({"display_order": "Deve ser >= 1."})

        module.display_order = new_order
        module.save()
        return Response(ModuleSerializer(module).data)


class ContentViewSet(TrackExceptionHandlerMixin, viewsets.ModelViewSet):
    serializer_class = ContentSerializer
    permission_classes = [IsAuthenticated, IsTeacherOrReadOnly]

    def get_queryset(self):
        queryset = Content.objects.all()

        user = self.request.user
        user_id = user.id
        role = user.role
        if role == 'TEACHER':
            visibility = Q(
                module__track__status='PUBLISHED',
                visibility='enrolled',
            )
        else:
            visibility = Q(
                module__track__status='PUBLISHED',
                module__track__enrollments__user_id=user_id,
                module__track__enrollments__status__in=['IN_PROGRESS', 'COMPLETED'],
                visibility='enrolled',
            )
        if user_id:
            visibility |= Q(module__track__creator_id=user_id)
        queryset = queryset.filter(visibility).distinct()

        module_id = self.request.query_params.get('module_id')
        if module_id:
            queryset = queryset.filter(module_id=module_id)

        return queryset

    def perform_create(self, serializer):
        module = serializer.validated_data['module']
        _ensure_track_owner(module.track, self.request)
        serializer.save()

    def perform_update(self, serializer):
        requested_module = serializer.validated_data.get('module')
        if requested_module and requested_module.pk != serializer.instance.module_id:
            raise ValidationError({
                'module': 'Não é permitido mover um conteúdo para outro módulo.'
            })
        serializer.save()

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def complete(self, request, pk=None):
        """Marca conteúdo comum como concluído para o aluno autenticado."""
        content = self.get_object()
        user_track = UserTrack.objects.filter(
            user_id=request.user.id,
            track=content.module.track,
            status__in=['IN_PROGRESS', 'COMPLETED'],
        ).first()
        if not user_track:
            raise NotFound('Você não está matriculado nesta trilha.')

        try:
            result = complete_content(user_track, content)
        except DjangoValidationError as exc:
            detail = exc.message_dict if hasattr(exc, 'message_dict') else exc.messages
            raise ValidationError(detail) from exc

        return Response(result)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated],
        url_path='uncomplete',
    )
    def uncomplete(self, request, pk=None):
        """Desmarca conteúdo comum para o aluno autenticado."""
        content = self.get_object()
        user_track = UserTrack.objects.filter(
            user_id=request.user.id,
            track=content.module.track,
            status__in=['IN_PROGRESS', 'COMPLETED'],
        ).first()
        if not user_track:
            raise NotFound('Você não está matriculado nesta trilha.')

        try:
            result = uncomplete_content(user_track, content)
        except DjangoValidationError as exc:
            detail = exc.message_dict if hasattr(exc, 'message_dict') else exc.messages
            raise ValidationError(detail) from exc

        return Response(result)

    @action(detail=True, methods=['post'])
    def reorder(self, request, pk=None):
        """Body: {"display_order": int}. Apenas o dono da trilha."""
        content = self.get_object()
        _ensure_track_owner(content.module.track, request)

        new_order = request.data.get('display_order')
        if new_order is None:
            raise ValidationError({"display_order": "Campo obrigatório."})
        try:
            new_order = int(new_order)
        except (TypeError, ValueError):
            raise ValidationError({"display_order": "Deve ser inteiro."})
        if new_order < 1:
            raise ValidationError({"display_order": "Deve ser >= 1."})

        content.display_order = new_order
        content.save()
        return Response(ContentSerializer(content).data)


class UserTrackViewSet(TrackExceptionHandlerMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UserTrackSerializer

    def get_queryset(self):
        target_user_uuid = self.request.query_params.get('user_uuid')
        if target_user_uuid:
            target_user_id = _parse_user_uuid(target_user_uuid)
            is_own_user = str(target_user_id) == str(self.request.user.id)

            if not is_own_user and self.request.user.role != 'TEACHER':
                raise PermissionDenied(
                    'Você não pode consultar as matrículas de outro aluno.'
                )

            return UserTrack.objects.filter(user_id=target_user_id)

        if self.request.user.is_authenticated:
            logged_user_id = self.request.user.id
            return UserTrack.objects.filter(user_id=logged_user_id)

        return UserTrack.objects.none()

    def perform_create(self, serializer):
        logged_user_id = self.request.user.id
        serializer.save(user_id=logged_user_id)

    @action(detail=False, methods=['get'])
    def completed(self, request):
        """Trilhas concluídas que podem ser exibidas no perfil do aluno."""
        target_user_id = _parse_user_uuid(
            request.query_params.get('user_uuid') or request.user.id
        )
        queryset = (
            UserTrack.objects.filter(
                user_id=target_user_id,
                status='COMPLETED',
                track__status='PUBLISHED',
            )
            .select_related('track')
            .order_by('-completed_at', 'track__title')
        )

        serializer = CompletedTrackSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Trilhas do aluno atual com progresso agregado."""
        user_id = request.user.id
        queryset = UserTrack.objects.filter(user_id=user_id).select_related('track')

        results = []
        for ut in queryset:
            total_modules = ut.track.modules.count()
            completed = ut.module_progress.filter(status='COMPLETED').count()
            progress_pct = (completed / total_modules * 100) if total_modules else 0
            results.append({
                'id': str(ut.id),
                'track_id': str(ut.track.id),
                'track_title': ut.track.title,
                'status': ut.status,
                'progress_pct': round(progress_pct, 2),
                'enrolled_at': ut.enrolled_at,
                'completed_at': ut.completed_at,
            })
        return Response(results)

    @action(detail=False, methods=['get'])
    def top(self, request):
        """Trilhas em que o usuário está MAIS AVANÇADO — widget "MINHAS TRILHAS".

        Lista as trilhas matriculadas (em andamento ou concluídas, publicadas),
        ordenadas por progresso decrescente e limitadas a `limit` (padrão 3).
        Aceita `user_uuid` para ver as trilhas de outro usuário (perfil de
        terceiros); sem ele, usa o usuário logado. Professores não se matriculam,
        então o resultado é naturalmente vazio para o perfil de um docente.
        """
        target_user_id = _parse_user_uuid(
            request.query_params.get('user_uuid') or request.user.id
        )

        try:
            limit = int(request.query_params.get('limit', 3))
        except (TypeError, ValueError):
            limit = 3
        limit = max(1, min(limit, 10))

        queryset = (
            UserTrack.objects.filter(
                user_id=target_user_id,
                status__in=['IN_PROGRESS', 'COMPLETED'],
                track__status='PUBLISHED',
            )
            .select_related('track')
        )

        results = []
        for ut in queryset:
            total_modules = ut.track.modules.count()
            completed_modules = ut.module_progress.filter(status='COMPLETED').count()
            progress_pct = (completed_modules / total_modules * 100) if total_modules else 0
            results.append({
                'track_id': str(ut.track.id),
                'track_title': ut.track.title,
                'status': ut.status,
                'completed_modules': completed_modules,
                'total_modules': total_modules,
                'progress_pct': round(progress_pct, 2),
            })

        results.sort(key=lambda item: item['progress_pct'], reverse=True)
        return Response(results[:limit])

    @action(detail=True, methods=['post'])
    def drop(self, request, pk=None):
        """Aluno desiste de uma trilha (status → DROPPED). Só o próprio aluno."""
        user_track = self.get_object()
        user_id = request.user.id
        if str(user_track.user_id) != str(user_id):
            raise PermissionDenied("Você só pode desistir das suas próprias inscrições.")

        if user_track.status == 'DROPPED':
            raise ValidationError({"status": "Inscrição já está marcada como DROPPED."})
        if user_track.status == 'COMPLETED':
            raise ValidationError({"status": "Não é possível desistir de uma trilha já concluída."})

        user_track.status = 'DROPPED'
        user_track.save()
        return Response(UserTrackSerializer(user_track, context={'request': request}).data)


class UserModuleProgressViewSet(TrackExceptionHandlerMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UserModuleProgressSerializer

    def get_queryset(self):
        return UserModuleProgress.objects.filter(
            user_track__user_id=self.request.user.id
        )


class UserContentProgressViewSet(TrackExceptionHandlerMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UserContentProgressSerializer

    def get_queryset(self):
        return UserContentProgress.objects.filter(
            user_track__user_id=self.request.user.id
        )


class ChallengeSubmissionViewSet(TrackExceptionHandlerMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ChallengeSubmission.objects.all()
    serializer_class = ChallengeSubmissionSerializer

    def get_queryset(self):
        """Aluno vê as próprias; professor vê as das trilhas que criou."""
        if not self.request.user.is_authenticated:
            return ChallengeSubmission.objects.none()

        user_id = self.request.user.id
        role = self.request.user.role

        if role == 'TEACHER':
            return ChallengeSubmission.objects.filter(
                challenge__module__track__creator_id=user_id
            )
        return ChallengeSubmission.objects.filter(user_track__user_id=user_id)

    def perform_create(self, serializer):
        submission = serializer.save(ai_status='PENDING_AI')
        transaction.on_commit(
            lambda: evaluate_challenge_submission.delay(str(submission.pk))
        )

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def approve(self, request, pk=None):
        """Professor aprova manualmente uma submissão. Só o dono da trilha."""
        submission = self.get_object()
        _ensure_track_owner(submission.challenge.module.track, request)
        if request.user.role != 'TEACHER':
            raise PermissionDenied("Apenas professores podem aprovar submissões.")

        submission.ai_status = 'EVALUATED'
        if submission.ai_score is None:
            submission.ai_score = 100
        if not submission.evaluated_at:
            submission.evaluated_at = timezone.now()
        if not submission.ai_feedback:
            submission.ai_feedback = "Aprovado manualmente pelo professor."
        submission.save()

        try:
            complete_content(
                submission.user_track,
                submission.challenge,
                allow_challenge=True,
            )
        except DjangoValidationError as exc:
            detail = exc.message_dict if hasattr(exc, 'message_dict') else exc.messages
            raise ValidationError(detail) from exc

        return Response(ChallengeSubmissionSerializer(submission).data)

    @action(detail=False, methods=['get'], url_path='pending-review')
    def pending_review(self, request):
        """Submissões avaliadas pela IA aguardando ação do professor."""
        if request.user.role != 'TEACHER':
            raise PermissionDenied("Apenas professores podem acessar este painel.")

        user_id = request.user.id
        queryset = ChallengeSubmission.objects.filter(
            challenge__module__track__creator_id=user_id,
            ai_status='EVALUATED',
        ).order_by('-evaluated_at')

        return Response(ChallengeSubmissionSerializer(queryset, many=True).data)
