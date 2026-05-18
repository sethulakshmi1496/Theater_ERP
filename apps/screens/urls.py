from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ScreenViewSet, MovieViewSet, ShowViewSet, SeatCategoryViewSet, ShowScheduleViewSet

router = DefaultRouter()
router.register('screens', ScreenViewSet, basename='screen')
router.register('categories', SeatCategoryViewSet, basename='category')
router.register('movies', MovieViewSet, basename='movie')
router.register('shows', ShowViewSet, basename='show')
router.register('schedules', ShowScheduleViewSet, basename='schedule')

urlpatterns = [path('', include(router.urls))]

