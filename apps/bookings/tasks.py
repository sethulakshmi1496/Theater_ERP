"""AEC Cinemas – Celery Tasks"""

from celery import shared_task


@shared_task
def sync_bms_bookings_task():
    """Placeholder for BookMyShow API sync. Replace with real API call."""
    from apps.bookings.services import BookingService
    # TODO: Call BMS API, parse response, pass to BookingService.sync_bms_bookings()
    bms_data = []  # Fetch from BMS API
    return BookingService.sync_bms_bookings(bms_data)
