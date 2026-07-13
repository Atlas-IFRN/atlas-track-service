"""
Publicação de notificações do track (produtor de eventos).

Quando um desafio é avaliado, o track-service PUBLICA o evento
`notifications.create` na fila do RabbitMQ — sem HTTP e sem conhecer a API/DB do
notification-service, que é o dono do consumo. Mesmo padrão do auth/feed.

Best-effort: qualquer falha (broker fora, etc.) é apenas logada, nunca
propagada, para não interromper a avaliação. Cada evento leva um `event_id`
para idempotência no consumidor. O `type` é `track` (usado pelo frontend para
escolher o ícone da notificação).
"""
import logging
import uuid

from django.conf import settings

from config.celery import app as celery_app

logger = logging.getLogger(__name__)

TYPE_TRACK = "track"


def send_notification(user_id, title, message):
    """Publica um evento de notificação do tipo `track` (fire-and-forget)."""
    try:
        celery_app.send_task(
            "notifications.create",
            kwargs={
                "user_id": str(user_id),
                "title": title,
                "message": message,
                "type": TYPE_TRACK,
                "event_id": str(uuid.uuid4()),
            },
            queue=settings.NOTIFICATIONS_QUEUE,
            retry=False,
        )
    except Exception:
        logger.exception("Falha ao publicar notificação de track para %s", user_id)
