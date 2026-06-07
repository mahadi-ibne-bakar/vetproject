"""
Utility functions for VetProject core app.
"""

import logging
logger = logging.getLogger(__name__)


def get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def log_action(request, action, description, target_id=None, target_type=''):
    """
    Creates an AuditLog entry for a significant admin action.

    Args:
        request:     Django request (for actor and IP)
        action:      AuditLog.Action choice string
        description: Human-readable description of what happened
        target_id:   PK of the affected object (optional)
        target_type: Model name of the affected object (optional)
    """
    from core.models import AuditLog
    try:
        AuditLog.objects.create(
            actor       = request.user if request.user.is_authenticated else None,
            action      = action,
            description = description,
            target_id   = target_id,
            target_type = target_type,
            ip_address  = get_client_ip(request),
        )
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")