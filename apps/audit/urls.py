from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DeletedLogViewSet, ChangeLogViewSet, StaffSessionViewSet, AdminDeleteVerifyView, AuditShieldLogViewSet

router = DefaultRouter()
router.register('deleted-logs', DeletedLogViewSet, basename='deleted-log')
router.register('change-logs', ChangeLogViewSet, basename='change-log')
router.register('staff-sessions', StaffSessionViewSet, basename='staff-session')
router.register('delete-verify', AdminDeleteVerifyView, basename='delete-verify')
router.register('shield-logs', AuditShieldLogViewSet, basename='shield-log')

urlpatterns = [path('', include(router.urls))]

