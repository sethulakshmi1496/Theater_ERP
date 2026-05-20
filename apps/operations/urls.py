from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ElectricityReadingViewSet,
    UtilityMeterViewSet, UtilityConfigViewSet, UtilityReadingViewSet,
    GeneratorLogViewSet, LampLogViewSet, LampInventoryViewSet,
    AssetCategoryViewSet, AssetTemplateViewSet, TenantAssetViewSet, AssetLogViewSet,
    FaultTicketViewSet, PMScheduleViewSet, WorkOrderViewSet,
    AMCContractViewSet, MaintenanceDashboardViewSet, ServiceHistoryViewSet,
    WaterLogViewSet, OperationalAlertViewSet
)

router = DefaultRouter()
router.register('electricity-readings', ElectricityReadingViewSet, basename='electricity-reading')
router.register('utility-meters', UtilityMeterViewSet, basename='utility-meter')
router.register('utility-configs', UtilityConfigViewSet, basename='utility-config')
router.register('utility-readings', UtilityReadingViewSet, basename='utility-reading')
router.register('water-logs', WaterLogViewSet, basename='water-log')
router.register('generator', GeneratorLogViewSet, basename='generator')
router.register('lamps', LampLogViewSet, basename='lamps')
router.register('lamp-inventory', LampInventoryViewSet, basename='lamp-inventory')
router.register('asset-categories', AssetCategoryViewSet, basename='asset-category')
router.register('asset-templates', AssetTemplateViewSet, basename='asset-template')
router.register('tenant-assets', TenantAssetViewSet, basename='tenant-asset')
router.register('asset-logs', AssetLogViewSet, basename='asset-log')
# Maintenance Desk
router.register('maintenance/fault-tickets', FaultTicketViewSet, basename='fault-ticket')
router.register('maintenance/pm-schedules', PMScheduleViewSet, basename='pm-schedule')
router.register('maintenance/work-orders', WorkOrderViewSet, basename='work-order')
router.register('maintenance/amc-contracts', AMCContractViewSet, basename='amc-contract')
router.register('maintenance/service-history', ServiceHistoryViewSet, basename='service-history')
router.register('maintenance/dashboard', MaintenanceDashboardViewSet, basename='maintenance-dashboard')
router.register('alerts', OperationalAlertViewSet, basename='operational-alert')

urlpatterns = [path('', include(router.urls))]


