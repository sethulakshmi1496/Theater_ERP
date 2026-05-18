"""AEC Cinemas – Root URL Configuration"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenBlacklistView,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # Auth
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/logout/', TokenBlacklistView.as_view(), name='token_blacklist'),

    # API Modules
    path('api/accounts/', include('apps.accounts.urls')),
    path('api/screens/', include('apps.screens.urls')),
    path('api/bookings/', include('apps.bookings.urls')),
    path('api/revenue/', include('apps.revenue.urls')),
    path('api/operations/', include('apps.operations.urls')),
    path('api/finance/', include('apps.finance.urls')),
    path('api/payroll/', include('apps.payroll.urls')),
    path('api/settings/', include('apps.settings_app.urls')),
    path('api/reports/', include('apps.reports.urls')),
    path('api/audit/', include('apps.audit.urls')),     # Audit Shield
    path('api/expenses/', include('apps.expenses.urls')),
    path('api/integrations/', include('apps.integrations.urls')),
    path('api/parking/', include('apps.parking.urls')),
    path('api/alerts/', include('apps.operations.alerts_urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
