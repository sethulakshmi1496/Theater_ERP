from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.integrations.views import DistrictDCRReportViewSet, IntegrationConnectorViewSet

router = DefaultRouter()
router.register('dcr', DistrictDCRReportViewSet, basename='dcr-report')
router.register('connectors', IntegrationConnectorViewSet, basename='connector')

urlpatterns = [
    path('', include(router.urls)),
]

