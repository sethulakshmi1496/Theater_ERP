import os
import django
from datetime import datetime
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aec_cinemas.settings')
django.setup()

from apps.operations.models import GeneratorLog, ElectricityReading

generator_data = [
    ("04.04.26", 352.6, 0, 140),
    ("05.04.26", 352.6, 0, 0),
    ("06.04.26", 352.7, 0.1, 0),
    ("07.04.26", 356, 3.3, 0),
    ("08.04.26", 356.1, 0.1, 0),
    ("09.04.26", 356.1, 0, 0),
    ("10.04.26", 356.1, 0, 0),
    ("11.04.26", 356.1, 0, 0),
    ("12.04.26", 356.1, 0, 0),
    ("13.04.26", 356.1, 0, 0),
    ("14.04.26", 356.2, 0.1, 0),
    ("15.04.26", 356.2, 0.2, 0),
    ("16.04.26", 358.3, 2.1, 0),
    ("17.04.26", 359, 0.7, 0),
    ("18.04.26", 359, 0, 100),
    ("19.04.26", 359.2, 0.2, 0),
    ("20.04.26", 359.4, 0.2, 0),
    ("21.04.26", 359.5, 0.1, 0),
    ("22.04.26", 360.4, 0.9, 0),
    ("23.04.26", 360.7, 0.3, 0),
    ("24.04.26", 361, 0.3, 0),
    ("25.04.26", 361.5, 0.5, 0),
    ("26.04.26", 362.9, 1.4, 0),
    ("27.04.26", 363, 0.1, 0),
    ("28.04.26", 363.1, 0.1, 0)
]

print("Seeding Generator Data...")
for date_str, hours, cons, diesel in generator_data:
    dt = datetime.strptime(date_str, "%d.%m.%y").date()
    GeneratorLog.objects.update_or_create(
        date=dt,
        defaults={
            'hours_run': Decimal(str(hours)),
            'consumption': Decimal(str(cons)),
            'diesel_added': Decimal(str(diesel)),
            'diesel_rate': Decimal('95.00')  # Default rate, adjust if needed
        }
    )

electricity_data = [
    # date, s1, s2, shows, tickets_sold, initial, final
    ("01.04.26", 3, 3, 6, 0, 21910.2, 21930.3),
    ("02.04.26", 1, 1, 2, 0, 21930.3, 21940.2),
    ("03.04.26", 4, 3, 7, 0, 21940.2, 21959.6),
    ("04.04.26", 3, 3, 6, 0, 21959.6, 21994.5),
    ("05.04.26", 5, 4, 9, 0, 21994.5, 22034.3),
    ("06.04.26", 4, 4, 8, 0, 22034.3, 22074.2),
    ("07.04.26", 3, 3, 6, 0, 22074.2, 22100.8),
    ("08.04.26", 4, 3, 7, 0, 22100.8, 22134.8),
    ("09.04.26", 3, 3, 6, 0, 22134.8, 22167.3),
    ("10.04.26", 4, 3, 7, 0, 22167.3, 22204.8),
    ("11.04.26", 4, 4, 8, 0, 22204.8, 22243),
    ("12.04.26", 5, 4, 9, 0, 22243, 22281.9),
    ("13.04.26", 4, 4, 8, 0, 22281.9, 22308.9),
    ("14.04.26", 4, 3, 7, 0, 22308.9, 22335.3),
    ("15.04.26", 5, 5, 10, 0, 22335.3, 22370.2),
    ("16.04.26", 5, 4, 9, 0, 22370.2, 22396.1),
    ("17.04.26", 4, 5, 9, 410, 22396.1, 22425.8),
    ("18.04.26", 5, 4, 9, 428, 22425.8, 22453.7),
    ("19.04.26", 6, 4, 10, 607, 22453.7, 22479.3),
    ("20.04.26", 4, 3, 7, 38, 22479.3, 22502.2),
    ("21.04.26", 3, 3, 6, 230, 22502.2, 22522.1),
    ("22.04.26", 3, 5, 8, 277, 22522.1, 22543.3),
    ("23.04.26", 3, 4, 7, 118, 22543.3, 22564.9),
    ("24.04.26", 4, 5, 9, 368, 22564.9, 22589.9),
    ("25.04.26", 5, 4, 9, 440, 22589.9, 22617.1),
    ("26.04.26", 5, 3, 8, 462, 22617.1, 22643.8),
    ("27.04.26", 3, 3, 6, 221, 22643.8, 22666),
    ("28.04.26", 2, 1, 3, 115, 22666, 22679.6)
]

print("Seeding Electricity Data...")
for date_str, s1, s2, shows, tickets, initial, final in electricity_data:
    dt = datetime.strptime(date_str, "%d.%m.%y").date()
    # The models calculates the consumption and stats in save()
    ElectricityReading.objects.update_or_create(
        date=dt,
        defaults={
            'screen_1_shows': s1,
            'screen_2_shows': s2,
            'tickets_sold': tickets,
            'initial_reading': Decimal(str(initial)),
            'final_reading': Decimal(str(final))
        }
    )

print("Done Seeding.")
