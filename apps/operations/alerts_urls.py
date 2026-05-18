from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.operations.views import OperationalAlertViewSet

router = DefaultRouter()
router.register('', OperationalAlertViewSet, basename='top-level-alert')

urlpatterns = [
    path('', include(router.urls)),
]
