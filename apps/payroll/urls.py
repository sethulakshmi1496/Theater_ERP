from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StaffViewSet, PayrollEntryViewSet, AttendanceMirrorViewSet, ShiftMirrorViewSet, HRSyncLogViewSet

router = DefaultRouter()
router.register('staff', StaffViewSet, basename='staff')
router.register('payroll-entries', PayrollEntryViewSet, basename='payroll-entry')
router.register('attendance-mirror', AttendanceMirrorViewSet, basename='attendance-mirror')
router.register('shift-mirror', ShiftMirrorViewSet, basename='shift-mirror')
router.register('sync-logs', HRSyncLogViewSet, basename='sync-log')

urlpatterns = [path('', include(router.urls))]

