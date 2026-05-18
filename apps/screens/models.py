"""AEC Cinemas – Screens, Shows, and Seat Models"""

from django.db import models
from django.utils import timezone
from decimal import Decimal


class Screen(models.Model):
    class ScreenType(models.TextChoices):
        TWO_D = '2D', '2D'
        THREE_D = '3D', '3D'
        IMAX = 'IMAX', 'IMAX'
        FOUR_DX = '4DX', '4DX'
        OTHER = 'OTHER', 'Other'

    # ── Tenant Foundation ──────────────────────────────────────────────────
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.PROTECT,
        null=True, blank=True, related_name='screens'
    )
    # ── End Tenant Foundation ──────────────────────────────────────────────
    name = models.CharField(max_length=50)
    screen_type = models.CharField(max_length=10, choices=ScreenType.choices, default=ScreenType.TWO_D)
    total_seats = models.PositiveIntegerField(default=0)  # cached — updated by recalculate_total_seats()
    is_active = models.BooleanField(default=True)

    # ── Legacy lamp fields — deprecated; asset tracking moved to TenantAsset ──
    lamp_balance = models.DecimalField(max_digits=8, decimal_places=2, default=3000)
    lamp_max_hours = models.DecimalField(max_digits=8, decimal_places=2, default=3000)
    lamp_alert_threshold = models.DecimalField(max_digits=8, decimal_places=2, default=100)
    # ── End legacy lamp fields ────────────────────────────────────────────

    class Meta:
        app_label = 'screens'

    def __str__(self):
        return self.name

    def recalculate_total_seats(self):
        """Recompute total_seats from active Seat rows and persist."""
        count = self.seats.filter(is_active=True).count()
        if count != self.total_seats:
            self.total_seats = count
            self.save(update_fields=['total_seats'])
        return count

    @property
    def sellable_seat_count(self):
        """Live count of sellable (active) seats — use this for occupancy math."""
        return self.seats.filter(is_active=True).count()

    # ── Legacy lamp helpers (kept for backward compat with LampLog) ────────
    @property
    def lamp_percentage(self):
        if self.lamp_max_hours == 0:
            return 0
        return float((self.lamp_balance / self.lamp_max_hours) * 100)

    @property
    def lamp_alert(self):
        if self.lamp_max_hours == 0:
            return False
        return self.lamp_balance <= (self.lamp_max_hours * Decimal('0.10'))


class SeatCategory(models.Model):
    # ── Tenant Foundation ──────────────────────────────────────────────────
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.PROTECT,
        null=True, blank=True, related_name='seat_categories'
    )
    # ── End Tenant Foundation ──────────────────────────────────────────────
    screen = models.ForeignKey(Screen, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    color_code = models.CharField(max_length=7, default='#4F46E5')
    seat_count = models.PositiveIntegerField(default=0)  # cached count for this category

    class Meta:
        app_label = 'screens'

    def __str__(self):
        return f"{self.screen.name} – {self.name} (₹{self.price})"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_price = None
        if not is_new:
            old_price = SeatCategory.objects.get(pk=self.pk).price

        super().save(*args, **kwargs)

        # Create a new PriceVersion if price changed
        if is_new or (old_price is not None and old_price != self.price):
            PriceVersion.objects.create(category=self, price=self.price)

        # Recalculate cached seat_count
        self.seat_count = self.seats.filter(is_active=True).count()
        SeatCategory.objects.filter(pk=self.pk).update(seat_count=self.seat_count)


class PriceVersion(models.Model):
    category = models.ForeignKey(SeatCategory, on_delete=models.CASCADE, related_name='price_versions')
    price = models.DecimalField(max_digits=8, decimal_places=2)
    start_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'screens'
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.category.name} @ ₹{self.price} from {self.start_date.strftime('%Y-%m-%d %H:%M')}"


class Seat(models.Model):
    screen = models.ForeignKey(Screen, on_delete=models.CASCADE, related_name='seats')
    category = models.ForeignKey(SeatCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='seats')
    row = models.CharField(max_length=5)   # A, B, C …
    number = models.PositiveIntegerField()  # 1, 2, 3 …
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = 'screens'
        unique_together = ('screen', 'row', 'number')
        ordering = ['row', 'number']

    def __str__(self):
        return f"{self.screen.name} – {self.row}{self.number}"


class Movie(models.Model):
    # ── Tenant Foundation ──────────────────────────────────────────────────
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.PROTECT,
        null=True, blank=True, related_name='movies'
    )
    # ── End Tenant Foundation ──────────────────────────────────────────────
    title = models.CharField(max_length=200)
    language = models.CharField(max_length=50, default='Tamil')
    genre = models.CharField(max_length=100, blank=True)
    duration_minutes = models.PositiveIntegerField()
    poster = models.ImageField(upload_to='posters/', blank=True, null=True)
    release_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    certificate = models.CharField(max_length=10, default='U/A')

    class Meta:
        app_label = 'screens'

    def __str__(self):
        return self.title


class Show(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = 'SCHEDULED', 'Scheduled'
        RUNNING = 'RUNNING', 'Running'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    screen = models.ForeignKey(Screen, on_delete=models.PROTECT, related_name='shows')
    movie = models.ForeignKey(Movie, on_delete=models.PROTECT, related_name='shows')
    show_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    duration_hours = models.DecimalField(max_digits=4, decimal_places=2, default=2.5)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    base_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    is_housefull = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'screens'
        ordering = ['show_date', 'start_time']

    def __str__(self):
        return f"{self.movie.title} | {self.screen.name} | {self.show_date} {self.start_time}"

    @property
    def total_seats(self):
        return self.screen.total_seats

    @property
    def booked_seats_count(self):
        from apps.bookings.models import BookedSeat
        return BookedSeat.objects.filter(
            booking__show=self,
            booking__status__in=['CONFIRMED', 'CHECKED_IN']
        ).count()

    @property
    def occupancy_percentage(self):
        total = self.total_seats
        if total == 0:
            return 0
        return round(self.booked_seats_count / total * 100, 1)


class ShowSchedule(models.Model):
    class ScheduleStatus(models.TextChoices):
        DRAFT     = 'DRAFT',     'Draft / Planned'
        PUBLISHED = 'PUBLISHED', 'Published / Live'
        PAUSED    = 'PAUSED',    'Paused'
        CANCELLED = 'CANCELLED', 'Cancelled'

    tenant           = models.ForeignKey('tenants.Tenant', on_delete=models.PROTECT, related_name='show_schedules')
    movie            = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='schedules')
    screen           = models.ForeignKey(Screen, on_delete=models.CASCADE, related_name='schedules')
    
    show_date        = models.DateField()
    show_slot        = models.CharField(max_length=50, help_text="e.g. Morning, Matinee, Evening, Night")
    start_time       = models.TimeField()
    end_time         = models.TimeField()
    
    status           = models.CharField(max_length=20, choices=ScheduleStatus.choices, default=ScheduleStatus.DRAFT)
    conflict_flag    = models.BooleanField(default=False, verbose_name='Conflict Flag')
    conflict_details = models.TextField(blank=True)
    holiday_override = models.BooleanField(default=False, verbose_name='Holiday Override')
    
    schedule_history = models.JSONField(default=list, blank=True, verbose_name='Schedule History')
    approved_by      = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_schedules')
    effective_date   = models.DateField()

    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'screens'
        ordering = ['show_date', 'start_time']

    def __str__(self):
        return f"{self.movie.title} Schedule | {self.screen.name} | {self.show_date} ({self.status})"

