import logging

import requests
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import ChallengeSubmission

logger = logging.getLogger(__name__)


def _build_challenge_description(challenge) -> str:
    description = challenge.instructions or ""
    if not challenge.technical_requirements:
        return description

    formatted_requirements = "\n".join(
        f"- {requirement}"
        for requirement in challenge.technical_requirements
    )
    return (
        f"{description}\n\n"
        f"Requisitos técnicos obrigatórios:\n{formatted_requirements}"
    ).strip()


def _extract_ai_detail(response: requests.Response) -> str:
    """Tira a string `detail` do JSON do ai-service (FastAPI HTTPException).

    Usado pra surfaçar a causa real ("Stack não corresponde...", "git clone falhou...")
    no `ai_feedback` em vez de "400 Client Error" puro, que não diz nada ao aluno.
    """
    try:
        data = response.json()
    except ValueError:
        return response.text[:500] or response.reason
    detail = data.get("detail") if isinstance(data, dict) else None
    if isinstance(detail, str):
        return detail
    if detail is not None:
        return str(detail)[:500]
    return response.text[:500] or response.reason


@shared_task(
    bind=True,
    name="tracks.evaluate_challenge_submission",
    # Retentamos apenas erros de rede e 5xx (transientes). 4xx é erro do cliente
    # (mismatch de stack, URL inválida) — retry não muda o resultado, então marca
    # FAILED de imediato com a mensagem do ai-service (vide bloco 4xx no corpo).
    autoretry_for=(requests.ConnectionError, requests.Timeout, requests.HTTPError),
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
        "challenge_description": _build_challenge_description(challenge),
        "theme": challenge.title or None,
    }

    url = f"{settings.AI_SERVICE_URL.rstrip('/')}/analyze"
    logger.info("Disparando avaliação IA submission=%s -> %s", submission.pk, url)

    try:
        response = requests.post(url, json=payload, timeout=settings.AI_SERVICE_TIMEOUT)
    except (requests.ConnectionError, requests.Timeout) as exc:
        logger.exception("Falha de rede ao chamar ai-service para submission %s", submission.pk)
        ChallengeSubmission.objects.filter(pk=submission.pk).update(
            ai_status='FAILED',
            ai_feedback=f"Falha de rede ao contatar serviço de IA: {exc}",
            evaluated_at=timezone.now(),
        )
        raise

    if 400 <= response.status_code < 500:
        detail = _extract_ai_detail(response)
        logger.warning(
            "ai-service rejeitou submission %s com %s: %s",
            submission.pk, response.status_code, detail,
        )
        ChallengeSubmission.objects.filter(pk=submission.pk).update(
            ai_status='FAILED',
            ai_feedback=detail,
            evaluated_at=timezone.now(),
        )
        return {"status": "rejected", "submission_id": submission_id, "detail": detail}

    if response.status_code >= 500:
        detail = _extract_ai_detail(response)
        logger.error(
            "ai-service falhou (5xx) para submission %s: %s %s",
            submission.pk, response.status_code, detail,
        )
        # 5xx é transiente — deixa o autoretry tentar de novo via HTTPError.
        response.raise_for_status()

    try:
        data = response.json()
    except ValueError as exc:
        logger.exception("Resposta do ai-service não é JSON válido para submission %s", submission.pk)
        ChallengeSubmission.objects.filter(pk=submission.pk).update(
            ai_status='FAILED',
            ai_feedback=f"Resposta inválida do serviço de IA: {exc}",
            evaluated_at=timezone.now(),
        )
        return {"status": "invalid_response", "submission_id": submission_id}
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
