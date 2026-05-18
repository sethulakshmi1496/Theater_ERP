"""AEC Cinemas – Parking Analytics Models
Count-and-utilization module for audience behavior, planning, and expansion intelligence.
"""

from django.db import models
from decimal import Decimal


class ParkingZone(models.Model):
    """Master for configurable parking zones (e.g. Ground Floor, Terrace, Overflow)."""
    tenant      = models.ForeignKey('tenants.Tenant', on_delete=models.PROTECT, related_name='parking_zones')
    name        = models.CharField(max_length=100)
    zone_code   = models.CharField(max_length=20)
    capacity_2w = models.PositiveIntegerField(default=0, help_text='Total 2-wheeler slots')
    capacity_4w = models.PositiveIntegerField(default=0, help_text='Total 4-wheeler slots')
    is_overflow = models.BooleanField(default=False)
    is_active   = models.BooleanField(default=True)
    notes       = models.TextField(blank=True)

    class Meta:
        app_label = 'parking'
        unique_together = ('tenant', 'zone_code')
        ordering = ['zone_code']

    def __str__(self):
        return f"{self.name} ({self.zone_code})"


class ParkingSlotEntry(models.Model):
    """
    One record per zone per show-slot per day.
    Tracks 2W and 4W vehicles: opening count, entered, exited, closing (auto-calculated).
    """
    class ShowSlot(models.TextChoices):
        MORNING   = 'MORNING',   'Morning (10:00–13:00)'
        AFTERNOON = 'AFTERNOON', 'Afternoon (13:00–16:00)'
        EVENING   = 'EVENING',   'Evening (16:00–19:00)'
        NIGHT     = 'NIGHT',     'Night (19:00–22:00)'
        LATE_NIGHT = 'LATE_NIGHT', 'Late Night (22:00+)'

    class SpecialDayTag(models.TextChoices):
        NONE     = 'NONE',     'Normal Day'
        WEEKEND  = 'WEEKEND',  'Weekend'
        HOLIDAY  = 'HOLIDAY',  'Public Holiday'
        FESTIVAL = 'FESTIVAL', 'Festival'
        EVENT    = 'EVENT',    'Special Event'

    tenant   = models.ForeignKey('tenants.Tenant', on_delete=models.PROTECT, related_name='parking_entries')
    zone     = models.ForeignKey(ParkingZone, on_delete=models.PROTECT, related_name='entries')
    date     = models.DateField()
    show_slot = models.CharField(max_length=15, choices=ShowSlot.choices)

    # ── 2-Wheeler counts ──────────────────────────────────────────────────────
    tw_opening = models.PositiveIntegerField(default=0, verbose_name='2W Opening Count')
    tw_entered = models.PositiveIntegerField(default=0, verbose_name='2W Entered')
    tw_exited  = models.PositiveIntegerField(default=0, verbose_name='2W Exited')
    tw_closing = models.PositiveIntegerField(default=0, verbose_name='2W Closing', editable=False)

    # ── 4-Wheeler counts ──────────────────────────────────────────────────────
    fw_opening = models.PositiveIntegerField(default=0, verbose_name='4W Opening Count')
    fw_entered = models.PositiveIntegerField(default=0, verbose_name='4W Entered')
    fw_exited  = models.PositiveIntegerField(default=0, verbose_name='4W Exited')
    fw_closing = models.PositiveIntegerField(default=0, verbose_name='4W Closing', editable=False)

    overflow_used    = models.BooleanField(default=False)
    special_day_tag  = models.CharField(max_length=10, choices=SpecialDayTag.choices, default=SpecialDayTag.NONE)
    notes            = models.TextField(blank=True)

    entered_by  = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='parking_entries_entered')
    verified_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='parking_entries_verified')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'parking'
        unique_together = ('tenant', 'zone', 'date', 'show_slot')
        ordering = ['-date', 'show_slot']

    def save(self, *args, **kwargs):
        """Auto-calculate closing counts: Opening + Entered - Exited (floor at 0)."""
        self.tw_closing = max(self.tw_opening + self.tw_entered - self.tw_exited, 0)
        self.fw_closing = max(self.fw_opening + self.fw_entered - self.fw_exited, 0)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.zone} | {self.date} | {self.get_show_slot_display()}"

    # ── Computed occupancy properties ─────────────────────────────────────────
    @property
    def tw_occupancy_pct(self):
        cap = self.zone.capacity_2w
        return round((self.tw_closing / cap) * 100, 1) if cap else 0

    @property
    def fw_occupancy_pct(self):
        cap = self.zone.capacity_4w
        return round((self.fw_closing / cap) * 100, 1) if cap else 0

    @property
    def tw_fw_ratio(self):
        if self.fw_closing == 0:
            return None
        return round(self.tw_closing / self.fw_closing, 2)

    @property
    def is_high_occupancy(self):
        return self.tw_occupancy_pct >= 90 or self.fw_occupancy_pct >= 90
