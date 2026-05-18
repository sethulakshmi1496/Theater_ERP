from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FilmAdvanceViewSet, 
    DistributorShareViewSet,
    DistributorViewSet,
    FilmContractViewSet,
    SettlementViewSet,
    DistributorStatementViewSet,
    FinanceDashboardViewSet
)

router = DefaultRouter()
router.register('advances', FilmAdvanceViewSet, basename='film-advance')
router.register('shares', DistributorShareViewSet, basename='distributor-share')
router.register('distributors', DistributorViewSet, basename='distributor')
router.register('contracts', FilmContractViewSet, basename='film-contract')
router.register('settlements', SettlementViewSet, basename='settlement')
router.register('statements', DistributorStatementViewSet, basename='statement')
router.register('dashboard', FinanceDashboardViewSet, basename='finance-dashboard')

urlpatterns = [path('', include(router.urls))]
