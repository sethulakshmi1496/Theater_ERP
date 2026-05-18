"""
Data Migration: Backfill tenant_id = 1 (AEC Cinemas) on ALL existing rows
across every business model that received a tenant FK.

Strategy:
- Runs a single UPDATE per table using F-less SQL for safety.
- All updates are idempotent: only rows where tenant_id IS NULL are changed.
- Safe to re-run; will not overwrite rows already assigned to a tenant.

Rollback: Sets tenant_id back to NULL for AEC rows. This effectively
          reverts the backfill without touching the schema.
"""

from django.db import migrations


MODELS_TO_BACKFILL = [
    # (app_label, model_name)
    ('accounts', 'User'),
    ('screens', 'Screen'),
    ('screens', 'Movie'),
    ('operations', 'ElectricityReading'),
    ('operations', 'GeneratorLog'),
    ('finance', 'FilmAdvance'),
    ('finance', 'DistributorShare'),
    ('revenue', 'CanteenSale'),
    ('revenue', 'AdvertisingSlot'),
    ('revenue', 'CafeExpense'),
    ('audit', 'DeletedLog'),
]


def backfill_aec_tenant(apps, schema_editor):
    Tenant = apps.get_model('tenants', 'Tenant')

    try:
        aec = Tenant.objects.get(slug='aec-cinemas')
    except Tenant.DoesNotExist:
        print("\n  ✗ AEC tenant not found. Run 0002_seed_aec_tenant first.")
        return

    total_updated = 0

    for app_label, model_name in MODELS_TO_BACKFILL:
        try:
            Model = apps.get_model(app_label, model_name)
            # Only update rows that have no tenant yet
            count = Model.objects.filter(tenant__isnull=True).update(tenant=aec)
            total_updated += count
            if count > 0:
                print(f"\n  ✓ {app_label}.{model_name}: {count} rows → AEC tenant")
        except Exception as e:
            print(f"\n  ✗ {app_label}.{model_name}: {e}")

    print(f"\n  ✓ Backfill complete. {total_updated} total rows assigned to AEC Cinemas.")


def reverse_backfill(apps, schema_editor):
    """Rollback: Null out tenant_id for all AEC rows."""
    Tenant = apps.get_model('tenants', 'Tenant')

    try:
        aec = Tenant.objects.get(slug='aec-cinemas')
    except Tenant.DoesNotExist:
        return

    for app_label, model_name in MODELS_TO_BACKFILL:
        try:
            Model = apps.get_model(app_label, model_name)
            Model.objects.filter(tenant=aec).update(tenant=None)
        except Exception:
            pass


class Migration(migrations.Migration):

    dependencies = [
        # All FK-adding migrations must be complete before we fill them
        ('tenants', '0002_seed_aec_tenant'),
        ('accounts', '0002_add_tenant_fk'),
        ('screens', '0003_add_tenant_fk'),
        ('operations', '0003_add_tenant_fk'),
        ('finance', '0002_add_tenant_fk'),
        ('revenue', '0003_add_tenant_fk'),
        ('audit', '0002_add_tenant_fk'),
    ]

    operations = [
        migrations.RunPython(backfill_aec_tenant, reverse_backfill),
    ]
