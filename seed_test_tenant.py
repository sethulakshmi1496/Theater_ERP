import os
import django
import sys
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aec_cinemas.settings')
django.setup()

from apps.tenants.models import Tenant, TenantModule
from apps.accounts.models import User
from apps.screens.models import Screen, SeatCategory
from apps.operations.models import UtilityMeter, UtilityConfig
from apps.settings_app.models import TenantSetting

def run():
    print("Creating Test Tenant...")
    tenant, created = Tenant.objects.get_or_create(
        slug='test-cinemas',
        defaults={
            'id': 2,
            'name': 'Test Cinemas',
            'plan': 'pro',
            'timezone': 'Asia/Kolkata',
            'currency': 'INR',
            'working_days_per_month': 26
        }
    )
    
    if created:
        print(f"Created Tenant: {tenant.name}")
    else:
        print(f"Tenant {tenant.name} already exists.")

    print("Creating Admin User...")
    user, u_created = User.objects.get_or_create(
        email='admin@testcinemas.com',
        defaults={
            'full_name': 'Test Admin',
            'role': 'MD',
            'tenant': tenant,
        }
    )
    if u_created:
        user.set_password('testpass123')
        user.save()
        print("Created User: admin@testcinemas.com / testpass123")

    print("Configuring Modules...")
    modules = ['CAFE', 'FINANCE']
    for m in modules:
        TenantModule.objects.get_or_create(tenant=tenant, module_key=m, defaults={'is_enabled': True})

    print("Configuring Settings...")
    TenantSetting.objects.get_or_create(tenant=tenant, key='ELEC_RATE', defaults={'value': '15.00'})
    TenantSetting.objects.get_or_create(tenant=tenant, key='UNIT_MULTIPLIER', defaults={'value': '1.0'})

    print("Creating Screen and Seat Categories...")
    screen, s_created = Screen.objects.get_or_create(
        tenant=tenant,
        name='Test Screen 1',
        defaults={
            'screen_type': '2D',
            'lamp_max_hours': 2000,
            'lamp_balance': 2000,
            'total_seats': 100
        }
    )

    if s_created:
        SeatCategory.objects.create(tenant=tenant, screen=screen, name='VIP', price=Decimal('250.00'), color_code='#FFD700', seat_count=20)
        SeatCategory.objects.create(tenant=tenant, screen=screen, name='Standard', price=Decimal('150.00'), color_code='#4F46E5', seat_count=80)

    print("Creating Utility Meters and Tariffs...")
    meter, m_created = UtilityMeter.objects.get_or_create(
        tenant=tenant,
        name='Main Test Grid',
        meter_type='ELECTRICITY',
        defaults={'unit_label': 'kWh'}
    )

    if m_created:
        UtilityConfig.objects.create(
            meter=meter,
            multiplier=Decimal('1.0000'),
            rate_per_unit=Decimal('15.0000'),
            effective_from='2024-01-01'
        )

    print("Done seeding second tenant.")

if __name__ == '__main__':
    run()
