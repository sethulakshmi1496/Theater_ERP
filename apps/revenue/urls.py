from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CanteenItemViewSet, CanteenSaleViewSet, AdvertisingSlotViewSet, 
    CafeExpenseViewSet, CafeUnitViewSet, CafeInwardViewSet, 
    CafeWastageViewSet, CafeDashboardViewSet, CafeDailyConsumptionViewSet,
    CafeReorderAlertViewSet, AdvertiserViewSet, AdCampaignViewSet
)

router = DefaultRouter()
router.register('canteen/units', CafeUnitViewSet, basename='cafe-unit')
router.register('canteen/items', CanteenItemViewSet, basename='canteen-item')
router.register('canteen/inwards', CafeInwardViewSet, basename='cafe-inward')
router.register('canteen/wastage', CafeWastageViewSet, basename='cafe-wastage')
router.register('canteen/sales', CanteenSaleViewSet, basename='canteen-sale')
router.register('canteen/consumption', CafeDailyConsumptionViewSet, basename='cafe-consumption')
router.register('canteen/expenses', CafeExpenseViewSet, basename='cafe-expense')
router.register('canteen/reorder-alerts', CafeReorderAlertViewSet, basename='cafe-reorder-alert')
router.register('canteen/dashboard', CafeDashboardViewSet, basename='cafe-dashboard')
router.register('advertising', AdvertisingSlotViewSet, basename='advertising')
router.register('advertisers', AdvertiserViewSet, basename='advertiser')
router.register('ad-campaigns', AdCampaignViewSet, basename='ad-campaign')

urlpatterns = [path('', include(router.urls))]

