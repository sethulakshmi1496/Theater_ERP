from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ParkingZoneViewSet, ParkingSlotEntryViewSet

router = DefaultRouter()
router.register('zones', ParkingZoneViewSet, basename='parking-zone')
router.register('entries', ParkingSlotEntryViewSet, basename='parking-entry')

urlpatterns = [path('', include(router.urls))]
