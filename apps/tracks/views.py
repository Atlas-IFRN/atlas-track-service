from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from .models import ChallengeSubmission, Content, Module, Track, UserContentProgress, UserModuleProgress, UserTrack
from .permissions import IsAuthenticatedViaRPC, IsTeacherOrReadOnly
from .serializers import (
    ChallengeSubmissionSerializer,
    ContentSerializer,
    ModuleListSerializer,
    ModuleSerializer,
    TrackListSerializer,
    TrackSerializer,
    UserContentProgressSerializer,
    UserModuleProgressSerializer,
    UserTrackSerializer,
)
from .tasks import evaluate_challenge_submission


def _ensure_track_owner(track: Track, request) -> None:
    """Bloqueia ação se o usuário logado não for o criador da trilha."""
    user_id = request.auth.get('user_id') if request.auth else None
    if str(track.creator_id) != str(user_id):
        raise PermissionDenied("Apenas o criador da trilha pode executar esta ação.")


class TrackViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedViaRPC, IsTeacherOrReadOnly]

    def get_queryset(self):
        return Track.objects.annotate(modules_count=Count('modules')).all()

    def get_serializer_class(self):
        if self.action == 'list':
            return TrackListSerializer
        return TrackSerializer

    def perform_create(self, serializer):
        logged_user_id = self.request.auth.get('user_id')
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
        return Response(TrackSerializer(track).data)

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Muda status para ARCHIVED."""
        track = self.get_object()
        _ensure_track_owner(track, request)

        track.status = 'ARCHIVED'
        track.save()
        return Response(TrackSerializer(track).data)

    @action(detail=False, methods=['get'], url_path='me/teaching')
    def me_teaching(self, request):
        """Trilhas criadas pelo professor atual + contagem de inscritos."""
        if request.auth.get('role') != 'TEACHER':
            raise PermissionDenied("Apenas professores podem acessar este painel.")

        user_id = request.auth.get('user_id')
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


class ModuleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedViaRPC, IsTeacherOrReadOnly]

    def get_queryset(self):
        queryset = Module.objects.annotate(contents_count=Count('contents')).all()

        track_id = self.request.query_params.get('track_id')
        if track_id:
            queryset = queryset.filter(track_id=track_id)

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return ModuleListSerializer
        return ModuleSerializer

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


class ContentViewSet(viewsets.ModelViewSet):
    serializer_class = ContentSerializer
    permission_classes = [IsAuthenticatedViaRPC, IsTeacherOrReadOnly]

    def get_queryset(self):
        queryset = Content.objects.all()

        module_id = self.request.query_params.get('module_id')
        if module_id:
            queryset = queryset.filter(module_id=module_id)

        return queryset

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


class UserTrackViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedViaRPC]
    serializer_class = UserTrackSerializer

    def get_queryset(self):
        target_user_uuid = self.request.query_params.get('user_uuid')
        if target_user_uuid:
            return UserTrack.objects.filter(user_id=target_user_uuid)

        if self.request.auth:
            logged_user_id = self.request.auth.get('user_id')
            return UserTrack.objects.filter(user_id=logged_user_id)

        return UserTrack.objects.none()

    def perform_create(self, serializer):
        logged_user_id = self.request.auth.get('user_id')
        serializer.save(user_id=logged_user_id)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Trilhas do aluno atual com progresso agregado."""
        user_id = request.auth.get('user_id')
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

    @action(detail=True, methods=['post'])
    def drop(self, request, pk=None):
        """Aluno desiste de uma trilha (status → DROPPED). Só o próprio aluno."""
        user_track = self.get_object()
        user_id = request.auth.get('user_id')
        if str(user_track.user_id) != str(user_id):
            raise PermissionDenied("Você só pode desistir das suas próprias inscrições.")

        if user_track.status == 'DROPPED':
            raise ValidationError({"status": "Inscrição já está marcada como DROPPED."})
        if user_track.status == 'COMPLETED':
            raise ValidationError({"status": "Não é possível desistir de uma trilha já concluída."})

        user_track.status = 'DROPPED'
        user_track.save()
        return Response(UserTrackSerializer(user_track, context={'request': request}).data)


class UserModuleProgressViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedViaRPC]
    queryset = UserModuleProgress.objects.all()
    serializer_class = UserModuleProgressSerializer


class UserContentProgressViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedViaRPC]
    queryset = UserContentProgress.objects.all()
    serializer_class = UserContentProgressSerializer


class ChallengeSubmissionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedViaRPC]
    queryset = ChallengeSubmission.objects.all()
    serializer_class = ChallengeSubmissionSerializer

    def get_queryset(self):
        """Aluno vê as próprias; professor vê as das trilhas que criou."""
        if not self.request.auth:
            return ChallengeSubmission.objects.none()

        user_id = self.request.auth.get('user_id')
        role = self.request.auth.get('role')

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
    def approve(self, request, pk=None):
        """Professor aprova manualmente uma submissão. Só o dono da trilha."""
        submission = self.get_object()
        _ensure_track_owner(submission.challenge.module.track, request)
        if request.auth.get('role') != 'TEACHER':
            raise PermissionDenied("Apenas professores podem aprovar submissões.")

        submission.ai_status = 'EVALUATED'
        if submission.ai_score is None:
            submission.ai_score = 100
        if not submission.evaluated_at:
            submission.evaluated_at = timezone.now()
        if not submission.ai_feedback:
            submission.ai_feedback = "Aprovado manualmente pelo professor."
        submission.save()
        return Response(ChallengeSubmissionSerializer(submission).data)

    @action(detail=False, methods=['get'], url_path='pending-review')
    def pending_review(self, request):
        """Submissões avaliadas pela IA aguardando ação do professor."""
        if request.auth.get('role') != 'TEACHER':
            raise PermissionDenied("Apenas professores podem acessar este painel.")

        user_id = request.auth.get('user_id')
        queryset = ChallengeSubmission.objects.filter(
            challenge__module__track__creator_id=user_id,
            ai_status='EVALUATED',
        ).order_by('-evaluated_at')

        return Response(ChallengeSubmissionSerializer(queryset, many=True).data)
