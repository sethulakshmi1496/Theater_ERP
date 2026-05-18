from django.db import migrations


def seed_cafe_units(apps, schema_editor):
    Tenant = apps.get_model('tenants', 'Tenant')
    CafeUnit = apps.get_model('revenue', 'CafeUnit')
    CanteenSale = apps.get_model('revenue', 'CanteenSale')
    CafeExpense = apps.get_model('revenue', 'CafeExpense')

    # Seed Main Counter for all existing tenants and backfill records
    for tenant in Tenant.objects.all():
        unit, created = CafeUnit.objects.get_or_create(
            tenant=tenant,
            name="Main Counter",
            defaults={'is_active': True}
        )
        # Update existing records
        CanteenSale.objects.filter(tenant=tenant, cafe_unit__isnull=True).update(cafe_unit=unit)
        CafeExpense.objects.filter(tenant=tenant, cafe_unit__isnull=True).update(cafe_unit=unit)

def reverse_seed(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('revenue', '0004_cafe_unit'),
    ]

    operations = [
        migrations.RunPython(seed_cafe_units, reverse_seed),
    ]
