"""
Data Migration: Insert AEC Cinemas as Tenant Zero.
This is a one-time safe data migration. It inserts the AEC tenant row
with id=1 and seeds default module flags for all current features.

Rollback: Deletes the AEC tenant row. Safe because tenant_id columns
          on business models are added in later migrations.
"""

from django.db import migrations

AEC_MODULES = [
    'OPERATIONS',
    'LAMP_REGISTRY',
    'SCREEN_BUILDER',
    'PRICING_ENGINE',
    'CAFE',
    'ADVERTISING',
    'FINANCE',
    'MD_DASHBOARD',
    'AUDIT',
    'BOOKINGS',
    'PAYROLL_MIRROR',
]


def insert_aec_tenant(apps, schema_editor):
    Tenant = apps.get_model('tenants', 'Tenant')
    TenantModule = apps.get_model('tenants', 'TenantModule')

    tenant = Tenant.objects.create(
        name='AEC Cinemas',
        slug='aec-cinemas',
        is_active=True,
        plan='pro',
        timezone='Asia/Kolkata',
        currency='INR',
        working_days_per_month=26,
    )

    for module_key in AEC_MODULES:
        TenantModule.objects.create(
            tenant=tenant,
            module_key=module_key,
            is_enabled=True,
        )

    print(f"\n  ✓ AEC Cinemas created as Tenant Zero (id={tenant.id})")
    print(f"  ✓ {len(AEC_MODULES)} modules enabled for AEC tenant")


def remove_aec_tenant(apps, schema_editor):
    """Rollback: remove the AEC tenant and its module records."""
    Tenant = apps.get_model('tenants', 'Tenant')
    Tenant.objects.filter(slug='aec-cinemas').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0001_tenant_foundation'),
    ]

    operations = [
        migrations.RunPython(insert_aec_tenant, remove_aec_tenant),
    ]
