from django.db import migrations

def seed_modules(apps, schema_editor):
    Tenant = apps.get_model('tenants', 'Tenant')
    TenantModule = apps.get_model('tenants', 'TenantModule')

    try:
        aec = Tenant.objects.get(id=1)
        modules = [
            'DISTRICT_BRIDGE',
            'PAYROLL_MIRROR',
            'ADVERTISING',
            'CAFE',
            'FINANCE',
            'AUDIT',
            'SCREEN_BUILDER',
        ]
        for mod in modules:
            TenantModule.objects.get_or_create(tenant=aec, module_key=mod, defaults={'is_enabled': True})
    except Tenant.DoesNotExist:
        pass

def reverse_seed(apps, schema_editor):
    TenantModule = apps.get_model('tenants', 'TenantModule')
    TenantModule.objects.filter(tenant_id=1).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0003_backfill_aec_tenant'),
    ]

    operations = [
        migrations.RunPython(seed_modules, reverse_seed),
    ]
