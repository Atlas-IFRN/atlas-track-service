from apps.tracks.models import UserTrack


NOT_ENROLLED_PROGRESS = {
    'enrolled': False,
    'completed_modules': 0,
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

    total_modules = track.modules.count()
    completed_modules = user_track.module_progress.filter(status='COMPLETED').count()
    percentage = round((completed_modules / total_modules) * 100, 2) if total_modules else 0

    return {
        'enrolled': True,
        'completed_modules': completed_modules,
        'percentage': percentage,
    }
