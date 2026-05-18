"""
AEC Cinemas Platform – Tenant Middleware & Utilities

TenantMiddleware:
  Attaches request.tenant and request.active_modules to every authenticated
  request. Single-tenant mode (AEC-only) is transparent.

TenantQuerysetMixin:
  Attach to any DRF ViewSet to automatically scope querysets to the
  authenticated user's tenant. Zero AEC behavior change — all AEC users
  are already assigned to tenant_id=1.
"""

from apps.tenants.models import Tenant, TenantModule


class TenantMiddleware:
    """
    Injects tenant context into every authenticated request.
    Sets request.tenant and request.active_modules.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant = None
        request.active_modules = set()

        if hasattr(request, 'user') and request.user.is_authenticated:
            # Resolve from user.tenant FK directly — avoids circular dependency
            tenant = getattr(request.user, 'tenant', None)

            if tenant is None:
                # Safety fallback for legacy AEC users if FK not populated
                try:
                    tenant = Tenant.objects.get(slug='aec-cinemas')
                except Tenant.DoesNotExist:
                    pass

            if tenant:
                request.tenant = tenant
                request.active_modules = set(
                    TenantModule.objects.filter(
                        tenant=tenant,
                        is_enabled=True
                    ).values_list('module_key', flat=True)
                )

        return self.get_response(request)


class TenantQuerysetMixin:
    """
    Attach to a DRF ViewSet to automatically scope its queryset to
    the authenticated user's tenant.

    Usage:
        class ScreenViewSet(TenantQuerysetMixin, viewsets.ModelViewSet):
            queryset = Screen.objects.all()
            ...

    The mixin filters on queryset.filter(tenant=request.tenant).
    If the model has no tenant field, the mixin is a no-op (safe).
    """

    def get_queryset(self):
        qs = super().get_queryset()
        tenant = getattr(self.request, 'tenant', None)
        if tenant and hasattr(qs.model, 'tenant'):
            return qs.filter(tenant=tenant)
        return qs

    def perform_create(self, serializer):
        """Auto-stamp tenant on every new object created via the API."""
        tenant = getattr(self.request, 'tenant', None)
        if tenant and 'tenant' in [f.name for f in serializer.Meta.model._meta.get_fields()]:
            serializer.save(tenant=tenant)
        else:
            serializer.save()
