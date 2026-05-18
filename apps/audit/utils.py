"""AEC Cinemas – Audit Shield Utils & Service Layer"""
import json
from django.forms.models import model_to_dict
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """Enhanced error handler that logs DB errors and returns clear messages."""
    import logging
    logger = logging.getLogger('aec_cinemas.audit')

    response = exception_handler(exc, context)

    if response is None:
        logger.error(f"Unhandled exception in {context.get('view')}: {exc}", exc_info=True)
        return Response(
            {'error': 'An unexpected server error occurred. Please contact your administrator.',
             'detail': str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # Enrich the response with context
    if response.status_code == 400:
        response.data['_hint'] = 'Validation failed. Check all required fields.'
    elif response.status_code == 403:
        response.data['_hint'] = 'You do not have permission for this action.'

    return response


def snapshot_model(instance) -> dict:
    """Serialize a model instance to a JSON-safe dict."""
    try:
        data = model_to_dict(instance)
        # Make Decimal/date serializable
        return {k: str(v) if hasattr(v, '__str__') and not isinstance(v, (str, int, float, bool, type(None))) else v
                for k, v in data.items()}
    except Exception:
        return {'__repr__': str(instance)}


def log_deletion(instance, user, reason=''):
    """Write a DeletedLog record before an object is deleted."""
    from apps.audit.models import DeletedLog
    DeletedLog.objects.create(
        table_name=instance.__class__.__name__,
        record_id=instance.pk,
        record_repr=str(instance),
        original_data=snapshot_model(instance),
        deleted_by=user,
        deletion_reason=reason,
    )


def log_change(instance, user, action, changes=None, ip=None, before_json=None, after_json=None):
    """Write a ChangeLog record for create/update."""
    from apps.audit.models import ChangeLog
    tenant_id = getattr(instance, 'tenant_id', None)
    if not tenant_id and getattr(user, 'tenant_id', None):
        tenant_id = user.tenant_id
        
    ChangeLog.objects.create(
        tenant_id=tenant_id,
        table_name=instance.__class__.__name__,
        record_id=instance.pk,
        action=action,
        changed_by=user,
        changes=changes or {},
        before_json=before_json,
        after_json=after_json,
        ip_address=ip,
    )


def log_audit_shield_event(user, module, record_id, action_type, old_value=None, new_value=None, approval_status='', alert_status='', sync_ref='', remarks=''):
    """Write an AuditShieldLog event record centrally for any sensitive action in the system."""
    from apps.audit.models import AuditShieldLog
    tenant_id = getattr(user, 'tenant_id', None)
    
    return AuditShieldLog.objects.create(
        tenant_id=tenant_id,
        module=module,
        record_id=record_id,
        action_type=action_type,
        user=user,
        old_value=old_value or {},
        new_value=new_value or {},
        approval_status=approval_status,
        alert_status=alert_status,
        sync_ref=sync_ref,
        remarks=remarks
    )

