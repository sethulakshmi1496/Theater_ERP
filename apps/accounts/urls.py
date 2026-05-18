from django.urls import path
from .views import MeView, UserListCreateView, UserDetailView

urlpatterns = [
    path('me/', MeView.as_view(), name='accounts-me'),
    path('users/', UserListCreateView.as_view(), name='accounts-users'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='accounts-user-detail'),
]
