"""AEC Cinemas – Booking Service Layer (ACID-safe)"""

from django.db import transaction
from django.utils import timezone
from .models import Booking, BookedSeat, ShowSeatStatus, BMSSyncLog
from apps.screens.models import Show, Seat


class BookingService:

    @staticmethod
    @transaction.atomic
    def create_booking(show_id, seat_ids, source='APP', user=None,
                       customer_name='', customer_phone='', customer_email=''):
        """
        ACID-safe booking with select_for_update to prevent race conditions.
        Raises ValueError on seat conflicts.
        """
        show = Show.objects.select_for_update().get(pk=show_id)

        # Lock the specific seat statuses for this show
        seat_statuses = ShowSeatStatus.objects.select_for_update().filter(
            show=show, seat_id__in=seat_ids
        )
        already_booked = seat_statuses.filter(state__in=['BOOKED', 'BLOCKED', 'RESERVED'])
        if already_booked.exists():
            conflict = [str(s.seat) for s in already_booked]
            raise ValueError(f"Seats already taken: {', '.join(conflict)}")

        # Fetch seats and compute total
        seats = Seat.objects.filter(pk__in=seat_ids, screen=show.screen, is_active=True)
        if seats.count() != len(seat_ids):
            raise ValueError("One or more seats are invalid or inactive.")

        total = sum(
            s.category.price if s.category else show.base_price for s in seats
        )

        # Create booking
        booking = Booking.objects.create(
            show=show,
            user=user,
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_email=customer_email,
            source=source,
            status=Booking.Status.CONFIRMED,
            total_amount=total,
        )

        # Create booked seats
        booked_seat_objs = []
        for seat in seats:
            price = seat.category.price if seat.category else show.base_price
            booked_seat_objs.append(BookedSeat(booking=booking, seat=seat, price_paid=price))
        BookedSeat.objects.bulk_create(booked_seat_objs)

        # Update seat statuses
        ShowSeatStatus.objects.filter(show=show, seat__in=seats).update(state='BOOKED')
        # Create for seats that had no status row yet
        existing_ids = seat_statuses.values_list('seat_id', flat=True)
        new_status_ids = [sid for sid in seat_ids if sid not in existing_ids]
        if new_status_ids:
            ShowSeatStatus.objects.bulk_create([
                ShowSeatStatus(show=show, seat_id=sid, state='BOOKED')
                for sid in new_status_ids
            ])

        return booking

    @staticmethod
    @transaction.atomic
    def cancel_booking(booking_id):
        booking = Booking.objects.select_for_update().get(pk=booking_id)
        if booking.status == Booking.Status.CANCELLED:
            raise ValueError("Booking already cancelled.")
        seat_ids = booking.booked_seats.values_list('seat_id', flat=True)
        ShowSeatStatus.objects.filter(
            show=booking.show, seat_id__in=seat_ids
        ).update(state='AVAILABLE')
        booking.status = Booking.Status.CANCELLED
        booking.cancelled_at = timezone.now()
        booking.save(update_fields=['status', 'cancelled_at'])
        return booking

    @staticmethod
    def sync_bms_bookings(bms_data: list):
        """Process BookMyShow synced booking records."""
        created = updated = 0
        for record in bms_data:
            obj, is_new = Booking.objects.update_or_create(
                bms_booking_id=record['bms_id'],
                defaults={
                    'show_id': record['show_id'],
                    'source': Booking.Source.BMS,
                    'status': Booking.Status.CONFIRMED,
                    'customer_name': record.get('customer_name', ''),
                    'customer_phone': record.get('customer_phone', ''),
                    'total_amount': record.get('amount', 0),
                }
            )
            if is_new:
                created += 1
            else:
                updated += 1
        BMSSyncLog.objects.create(
            records_fetched=len(bms_data),
            records_created=created,
            records_updated=updated,
            status=BMSSyncLog.SyncStatus.SUCCESS,
        )
        return {'created': created, 'updated': updated}
