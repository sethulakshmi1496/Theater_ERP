from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookingViewSet, BookingCorrectionViewSet

router = DefaultRouter()
router.register('corrections', BookingCorrectionViewSet, basename='booking-correction')
router.register('', BookingViewSet, basename='booking')

urlpatterns = [path('', include(router.urls))]

