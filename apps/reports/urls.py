from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DailyPLView, MonthlyPLView, AlertsView,
    ExportDailyCSVView, ExportMonthlyCSVView,
    PLCompareView, PLDrillDownView, PLVarianceDriversView,
    ManagementSnapshotViewSet
)

router = DefaultRouter()
router.register(r'pl/snapshots', ManagementSnapshotViewSet, basename='pl-snapshots')
from .views import AIInsightReportViewSet, AIActionItemViewSet
router.register(r'ai/reports', AIInsightReportViewSet, basename='ai-reports')
router.register(r'ai/actions', AIActionItemViewSet, basename='ai-actions')

urlpatterns = [
    path('', include(router.urls)),
    path('pl/daily/', DailyPLView.as_view(), name='report-daily-pl'),
    path('pl/monthly/', MonthlyPLView.as_view(), name='report-monthly-pl'),
    path('pl/compare/', PLCompareView.as_view(), name='report-compare-pl'),
    path('pl/drill-down/', PLDrillDownView.as_view(), name='report-drill-down-pl'),
    path('pl/variance-drivers/', PLVarianceDriversView.as_view(), name='report-variance-drivers-pl'),
    
    path('alerts/', AlertsView.as_view(), name='report-alerts'),
    path('export/daily/', ExportDailyCSVView.as_view(), name='export-daily-csv'),
    path('export/monthly/', ExportMonthlyCSVView.as_view(), name='export-monthly-csv'),
]
