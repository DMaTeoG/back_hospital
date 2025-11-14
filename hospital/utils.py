from __future__ import annotations

from django.conf import settings

from .models import AuditLog


def register_audit(user, action: str, entity: str, entity_id: str, payload=None, ip=None):
    if not getattr(settings, 'AUDIT_ENABLED', True):
        return
    AuditLog.objects.create(
        user=user,
        action=action,
        entity=entity,
        entity_id=str(entity_id),
        payload=payload or {},
        ip=ip,
    )
