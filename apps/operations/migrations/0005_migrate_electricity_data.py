import datetime
from django.db import migrations


def migrate_electricity_data(apps, schema_editor):
    Tenant = apps.get_model('tenants', 'Tenant')
    UtilityMeter = apps.get_model('operations', 'UtilityMeter')
    UtilityConfig = apps.get_model('operations', 'UtilityConfig')
    ElectricityReading = apps.get_model('operations', 'ElectricityReading')
    UtilityReading = apps.get_model('operations', 'UtilityReading')

    # Find the AEC tenant
    try:
        aec = Tenant.objects.get(slug='aec-cinemas')
    except Tenant.DoesNotExist:
        print("\nAEC tenant not found. Skipping data migration.")
        return

    # Create Main EB Meter for AEC
    meter, created = UtilityMeter.objects.get_or_create(
        tenant=aec,
        name="Main EB Meter",
        meter_type="ELECTRICITY",
        unit_label="kWh",
        is_active=True
    )

    # Create Config: Multiplier 40, Rate 10.64
    UtilityConfig.objects.get_or_create(
        meter=meter,
        multiplier=40.0000,
        rate_per_unit=10.6400,
        effective_from=datetime.date(2000, 1, 1)
    )

    # Migrate Readings
    readings = ElectricityReading.objects.all()
    created_count = 0
    for reading in readings:
        _, created = UtilityReading.objects.get_or_create(
            meter=meter,
            reading_date=reading.date,
            defaults={
                'initial_reading': reading.initial_reading,
                'final_reading': reading.final_reading,
                'consumption': reading.total_consumption,
                'billed_units': reading.unit_conversion,
                'total_cost': reading.elec_charges,
                'entered_by': reading.entered_by,
                'notes': reading.notes,
            }
        )
        if created:
            created_count += 1
            
    print(f"\nMigrated {created_count} electricity readings to UtilityReading.")


def reverse_migration(apps, schema_editor):
    UtilityMeter = apps.get_model('operations', 'UtilityMeter')
    UtilityMeter.objects.filter(name="Main EB Meter").delete()


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0004_utility_meter_models'),
        ('tenants', '0003_backfill_aec_tenant'),
    ]

    operations = [
        migrations.RunPython(migrate_electricity_data, reverse_migration)
    ]
