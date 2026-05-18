from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TenantSettingViewSet, TenantProfileViewSet, TenantModuleViewSet,
    VendorViewSet, AlertRuleViewSet, SystemGovernanceViewSet
)

router = DefaultRouter()
router.register('profile', TenantProfileViewSet, basename='tenant-profile')
router.register('modules', TenantModuleViewSet, basename='tenant-modules')
router.register('keys', TenantSettingViewSet, basename='tenant-setting')
router.register('vendors', VendorViewSet, basename='vendor')
router.register('alert-rules', AlertRuleViewSet, basename='alert-rule')
router.register('governance', SystemGovernanceViewSet, basename='governance')

urlpatterns = [path('', include(router.urls))]


