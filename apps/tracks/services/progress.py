from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.tracks.models import (
    Content,
    UserContentProgress,
    UserModuleProgress,
    UserTrack,
)


NOT_ENROLLED_PROGRESS = {
    'enrolled': False,
    'completed_modules': 0,
    'completed_content_ids': [],
    'percentage': 0,
}


def get_track_user_progress(track, user_id, role=None):
    if role == 'TEACHER':
        return None

    if not user_id:
        return NOT_ENROLLED_PROGRESS.copy()

    user_track = UserTrack.objects.filter(
        user_id=user_id,
        track=track,
        status__in=['IN_PROGRESS', 'COMPLETED'],
    ).first()
    if not user_track:
        return NOT_ENROLLED_PROGRESS.copy()

    total_contents = Content.objects.filter(module__track=track).count()
    completed_modules = user_track.module_progress.filter(status='COMPLETED').count()
    completed_content_ids = list(
        user_track.content_progress.filter(status='COMPLETED').values_list(
            'content_id', flat=True
        )
    )
    percentage = (
        round((len(completed_content_ids) / total_contents) * 100, 2)
        if total_contents
        else 0
    )

    return {
        'enrolled': True,
        'completed_modules': completed_modules,
        'completed_content_ids': completed_content_ids,
        'percentage': percentage,
    }


@transaction.atomic
def complete_content(user_track, content, *, allow_challenge=False):
    """Conclui um conteúdo e recalcula módulo e trilha de forma idempotente."""
    if user_track.track_id != content.module.track_id:
        raise ValidationError('O conteúdo não pertence à trilha desta matrícula.')

    if user_track.status not in {'IN_PROGRESS', 'COMPLETED'}:
        raise ValidationError('A matrícula não está ativa.')

    if content.content_type == 'CHALLENGE' and not allow_challenge:
        raise ValidationError(
            'Desafios são concluídos automaticamente após aprovação na avaliação.'
        )

    now = timezone.now()
    content_progress, _ = UserContentProgress.objects.select_for_update().get_or_create(
        user_track=user_track,
        content=content,
    )

    if content_progress.status != 'COMPLETED':
        content_progress.status = 'COMPLETED'
        content_progress.completed_at = now
        content_progress.save()

    module = content.module
    module_content_ids = list(module.contents.values_list('id', flat=True))
    completed_in_module = user_track.content_progress.filter(
        content_id__in=module_content_ids,
        status='COMPLETED',
    ).count()
    module_total = len(module_content_ids)
    module_percentage = (
        round((completed_in_module / module_total) * 100, 2)
        if module_total
        else 0
    )

    module_progress, _ = UserModuleProgress.objects.select_for_update().get_or_create(
        user_track=user_track,
        module=module,
    )
    module_progress.progress_pct = module_percentage
    module_progress.status = (
        'COMPLETED' if module_total and completed_in_module == module_total else 'IN_PROGRESS'
    )
    module_progress.completed_at = (
        now if module_progress.status == 'COMPLETED' else None
    )
    module_progress.save()

    track_content_ids = list(
        Content.objects.filter(module__track=user_track.track).values_list('id', flat=True)
    )
    completed_in_track = user_track.content_progress.filter(
        content_id__in=track_content_ids,
        status='COMPLETED',
    ).count()
    track_total = len(track_content_ids)
    track_completed = bool(track_total and completed_in_track == track_total)

    if track_completed and user_track.status != 'COMPLETED':
        user_track.status = 'COMPLETED'
        user_track.completed_at = now
        user_track.save(update_fields=['status', 'completed_at'])

    next_content = (
        Content.objects.filter(module__track=user_track.track)
        .exclude(
            id__in=user_track.content_progress.filter(status='COMPLETED').values(
                'content_id'
            )
        )
        .order_by('module__display_order', 'module__created_at', 'display_order', 'created_at')
        .first()
    )

    return {
        'content_id': str(content.id),
        'content_completed': True,
        'module_completed': module_progress.status == 'COMPLETED',
        'track_completed': track_completed,
        'percentage': round((completed_in_track / track_total) * 100, 2)
        if track_total
        else 0,
        'next_content': {
            'id': str(next_content.id),
            'module_id': str(next_content.module_id),
            'title': next_content.title,
        }
        if next_content
        else None,
    }


@transaction.atomic
def uncomplete_content(user_track, content):
    """Desmarca um conteúdo comum e recalcula o progresso agregado."""
    if user_track.track_id != content.module.track_id:
        raise ValidationError('O conteúdo não pertence à trilha desta matrícula.')

    if content.content_type == 'CHALLENGE':
        raise ValidationError('Desafios aprovados não podem ser desmarcados manualmente.')

    content_progress = UserContentProgress.objects.select_for_update().filter(
        user_track=user_track,
        content=content,
    ).first()
    if content_progress and content_progress.status == 'COMPLETED':
        content_progress.status = 'PENDING'
        content_progress.completed_at = None
        content_progress.save()

    module = content.module
    module_content_ids = list(module.contents.values_list('id', flat=True))
    completed_in_module = user_track.content_progress.filter(
        content_id__in=module_content_ids,
        status='COMPLETED',
    ).count()
    module_total = len(module_content_ids)
    module_percentage = (
        round((completed_in_module / module_total) * 100, 2)
        if module_total
        else 0
    )

    module_progress, _ = UserModuleProgress.objects.select_for_update().get_or_create(
        user_track=user_track,
        module=module,
    )
    module_progress.progress_pct = module_percentage
    module_progress.status = 'IN_PROGRESS' if completed_in_module else 'PENDING'
    module_progress.completed_at = None
    module_progress.save()

    track_content_ids = list(
        Content.objects.filter(module__track=user_track.track).values_list('id', flat=True)
    )
    completed_in_track = user_track.content_progress.filter(
        content_id__in=track_content_ids,
        status='COMPLETED',
    ).count()
    track_total = len(track_content_ids)

    if user_track.status == 'COMPLETED':
        user_track.status = 'IN_PROGRESS'
        user_track.completed_at = None
        user_track.save(update_fields=['status', 'completed_at'])

    return {
        'content_id': str(content.id),
        'content_completed': False,
        'module_completed': False,
        'track_completed': False,
        'percentage': round((completed_in_track / track_total) * 100, 2)
        if track_total
        else 0,
        'next_content': None,
    }
