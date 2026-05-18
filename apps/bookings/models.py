"""AEC Cinemas – Booking Models (ACID-safe)"""

from django.db import models
from django.conf import settings
import uuid


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        CHECKED_IN = 'CHECKED_IN', 'Checked In'
        CANCELLED = 'CANCELLED', 'Cancelled'
        REFUNDED = 'REFUNDED', 'Refunded'

    class Source(models.TextChoices):
        APP = 'APP', 'App / Web'
        COUNTER = 'COUNTER', 'Counter POS'
        BMS = 'BMS', 'BookMyShow'

    booking_ref = models.CharField(max_length=20, unique=True, editable=False)
    show = models.ForeignKey('screens.Show', on_delete=models.PROTECT, related_name='bookings')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    customer_name = models.CharField(max_length=150, blank=True)
    customer_phone = models.CharField(max_length=15, blank=True)
    customer_email = models.EmailField(blank=True)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.APP)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    convenience_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    bms_booking_id = models.CharField(max_length=100, blank=True)  # For BMS sync
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        app_label = 'bookings'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.booking_ref:
            self.booking_ref = f"AEC{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.booking_ref} – {self.show}"


class BookedSeat(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='booked_seats')
    seat = models.ForeignKey('screens.Seat', on_delete=models.PROTECT)
    price_paid = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        app_label = 'bookings'
        unique_together = ('booking', 'seat')

    def __str__(self):
        return f"{self.booking.booking_ref} – Seat {self.seat}"


class ShowSeatStatus(models.Model):
    """Track seat availability per show (for SVG map)."""
    class SeatState(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Available'
        BOOKED = 'BOOKED', 'Booked'
        BLOCKED = 'BLOCKED', 'Blocked'
        RESERVED = 'RESERVED', 'Reserved (BMS)'

    show = models.ForeignKey('screens.Show', on_delete=models.CASCADE, related_name='seat_statuses')
    seat = models.ForeignKey('screens.Seat', on_delete=models.CASCADE)
    state = models.CharField(max_length=15, choices=SeatState.choices, default=SeatState.AVAILABLE)

    class Meta:
        app_label = 'bookings'
        unique_together = ('show', 'seat')

    def __str__(self):
        return f"{self.show} – {self.seat} [{self.state}]"


class BMSSyncLog(models.Model):
    class SyncStatus(models.TextChoices):
        SUCCESS = 'SUCCESS', 'Success'
        FAILED = 'FAILED', 'Failed'
        PARTIAL = 'PARTIAL', 'Partial'

    sync_timestamp = models.DateTimeField(auto_now_add=True)
    records_fetched = models.PositiveIntegerField(default=0)
    records_created = models.PositiveIntegerField(default=0)
    records_updated = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=10, choices=SyncStatus.choices, default=SyncStatus.SUCCESS)
    error_message = models.TextField(blank=True)
    triggered_by = models.CharField(max_length=50, default='CELERY')

    class Meta:
        app_label = 'bookings'
        ordering = ['-sync_timestamp']

    def __str__(self):
        return f"BMS Sync {self.sync_timestamp.strftime('%Y-%m-%d %H:%M')} – {self.status}"


class BookingCorrection(models.Model):
    class CorrectionType(models.TextChoices):
        REFUND         = 'REFUND',         'Refund'
        CANCELLATION   = 'CANCELLATION',   'Cancellation'
        COMPLIMENTARY  = 'COMPLIMENTARY',  'Complimentary Pass'
        ADJUSTMENT     = 'ADJUSTMENT',     'Adjustment'

    class Status(models.TextChoices):
        PENDING  = 'PENDING',  'Pending Approval'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    class RefundMode(models.TextChoices):
        CASH        = 'CASH',        'Cash'
        CARD        = 'CARD',        'Credit/Debit Card'
        UPI         = 'UPI',         'UPI'
        WALLET      = 'WALLET',      'Digital Wallet'
        NETBANKING  = 'NETBANKING',  'Net Banking'
        NONE        = 'NONE',        'None / Not Applicable'

    tenant          = models.ForeignKey('tenants.Tenant', on_delete=models.PROTECT, related_name='booking_corrections')
    booking         = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='corrections')
    correction_type = models.CharField(max_length=20, choices=CorrectionType.choices)
    original_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reason          = models.TextField()
    status          = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    approved_by     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_corrections')
    audit_ref       = models.CharField(max_length=50, blank=True, unique=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    # Type-specific attributes
    # ── Refund ──
    refund_amount   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    refund_mode     = models.CharField(max_length=20, choices=RefundMode.choices, default=RefundMode.NONE)

    # ── Adjustment ──
    before_value    = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    after_value     = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    adjustment_logic = models.TextField(blank=True, help_text='Explanation of manual adjustment logic')

    class Meta:
        app_label = 'bookings'
        ordering  = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.audit_ref:
            from django.utils import timezone
            ts = timezone.now().strftime('%Y%m%d%H%M%S')
            prefix = {
                self.CorrectionType.REFUND: 'RF',
                self.CorrectionType.CANCELLATION: 'CN',
                self.CorrectionType.COMPLIMENTARY: 'CP',
                self.CorrectionType.ADJUSTMENT: 'AD',
            }.get(self.correction_type, 'BC')
            self.audit_ref = f"{prefix}-{ts}"
        if not self.original_amount and self.booking:
            self.original_amount = self.booking.total_amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.audit_ref} | {self.correction_type} | {self.status}"

