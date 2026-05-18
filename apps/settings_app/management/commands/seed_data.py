"""AEC Cinemas – Database seeder with initial data"""

from django.core.management.base import BaseCommand
from apps.settings_app.models import GlobalSetting
from apps.screens.models import Screen, SeatCategory, Seat
from apps.accounts.models import User


class Command(BaseCommand):
    help = 'Seed initial AEC Cinemas data'

    def handle(self, *args, **options):
        self.seed_settings()
        self.seed_screens()
        self.seed_users()
        self.stdout.write(self.style.SUCCESS('✅ Database seeded successfully!'))

    def seed_settings(self):
        settings = [
            ('ELEC_RATE', '10.64', 'Electricity charge per unit (₹)'),
            ('UNIT_MULTIPLIER', '40', 'Unit conversion multiplier for electricity readings'),
            ('LAMP_MAX_HOURS', '3000', 'Maximum lamp life in hours'),
            ('LAMP_ALERT_THRESHOLD', '100', 'Hours remaining to trigger lamp alert'),
            ('UNITS_PER_SHOW_AVERAGE', '3.84', 'Expected average units per show for efficiency check'),
            ('BMS_SYNC_INTERVAL_MINUTES', '30', 'How often to sync BookMyShow bookings'),
        ]
        for key, value, desc in settings:
            obj, created = GlobalSetting.objects.get_or_create(key=key, defaults={'value': value, 'description': desc})
            if created:
                self.stdout.write(f'  Created setting: {key}={value}')

    def seed_screens(self):
        screens_data = [
            {'name': 'Screen 1', 'total_seats': 200, 'lamp_balance': 3000},
            {'name': 'Screen 2', 'total_seats': 150, 'lamp_balance': 3000},
        ]
        for s_data in screens_data:
            screen, created = Screen.objects.get_or_create(
                name=s_data['name'],
                defaults={'total_seats': s_data['total_seats'], 'lamp_balance': s_data['lamp_balance']}
            )
            if created:
                self.stdout.write(f'  Created screen: {screen.name}')
                # Seat categories
                cats = [
                    ('Balcony', 250, '#F59E0B'),
                    ('Upper Class', 180, '#8B5CF6'),
                    ('Lower Class', 120, '#10B981'),
                ]
                for cat_name, price, color in cats:
                    SeatCategory.objects.create(
                        screen=screen, name=cat_name, price=price, color_code=color
                    )
                # Generate seats (rows A-J, 20 seats each for Screen 1)
                cat_list = list(screen.categories.all())
                rows = [chr(i) for i in range(ord('A'), ord('A') + 10)]
                for i, row in enumerate(rows):
                    cat = cat_list[0] if i < 3 else (cat_list[1] if i < 7 else cat_list[2])
                    seats_per_row = 20 if screen.name == 'Screen 1' else 15
                    for num in range(1, seats_per_row + 1):
                        Seat.objects.create(screen=screen, row=row, number=num, category=cat)
                # Update total_seats
                screen.total_seats = screen.seats.count()
                screen.save()
                self.stdout.write(f'    Created {screen.total_seats} seats for {screen.name}')

    def seed_users(self):
        users = [
            ('md@aeccinemas.com', 'AEC@md2026', 'Managing Director', 'MD'),
            ('admin@aeccinemas.com', 'AEC@admin2026', 'Admin Accountant', 'ADMIN'),
            ('staff@aeccinemas.com', 'AEC@staff2026', 'Front Desk Staff', 'STAFF'),
        ]
        for email, password, name, role in users:
            if not User.objects.filter(email=email).exists():
                User.objects.create_user(email=email, password=password, full_name=name, role=role)
                self.stdout.write(f'  Created user: {email} [{role}]')
