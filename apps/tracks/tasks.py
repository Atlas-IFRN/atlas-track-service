import logging

import requests
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import ChallengeSubmission

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="tracks.evaluate_challenge_submission",
    autoretry_for=(requests.RequestException,),
    retry_backoff=True,
    retry_backoff_max=60,
    max_retries=3,
    acks_late=True,
)
def evaluate_challenge_submission(self, submission_id: str) -> dict:
    """Envia o desafio + repositório ao ai-service e persiste o resultado no submission."""
    try:
        submission = ChallengeSubmission.objects.select_related(
            'user_track', 'challenge'
        ).get(pk=submission_id)
    except ChallengeSubmission.DoesNotExist:
        logger.error("ChallengeSubmission %s não encontrada — abortando task.", submission_id)
        return {"status": "not_found", "submission_id": submission_id}

    ChallengeSubmission.objects.filter(pk=submission.pk).update(ai_status='EVALUATING')

    challenge = submission.challenge
    payload = {
        "user_id": str(submission.user_track.user_id),
        "challenge_id": str(challenge.id),
        "github_repo_url": submission.github_url,
        "language": (challenge.language or "python").strip(),
        "criteria": challenge.evaluation_criteria or {},
        "challenge_description": challenge.instructions or "",
        "theme": challenge.title or None,
    }

    url = f"{settings.AI_SERVICE_URL.rstrip('/')}/analyze"
    logger.info("Disparando avaliação IA submission=%s -> %s", submission.pk, url)

    try:
        response = requests.post(url, json=payload, timeout=settings.AI_SERVICE_TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        logger.exception("Falha de rede ao chamar ai-service para submission %s", submission.pk)
        ChallengeSubmission.objects.filter(pk=submission.pk).update(
            ai_status='FAILED',
            ai_feedback=f"Falha ao contatar serviço de IA: {exc}",
            evaluated_at=timezone.now(),
        )
        raise
    except ValueError as exc:
        logger.exception("Resposta do ai-service não é JSON válido para submission %s", submission.pk)
        ChallengeSubmission.objects.filter(pk=submission.pk).update(
            ai_status='FAILED',
            ai_feedback=f"Resposta inválida do serviço de IA: {exc}",
            evaluated_at=timezone.now(),
        )
        return {"status": "invalid_response", "submission_id": submission_id}

    ChallengeSubmission.objects.filter(pk=submission.pk).update(
        ai_status='EVALUATED',
        ai_score=data.get('score'),
        ai_feedback=data.get('feedback') or '',
        ai_criteries=data.get('criteries') or [],
        evaluated_at=timezone.now(),
    )

    logger.info("Submission %s avaliada com score=%s", submission.pk, data.get('score'))
    return {
        "status": "evaluated",
        "submission_id": submission_id,
        "score": data.get('score'),
    }
