import os
import django
import random
from datetime import date, timedelta, time
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aec_cinemas.settings')
django.setup()

from apps.screens.models import Screen, Movie, Show, Seat
from apps.bookings.models import Booking, BookedSeat, ShowSeatStatus
from apps.revenue.models import CanteenSale, AdvertisingSlot
from apps.operations.models import LampLog, LampInventory

def seed():
    today = date.today()
    print(f"Seeding test data for {today}...")

    # Screens
    screen1 = Screen.objects.filter(name__icontains="Screen 1").first()
    screen2 = Screen.objects.filter(name__icontains="Screen 2").first()
    if not screen1 or not screen2:
        print("Screens not found. Did you run standard seed?")
        return

    # Movies
    m1, _ = Movie.objects.update_or_create(
        title="Avatar: The Way of Water",
        defaults={'language': 'English', 'genre': 'Sci-Fi', 'duration_minutes': 192, 'certificate': 'U/A', 'release_date': today}
    )
    m2, _ = Movie.objects.update_or_create(
        title="KGF: Chapter 2",
        defaults={'language': 'Kannada', 'genre': 'Action', 'duration_minutes': 168, 'certificate': 'A', 'release_date': today}
    )

    # Shows
    shows_data = [
        (screen1, m1, time(10, 0), time(13, 15), 150),
        (screen1, m2, time(14, 0), time(17, 0), 200),
        (screen2, m2, time(11, 0), time(14, 0), 180),
        (screen2, m1, time(15, 0), time(18, 15), 150),
    ]

    created_shows = []
    for screen, movie, start, end, price in shows_data:
        s, _ = Show.objects.update_or_create(
            screen=screen, movie=movie, show_date=today, start_time=start,
            defaults={'end_time': end, 'base_price': price, 'status': 'SCHEDULED'}
        )
        created_shows.append(s)

    # Bookings and Seats
    sources = ['APP', 'COUNTER', 'BMS']
    for show in created_shows:
        seats = list(show.screen.seats.all())
        random.shuffle(seats)
        book_count = random.randint(10, 50)
        seats_to_book = seats[:book_count]
        
        for i, seat in enumerate(seats_to_book):
            source = random.choice(sources)
            # Create a booking
            b = Booking.objects.create(
                show=show,
                customer_name=f"Test User {i}",
                source=source,
                status='CONFIRMED',
                total_amount=seat.category.price if seat.category else 150
            )
            # Book seat
            BookedSeat.objects.create(
                booking=b,
                seat=seat,
                price_paid=b.total_amount
            )
            # Update ShowSeatStatus
            ShowSeatStatus.objects.update_or_create(
                show=show, seat=seat,
                defaults={'state': 'BOOKED'}
            )

    # Advertising
    for show in created_shows[:2]:
        AdvertisingSlot.objects.create(
            show=show,
            slot_type='PRE_SHOW',
            advertiser_name="Local Jewelers",
            duration_seconds=30,
            amount=5000
        )
        AdvertisingSlot.objects.create(
            show=show,
            slot_type='INTERVAL',
            advertiser_name="Real Estate Co.",
            duration_seconds=15,
            amount=3000
        )

    # Cafe Sales
    cafe_items = [
        ("Popcorn Large", 250),
        ("Coke Medium", 120),
        ("Nachos with Cheese", 180),
        ("Coffee", 80),
        ("French Fries", 150)
    ]
    for name, price in cafe_items:
        qty = random.randint(5, 30)
        CanteenSale.objects.create(
            date=today,
            item_name=name,
            quantity=qty,
            unit_price=price,
            total=qty * price
        )

    # Lamp Log
    for screen in [screen1, screen2]:
        LampLog.objects.update_or_create(
            screen=screen,
            date=today,
            defaults={
                'opening_hours': 100,
                'closing_hours': 108,
                'working_hours': 8
            }
        )

    print("Test data seeded successfully!")

if __name__ == "__main__":
    seed()
