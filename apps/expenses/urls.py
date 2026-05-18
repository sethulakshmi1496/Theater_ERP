from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ExpenseViewSet, ExpenseSubcategoryViewSet

router = DefaultRouter()
router.register(r'expenses', ExpenseViewSet, basename='expense')
router.register(r'subcategories', ExpenseSubcategoryViewSet, basename='expense-subcategory')

urlpatterns = [
    path('', include(router.urls)),
]
