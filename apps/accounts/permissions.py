"""AEC Cinemas – RBAC Permission Classes"""

from rest_framework.permissions import BasePermission


class IsMD(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'MD'


class IsMDOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['MD', 'ADMIN']


class IsStaffOrAbove(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['MD', 'ADMIN', 'STAFF']


class HasModule:
    """
    Returns a permission class that checks if a module is enabled for the tenant.
    Usage: permission_classes = [HasModule('CAFE')]
    """
    def __new__(cls, module_key):
        class HasModulePermission(BasePermission):
            def has_permission(self, request, view):
                if not request.user.is_authenticated:
                    return False
                active = getattr(request, 'active_modules', set())
                return module_key in active
        return HasModulePermission
