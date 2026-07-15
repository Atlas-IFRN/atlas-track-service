from django.db.models.signals import m2m_changed, post_delete, post_save, pre_save
from django.dispatch import receiver

from .audit import get_current_actor_id, snapshot_instance
from .models import (
    AuditAction,
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


AUDITED_MODELS = {
    TrackCategory: 'track_category',
    Skill: 'skill',
    Track: 'track',
    Module: 'module',
    Content: 'content',
    UserTrack: 'user_track',
    UserModuleProgress: 'user_module_progress',
    UserContentProgress: 'user_content_progress',
    ChallengeSubmission: 'challenge_submission',
}


def _instance_actor_id(instance):
    return get_current_actor_id()


def _write_log(instance, action, payload):
    AuditLog.objects.create(
        table_name=AUDITED_MODELS[type(instance)],
        action=action,
        record_id=instance.pk,
        user_id=_instance_actor_id(instance),
        payload=payload,
    )


def capture_before_save(sender, instance, **kwargs):
    instance._audit_before = None
    if instance.pk:
        previous = sender._default_manager.filter(pk=instance.pk).first()
        if previous is not None:
            instance._audit_before = snapshot_instance(previous)


def audit_after_save(sender, instance, created, **kwargs):
    after = snapshot_instance(instance)
    if created:
        _write_log(instance, AuditAction.CREATE, {'after': after})
        return

    _write_log(
        instance,
        AuditAction.UPDATE,
        {'before': getattr(instance, '_audit_before', None), 'after': after},
    )


def audit_after_delete(sender, instance, **kwargs):
    _write_log(instance, AuditAction.DELETE, {'before': snapshot_instance(instance)})


for audited_model in AUDITED_MODELS:
    pre_save.connect(
        capture_before_save,
        sender=audited_model,
        dispatch_uid=f'tracks_audit_pre_save_{audited_model._meta.label_lower}',
    )
    post_save.connect(
        audit_after_save,
        sender=audited_model,
        dispatch_uid=f'tracks_audit_post_save_{audited_model._meta.label_lower}',
    )
    post_delete.connect(
        audit_after_delete,
        sender=audited_model,
        dispatch_uid=f'tracks_audit_post_delete_{audited_model._meta.label_lower}',
    )


@receiver(m2m_changed, sender=Track.skills.through)
def audit_track_skills(sender, instance, action, pk_set, **kwargs):
    if action not in {'post_add', 'post_remove', 'post_clear'}:
        return

    _write_log(
        instance,
        AuditAction.UPDATE,
        {
            'relation': 'skills',
            'operation': action.removeprefix('post_'),
            'related_ids': sorted(str(pk) for pk in (pk_set or [])),
        },
    )
