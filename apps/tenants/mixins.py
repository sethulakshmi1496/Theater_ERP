"""
AEC Cinemas Platform – Tenant Scoping Layer (v2 — test-verified)
================================================================
Module 2: Tenant Query Scoping and Request Context

Fixes applied post-test-run:
  - perform_create uses serializer.instance model introspection correctly
  - get_tenant_from_request is the single authoritative resolver
  - TenantQuerysetMixin returns qs.none() for unresolved tenants on tenant models
  - TenantCreateMixin reads tenant from request.tenant, never from body
"""

import logging
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.exceptions import NotFound

logger = logging.getLogger(__name__)


# ─── Core resolver ───────────────────────────────────────────────────────────

def get_tenant_from_request(request):
    """
    Single authoritative function to resolve tenant from a DRF request.
    Order of resolution:
      1. request.tenant (set by TenantMiddleware)
      2. request.user.tenant (direct FK, works in tests without middleware)
    Returns None if not resolvable.
    """
    # Middleware path (production)
    tenant = getattr(request, 'tenant', None)
    if tenant is not None:
        return tenant

    # Fallback for tests / direct invocations
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        return getattr(user, 'tenant', None)

    return None


def _model_has_tenant_field(model_class) -> bool:
    """Return True if this model has a 'tenant' database field."""
    try:
        model_class._meta.get_field('tenant')
        return True
    except Exception:
        return False


# ─── Permission ───────────────────────────────────────────────────────────────

class HasTenantPermission(BasePermission):
    """
    Rejects requests from authenticated users with no tenant assigned.
    Acts as a safety net for orphaned accounts.
    """
    message = 'Your account is not linked to a tenant. Contact the platform administrator.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return True
        tenant = get_tenant_from_request(request)
        if tenant is None:
            logger.warning(
                f'[TENANT] User {request.user.id} ({request.user.email}) '
                f'has no tenant. Blocking request to {request.path}'
            )
            return False
        return True


# ─── Queryset Mixin ───────────────────────────────────────────────────────────

class TenantQuerysetMixin:
    """
    Auto-scopes any ViewSet queryset to the authenticated user's tenant.

    - If model has `tenant` field: filters to request.tenant
    - If model has no `tenant` field: passes through unchanged (safe)
    - No tenant resolved + tenant model: returns qs.none() (hard safety net)
    """

    def get_queryset(self):
        qs = super().get_queryset()
        tenant = get_tenant_from_request(self.request)

        if not _model_has_tenant_field(qs.model):
            return qs

        if tenant is None:
            logger.warning(
                f'[TENANT SCOPE] No tenant resolved for {qs.model.__name__}. '
                f'Returning empty queryset.'
            )
            return qs.none()

        return qs.filter(tenant=tenant)


# ─── Create / Write Mixin ─────────────────────────────────────────────────────

class TenantCreateMixin:
    """
    Auto-stamps `tenant` from request context on every create.
    The `tenant` field is NEVER accepted from the request body.
    """

    def _get_model_fields(self, serializer):
        try:
            return [f.name for f in serializer.Meta.model._meta.get_fields()]
        except AttributeError:
            return []

    def perform_create(self, serializer):
        kwargs = {}
        tenant = get_tenant_from_request(self.request)
        fields = self._get_model_fields(serializer)

        if 'tenant' in fields and tenant:
            kwargs['tenant'] = tenant

        if 'entered_by' in fields:
            kwargs['entered_by'] = self.request.user

        serializer.save(**kwargs)

    def perform_update(self, serializer):
        # Strip tenant from validated data — tenant can never change
        serializer.validated_data.pop('tenant', None)
        serializer.save()


# ─── Per-Object Cross-Tenant Guard ────────────────────────────────────────────

class TenantObjectGuardMixin:
    """
    Guards individual object retrieval. Returns 404 (not 403) for cross-tenant
    access to avoid leaking record existence.
    """

    def get_object(self):
        obj = super().get_object()
        tenant = get_tenant_from_request(self.request)

        if tenant and _model_has_tenant_field(obj.__class__):
            if obj.tenant_id != tenant.id:
                logger.warning(
                    f'[TENANT ISOLATION] User {self.request.user.id} (tenant={tenant.id}) '
                    f'attempted access to {obj.__class__.__name__}#{obj.pk} '
                    f'(tenant={obj.tenant_id}). Blocked with 404.'
                )
                raise NotFound()

        return obj


# ─── Combined Mixin for Standard ViewSets ─────────────────────────────────────

class TenantSafeMixin(TenantQuerysetMixin, TenantObjectGuardMixin, TenantCreateMixin):
    """
    Primary mixin for all tenant-owned ViewSets.
    Provides: scoped reads + object guard + tenant-stamped writes.
    """
    pass


# ─── Audit-aware Mixin (for operational ViewSets) ─────────────────────────────

class AuditShieldMixin:
    """
    Enforces: Staff cannot DELETE.
    Logs every create/update/delete to the audit ChangeLog.
    Now tenant-aware via per-model field inspection.
    """

    def _get_model_fields(self, serializer):
        try:
            return [f.name for f in serializer.Meta.model._meta.get_fields()]
        except AttributeError:
            return []

    def destroy(self, request, *args, **kwargs):
        if request.user.role == 'STAFF':
            return Response(
                {'error': 'Staff are not permitted to delete records. Contact your Admin.'},
                status=status.HTTP_403_FORBIDDEN
            )
        instance = self.get_object()
        reason = request.data.get('reason', 'No reason provided')
        from apps.audit.utils import log_deletion
        log_deletion(instance, request.user, reason)
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        kwargs = {}
        tenant = get_tenant_from_request(self.request)
        fields = self._get_model_fields(serializer)

        if 'tenant' in fields and tenant:
            kwargs['tenant'] = tenant

        if 'entered_by' in fields:
            kwargs['entered_by'] = self.request.user

        instance = serializer.save(**kwargs)
        from apps.audit.utils import log_change, snapshot_model
        log_change(
            instance=instance, 
            user=self.request.user, 
            action='CREATE', 
            after_json=snapshot_model(instance),
            ip=self.request.META.get('REMOTE_ADDR')
        )

    def perform_update(self, serializer):
        serializer.validated_data.pop('tenant', None)
        obj = self.get_object()
        from apps.audit.utils import snapshot_model, log_change
        before_data = snapshot_model(obj)
        instance = serializer.save()
        after_data = snapshot_model(instance)
        log_change(
            instance=instance, 
            user=self.request.user, 
            action='UPDATE', 
            before_json=before_data,
            after_json=after_data,
            ip=self.request.META.get('REMOTE_ADDR')
        )


class TenantAuditMixin(TenantQuerysetMixin, TenantObjectGuardMixin, AuditShieldMixin):
    """
    Full production mixin: Tenant scoping + Object guard + Audit logging + Delete guard.
    Use on all operational ViewSets.
    """
    pass
