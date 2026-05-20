"""AEC Cinemas – Operations Models
Electricity Readings, Generator Logs, Lamp Hour Tracking
Business Logic: Dynamic occupancy (from real seats), predictive defaults, lamp lifecycle registry
"""

from django.db import models
from decimal import Decimal
from django.conf import settings


def get_total_theater_capacity(tenant=None):
    """Returns the real sum of total_seats across all active screens for a given tenant.
    Falls back to summing all active screens if no tenant is given.
    Never returns a hardcoded constant.
    """
    from apps.screens.models import Screen
    qs = Screen.objects.filter(is_active=True)
    if tenant:
        qs = qs.filter(tenant=tenant)
    total = sum(qs.values_list('total_seats', flat=True))
    return total or 1  # Avoid division by zero


class ElectricityReading(models.Model):
    # ── Tenant Foundation ──────────────────────────────────────────────────
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.PROTECT,
        null=True, blank=True, related_name='electricity_readings'
    )
    # ── End Tenant Foundation ──────────────────────────────────────────────
    date = models.DateField(unique=True)
    screen_1_shows = models.PositiveSmallIntegerField(default=0)
    screen_2_shows = models.PositiveSmallIntegerField(default=0)
    working_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tickets_sold = models.PositiveIntegerField(default=0)
    initial_reading = models.DecimalField(max_digits=10, decimal_places=2)
    final_reading = models.DecimalField(max_digits=10, decimal_places=2)
    # Auto-calculated
    total_consumption = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit_conversion = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    elec_charges = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    units_per_show = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    # Occupancy: (tickets_sold / (number_of_shows × 434)) × 100
    occupancy_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    entered_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'operations'
        ordering = ['-date']

    def calculate(self):
        from apps.settings_app.models import TenantSetting
        multiplier = TenantSetting.get(self.tenant, 'UNIT_MULTIPLIER', Decimal('40'))
        rate = TenantSetting.get(self.tenant, 'ELEC_RATE', Decimal('10.64'))
        total_shows = self.screen_1_shows + self.screen_2_shows

        self.total_consumption = self.final_reading - self.initial_reading
        self.unit_conversion = self.total_consumption * multiplier
        self.elec_charges = self.unit_conversion * rate
        self.units_per_show = (
            self.total_consumption / total_shows if total_shows > 0 else Decimal('0')
        )

        # ── OCCUPANCY FORMULA ───────────────────────────────────────────────────
        # Daily Occupancy % = (Total Tickets Sold / (No. of Shows × Dynamic Capacity)) × 100
        total_theater_capacity = get_total_theater_capacity(
            tenant=getattr(self, 'tenant', None)
        )
        max_capacity = Decimal(str(total_shows * total_theater_capacity))
        if max_capacity > 0 and self.tickets_sold > 0:
            self.occupancy_percent = round(
                (Decimal(str(self.tickets_sold)) / max_capacity) * 100, 2
            )
        else:
            self.occupancy_percent = Decimal('0')

    def save(self, *args, **kwargs):
        self.calculate()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Electricity {self.date} – ₹{self.elec_charges} – Occupancy {self.occupancy_percent}%"

    @property
    def total_shows(self):
        return self.screen_1_shows + self.screen_2_shows

    @property
    def is_high_consumption(self):
        avg = Decimal('3.84')
        return self.units_per_show > avg * Decimal('1.20')


class GeneratorLog(models.Model):
    class VarianceStatus(models.TextChoices):
        NORMAL    = 'NORMAL',    'Normal Burn'
        HIGH_BURN = 'HIGH_BURN', 'Abnormal High Burn'
        LOW_BURN  = 'LOW_BURN',  'Abnormal Low Burn'

    tenant               = models.ForeignKey('tenants.Tenant', on_delete=models.PROTECT, null=True, blank=True, related_name='generator_logs')
    date                 = models.DateField()
    
    opening_hours        = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    closing_hours        = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    runtime              = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text="Calculated running hours (closing - opening)")
    hours_run            = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Backwards compatible alias for runtime")
    
    opening_diesel_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Diesel stock level at start of day")
    refill_qty           = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Refilled diesel quantity in liters")
    refill_vendor        = models.CharField(max_length=200, blank=True)
    refill_cost          = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    consumed_qty         = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Diesel consumed in liters")
    closing_diesel_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Diesel stock level at end of day (opening + refill - consumed)")
    
    # Legacy fields
    consumption          = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text="Backwards compatible alias for consumed_qty")
    diesel_added         = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text="Backwards compatible alias for refill_qty")
    diesel_rate          = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    diesel_cost          = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    outage_tag           = models.CharField(max_length=150, blank=True, help_text="Grid outage code/tag reference")
    attachment           = models.FileField(upload_to='generators/attachments/', blank=True, null=True)
    variance_status      = models.CharField(max_length=20, choices=VarianceStatus.choices, default=VarianceStatus.NORMAL)
    
    entered_by           = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    notes                = models.TextField(blank=True)
    created_at           = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'operations'
        ordering = ['-date']

    def save(self, *args, **kwargs):
        # Sync opening and closing hours
        if self.closing_hours >= self.opening_hours:
            self.runtime = self.closing_hours - self.opening_hours
        self.hours_run = self.runtime

        # Calculate diesel stock logic
        self.closing_diesel_stock = self.opening_diesel_stock + self.refill_qty - self.consumed_qty

        # Sync legacy variables
        self.consumption = self.consumed_qty
        self.diesel_added = self.refill_qty
        self.diesel_cost = self.refill_cost
        if self.refill_qty > 0:
            self.diesel_rate = self.refill_cost / self.refill_qty
        else:
            self.diesel_rate = 0

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Generator {self.date} – Runtime: {self.runtime}h – Refill: {self.refill_qty}L"



class LampInventory(models.Model):
    class LampType(models.TextChoices):
        XENON        = 'XENON',        'Xenon'
        LASER        = 'LASER',        'Laser'
        METAL_HALIDE = 'METAL_HALIDE', 'Metal Halide'
        LED          = 'LED',          'LED'

    class Status(models.TextChoices):
        INSTALLED = 'INSTALLED', 'Installed'
        RUNNING   = 'RUNNING',   'Running'
        REPLACED  = 'REPLACED',  'Replaced'
        ARCHIVED  = 'ARCHIVED',  'Archived'

    screen               = models.ForeignKey('screens.Screen', on_delete=models.PROTECT, related_name='lamp_inventory')
    serial_number        = models.CharField(max_length=100, unique=True, verbose_name="Lamp ID")
    manufacturer         = models.CharField(max_length=100, blank=True)
    model_number         = models.CharField(max_length=100, blank=True)
    purchase_date        = models.DateField()
    purchase_rate        = models.DecimalField(max_digits=10, decimal_places=2)      # ₹ cost
    rated_lifespan_hours = models.DecimalField(max_digits=8, decimal_places=2, default=3000)
    
    installed_date       = models.DateField(null=True, blank=True, verbose_name="Install Date")
    retired_date         = models.DateField(null=True, blank=True, verbose_name="Replacement Date")
    is_current           = models.BooleanField(default=True)       # Only one lamp is 'current' per screen
    
    # Enhanced Lifecycle Fields
    lamp_type            = models.CharField(max_length=20, choices=LampType.choices, default=LampType.XENON, verbose_name="Lamp Type")
    opening_hours        = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Opening Hours")
    closing_hours        = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Closing Hours")
    working_hours        = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Working Hours")
    balance_life         = models.DecimalField(max_digits=10, decimal_places=2, default=3000, verbose_name="Balance Life")
    
    threshold            = models.DecimalField(max_digits=8, decimal_places=2, default=200, help_text="Warning threshold in hours")
    vendor               = models.CharField(max_length=150, blank=True, verbose_name="Vendor")
    status               = models.CharField(max_length=20, choices=Status.choices, default=Status.INSTALLED)
    archived_flag        = models.BooleanField(default=False, verbose_name="Archived Flag")
    
    notes                = models.TextField(blank=True)
    entered_by           = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    created_at           = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'operations'
        ordering = ['-purchase_date']

    def __str__(self):
        return f"{self.screen.name} - {self.serial_number} ({self.status})"

    @property
    def hours_used(self):
        """Total hours consumed across all logs for this lamp."""
        return self.lamp_logs.aggregate(
            total=models.Sum('working_hours')
        )['total'] or Decimal('0')

    @property
    def remaining_hours(self):
        return max(self.rated_lifespan_hours - self.hours_used, Decimal('0'))

    @property
    def depreciation_per_hour(self):
        if self.rated_lifespan_hours > 0:
            return self.purchase_rate / self.rated_lifespan_hours
        return Decimal('0')



class LampLog(models.Model):
    """Daily lamp hour log – linked to LampInventory for full back-tracing."""
    screen = models.ForeignKey('screens.Screen', on_delete=models.PROTECT, related_name='lamp_logs')
    lamp = models.ForeignKey(
        LampInventory, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='lamp_logs'
    )
    date = models.DateField()
    opening_hours = models.DecimalField(max_digits=8, decimal_places=2)
    working_hours = models.DecimalField(max_digits=6, decimal_places=2)
    closing_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    entered_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'operations'
        ordering = ['-date']
        unique_together = ('screen', 'date')

    def save(self, *args, **kwargs):
        from django.db import transaction
        from decimal import Decimal
        
        # Auto-link to current lamp for this screen if not specified
        if not self.lamp_id:
            current_lamp = LampInventory.objects.filter(screen=self.screen, is_current=True).first()
            if current_lamp:
                self.lamp = current_lamp

        if self.closing_hours is not None and self.opening_hours is not None:
            self.working_hours = self.closing_hours - self.opening_hours

        if self.lamp:
            self.balance = self.lamp.rated_lifespan_hours - self.closing_hours
        else:
            self.balance = self.screen.lamp_max_hours - self.closing_hours
            
        with transaction.atomic():
            super().save(*args, **kwargs)
            
            if self.lamp:
                # Sync hours to the physical lamp
                self.lamp.closing_hours = self.closing_hours
                self.lamp.working_hours = self.lamp.hours_used
                self.lamp.balance_life = self.lamp.rated_lifespan_hours - self.closing_hours
                
                # Check status transition
                if self.lamp.status == LampInventory.Status.INSTALLED:
                    self.lamp.status = LampInventory.Status.RUNNING
                
                self.lamp.save(update_fields=['closing_hours', 'working_hours', 'balance_life', 'status'])
                
                # Trigger warning/alert if crossed threshold
                if self.lamp.balance_life <= self.lamp.threshold:
                    from apps.operations.models import OperationalAlert
                    # Create operational alert if it doesn't already exist or trigger it
                    OperationalAlert.objects.get_or_create(
                        tenant=self.screen.tenant,
                        alert_type=OperationalAlert.AlertType.LAMP_THRESHOLD,
                        source_module='Projection Lamps',
                        reference_record=f"LampInventory-{self.lamp.id}",
                        defaults={
                            'severity': OperationalAlert.Severity.CRITICAL,
                            'status': OperationalAlert.Status.TRIGGERED,
                            'resolution_note': f"Projection Lamp S/N {self.lamp.serial_number} for Screen {self.screen.name} has crossed threshold warning limits. Balance life: {self.lamp.balance_life}h (Threshold: {self.lamp.threshold}h)."
                        }
                    )

            screen = self.screen.__class__.objects.select_for_update().get(pk=self.screen_id)
            screen.lamp_balance = self.balance
            screen.save(update_fields=['lamp_balance'])
            if screen.lamp_balance <= (Decimal('0.10') * screen.lamp_max_hours):
                try:
                    from apps.operations.views import send_lamp_alert
                    send_lamp_alert(screen)
                except ImportError:
                    pass

    def __str__(self):
        return f"Lamp {self.screen.name} {self.date} – Balance: {self.balance}h"


# ─── UTILITY MODELS (METER-BASED) ──────────────────────────────────────────────

class UtilityMeter(models.Model):
    class MeterType(models.TextChoices):
        ELECTRICITY = 'ELECTRICITY', 'Electricity'
        GENERATOR = 'GENERATOR', 'Generator'
        WATER = 'WATER', 'Water'
        OTHER = 'OTHER', 'Other'

    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.PROTECT, related_name='utility_meters'
    )
    name = models.CharField(max_length=100)
    meter_type = models.CharField(max_length=20, choices=MeterType.choices)
    unit_label = models.CharField(max_length=20, help_text="e.g. kWh, Liters")
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = 'operations'

    def __str__(self):
        return f"{self.name} ({self.get_meter_type_display()})"


class UtilityConfig(models.Model):
    meter = models.ForeignKey(UtilityMeter, on_delete=models.CASCADE, related_name='configs')
    multiplier = models.DecimalField(max_digits=10, decimal_places=4, default=1)
    rate_per_unit = models.DecimalField(max_digits=10, decimal_places=4)
    effective_from = models.DateField()
    
    class Meta:
        app_label = 'operations'
        ordering = ['-effective_from']

    def __str__(self):
        return f"{self.meter.name} Config (x{self.multiplier} @ {self.rate_per_unit})"


class UtilityReading(models.Model):
    class UtilityType(models.TextChoices):
        ELECTRICITY = 'ELECTRICITY', 'Electricity'
        WATER       = 'WATER',       'Water'
        GENERATOR   = 'GENERATOR',   'Generator'
        OTHER       = 'OTHER',       'Other'

    class AnomalyStatus(models.TextChoices):
        NORMAL  = 'NORMAL',  'Normal'
        WARNING = 'WARNING', 'Warning'
        ANOMALY = 'ANOMALY', 'Critical Anomaly'

    class PostingStatus(models.TextChoices):
        DRAFT  = 'DRAFT',  'Draft'
        POSTED = 'POSTED', 'Posted'

    meter           = models.ForeignKey(UtilityMeter, on_delete=models.PROTECT, related_name='readings')
    utility_type    = models.CharField(max_length=20, choices=UtilityType.choices, default=UtilityType.ELECTRICITY)
    reading_date    = models.DateField()
    
    opening         = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    closing         = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    initial_reading = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Backwards compatible alias for opening")
    final_reading   = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Backwards compatible alias for closing")
    
    consumption     = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    billed_units    = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_cost      = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    
    bill_amount     = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Bill Amount")
    bill_attachment = models.FileField(upload_to='utilities/bills/', blank=True, null=True, verbose_name="Bill Attachment")
    
    trend_variance  = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text="Percentage variance compared to baseline daily consumption")
    anomaly_status  = models.CharField(max_length=20, choices=AnomalyStatus.choices, default=AnomalyStatus.NORMAL, verbose_name="Anomaly Status")
    review_note     = models.TextField(blank=True, verbose_name="Review Note")
    posting_status  = models.CharField(max_length=20, choices=PostingStatus.choices, default=PostingStatus.DRAFT, verbose_name="Posting Status")
    
    entered_by      = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    notes           = models.TextField(blank=True)
    override_reason = models.TextField(blank=True, help_text="Required if opening reading differs from previous closing")
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'operations'
        unique_together = ('meter', 'reading_date')
        ordering = ['-reading_date']

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.closing is not None and self.opening is not None:
            if self.closing < self.opening:
                raise ValidationError({"closing": "Closing reading cannot be less than opening reading."})
        
        if not self.pk:
            prev = UtilityReading.objects.filter(meter=self.meter, reading_date__lt=self.reading_date).order_by('-reading_date').first()
            if prev and self.opening != prev.closing:
                if not self.override_reason:
                    raise ValidationError({"override_reason": f"Opening reading ({self.opening}) differs from previous closing reading ({prev.closing}). Override reason is required."})

    def save(self, *args, **kwargs):
        # Enforce sync with legacy fields
        self.initial_reading = self.opening
        self.final_reading = self.closing
        
        self.clean()
        self.consumption = self.closing - self.opening
        
        # Get active config for the reading date
        config = self.meter.configs.filter(effective_from__lte=self.reading_date).first()
        if config:
            self.billed_units = self.consumption * config.multiplier
            self.total_cost = self.billed_units * config.rate_per_unit
        else:
            self.billed_units = self.consumption
            self.total_cost = 0
            
        if self.bill_amount == 0 and self.total_cost > 0:
            self.bill_amount = self.total_cost

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.utility_type} - {self.meter.name} - {self.reading_date} - ₹{self.bill_amount}"



# ─── UNIVERSAL ASSET REGISTRY ──────────────────────────────────────────────

class AssetCategory(models.Model):
    key = models.CharField(max_length=50, unique=True, help_text="e.g. LAMP, PROJECTOR, SOUND, DG_SET, METER")
    label = models.CharField(max_length=100)
    tracks_hours = models.BooleanField(default=False)
    tracks_fuel = models.BooleanField(default=False)
    tracks_units = models.BooleanField(default=False)

    class Meta:
        app_label = 'operations'
        verbose_name_plural = 'Asset Categories'

    def __str__(self):
        return self.label


class AssetTemplate(models.Model):
    category = models.ForeignKey(AssetCategory, on_delete=models.CASCADE, related_name='templates')
    manufacturer = models.CharField(max_length=100)
    model_number = models.CharField(max_length=100)
    rated_life_hours = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    specs_json = models.JSONField(default=dict, blank=True)

    class Meta:
        app_label = 'operations'

    def __str__(self):
        return f"{self.manufacturer} {self.model_number}"


class TenantAsset(models.Model):
    class StatusChoices(models.TextChoices):
        OPERATIONAL    = 'OPERATIONAL',    'Operational'
        OUT_OF_SERVICE = 'OUT_OF_SERVICE', 'Out of Service'
        MAINTENANCE    = 'MAINTENANCE',    'Under Maintenance'
        RETIRED        = 'RETIRED',        'Retired'

    tenant                = models.ForeignKey('tenants.Tenant', on_delete=models.PROTECT, related_name='assets')
    template              = models.ForeignKey(AssetTemplate, on_delete=models.PROTECT, related_name='instances')
    screen                = models.ForeignKey('screens.Screen', on_delete=models.SET_NULL, null=True, blank=True, related_name='assets')
    
    asset_id              = models.CharField(max_length=50, blank=True, unique=True, help_text="Unique Canonical Asset ID")
    asset_name            = models.CharField(max_length=150, default='', verbose_name="Asset Name")
    location              = models.CharField(max_length=150, default='', blank=True, verbose_name="Location")
    serial_number         = models.CharField(max_length=100, default='', verbose_name="Serial No")
    
    purchase_date         = models.DateField(null=True, blank=True, verbose_name="Purchase Date")
    vendor                = models.CharField(max_length=150, blank=True, verbose_name="Vendor")
    warranty              = models.CharField(max_length=200, blank=True, verbose_name="Warranty")
    
    status                = models.CharField(max_length=30, choices=StatusChoices.choices, default=StatusChoices.OPERATIONAL)
    service_due_date      = models.DateField(null=True, blank=True, verbose_name="Service Due Date")
    notes                 = models.TextField(blank=True)
    
    installed_date        = models.DateField(null=True, blank=True)
    current_hours         = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    alert_threshold_hours = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active             = models.BooleanField(default=True)
    
    class Meta:
        app_label = 'operations'

    def __str__(self):
        return f"{self.asset_name} ({self.asset_id}) - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        # Auto-generate asset_id if blank
        if not self.asset_id:
            cat_key = self.template.category.key[:4].upper()
            import uuid
            self.asset_id = f"AST-{cat_key}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    @property
    def remaining_hours(self):
        if self.template.rated_life_hours:
            return max(self.template.rated_life_hours - self.current_hours, Decimal('0'))
        return None

    @property
    def life_percentage(self):
        if self.template.rated_life_hours and self.template.rated_life_hours > 0:
            return (self.remaining_hours / self.template.rated_life_hours) * 100
        return None



class AssetLog(models.Model):
    asset = models.ForeignKey(TenantAsset, on_delete=models.PROTECT, related_name='logs')
    log_date = models.DateField()
    opening_value = models.DecimalField(max_digits=10, decimal_places=2)
    closing_value = models.DecimalField(max_digits=10, decimal_places=2)
    delta = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    entered_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'operations'
        ordering = ['-log_date']

    def save(self, *args, **kwargs):
        self.delta = self.closing_value - self.opening_value
        super().save(*args, **kwargs)
        
        # Update current_hours on asset if it tracks hours
        if self.asset.template.category.tracks_hours:
            from django.db.models import Sum
            total_hours = self.asset.logs.aggregate(total=Sum('delta'))['total'] or Decimal('0')
            self.asset.current_hours = total_hours
            self.asset.save(update_fields=['current_hours'])


# ─── MAINTENANCE DESK ──────────────────────────────────────────────────────────

class FaultTicket(models.Model):
    """Breakdown or fault reported against a tenant asset."""
    class Priority(models.TextChoices):
        LOW    = 'LOW',    'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH   = 'HIGH',   'High'
        URGENT = 'URGENT', 'Urgent'

    class Status(models.TextChoices):
        OPEN        = 'OPEN',        'Open'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        ESCALATED   = 'ESCALATED',   'Escalated'
        RESOLVED    = 'RESOLVED',    'Resolved'
        CLOSED      = 'CLOSED',      'Closed'

    class Category(models.TextChoices):
        ELECTRICAL   = 'ELECTRICAL',   'Electrical'
        MECHANICAL   = 'MECHANICAL',   'Mechanical'
        HVAC         = 'HVAC',         'HVAC / Air Conditioning'
        AV           = 'AV',           'Audio / Visual'
        PROJECTION   = 'PROJECTION',   'Projection'
        PLUMBING     = 'PLUMBING',     'Plumbing'
        CIVIL        = 'CIVIL',        'Civil / Structural'
        IT           = 'IT',           'IT / Networking'
        OTHER        = 'OTHER',        'Other'

    tenant     = models.ForeignKey('tenants.Tenant', on_delete=models.PROTECT, related_name='fault_tickets')
    asset      = models.ForeignKey(TenantAsset, on_delete=models.PROTECT, related_name='fault_tickets')
    ticket_no  = models.CharField(max_length=30, blank=True, unique=True)
    category   = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    title      = models.CharField(max_length=200)
    description = models.TextField()
    priority    = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    status      = models.CharField(max_length=15, choices=Status.choices, default=Status.OPEN)

    reported_date = models.DateField()
    reported_time = models.TimeField(null=True, blank=True)
    resolved_date = models.DateField(null=True, blank=True)
    closure_timestamp = models.DateTimeField(null=True, blank=True)

    reported_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='fault_tickets_reported')
    assigned_to = models.CharField(max_length=200, blank=True, help_text='Technician / Vendor name')

    resolution_note = models.TextField(blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Repair cost')
    downtime_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    is_escalated = models.BooleanField(default=False)
    escalation_reason = models.TextField(blank=True)

    attachment = models.FileField(upload_to='maintenance/faults/', blank=True, null=True)
    notes      = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'operations'
        ordering  = ['-reported_date', '-created_at']

    def save(self, *args, **kwargs):
        if not self.ticket_no:
            from django.utils import timezone
            ts = timezone.now().strftime('%Y%m%d%H%M%S')
            self.ticket_no = f"FT-{ts}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ticket_no} [{self.priority}] {self.title} – {self.status}"


class PMSchedule(models.Model):
    """Preventive Maintenance schedule for a tenant asset."""
    class Frequency(models.TextChoices):
        DAILY       = 'DAILY',       'Daily'
        WEEKLY      = 'WEEKLY',      'Weekly'
        MONTHLY     = 'MONTHLY',     'Monthly'
        QUARTERLY   = 'QUARTERLY',   'Quarterly'
        HALF_YEARLY = 'HALF_YEARLY', 'Half-Yearly'
        YEARLY      = 'YEARLY',      'Yearly'
        CUSTOM      = 'CUSTOM',      'Custom (Hours)'

    class MaintenanceType(models.TextChoices):
        INSPECTION   = 'INSPECTION',   'Inspection'
        LUBRICATION  = 'LUBRICATION',  'Lubrication'
        CALIBRATION  = 'CALIBRATION',  'Calibration'
        CLEANING     = 'CLEANING',     'Cleaning'
        REPLACEMENT  = 'REPLACEMENT',  'Parts Replacement'
        TESTING      = 'TESTING',      'Testing & Verification'
        FULL_SERVICE = 'FULL_SERVICE', 'Full Service'
        OTHER        = 'OTHER',        'Other'

    class Status(models.TextChoices):
        ACTIVE    = 'ACTIVE',    'Active'
        PAUSED    = 'PAUSED',    'Paused'
        COMPLETED = 'COMPLETED', 'Completed'

    tenant         = models.ForeignKey('tenants.Tenant', on_delete=models.PROTECT, related_name='pm_schedules')
    asset          = models.ForeignKey(TenantAsset, on_delete=models.PROTECT, related_name='pm_schedules')
    task_name      = models.CharField(max_length=200)
    maintenance_type = models.CharField(max_length=20, choices=MaintenanceType.choices, default=MaintenanceType.INSPECTION)
    frequency      = models.CharField(max_length=15, choices=Frequency.choices)
    interval_hours = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text='For CUSTOM frequency')
    last_done_date = models.DateField(null=True, blank=True)
    next_due_date  = models.DateField()
    assigned_to    = models.CharField(max_length=200, blank=True, help_text='Vendor / Technician name')
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    checklist      = models.JSONField(default=list, blank=True, help_text='List of checklist items as JSON array')
    reminder_lead_days = models.PositiveIntegerField(default=3, help_text='Days before due to send reminder alert')
    completed_count = models.PositiveIntegerField(default=0, help_text='Total number of times this PM has been completed')
    status         = models.CharField(max_length=15, choices=Status.choices, default=Status.ACTIVE)
    notes          = models.TextField(blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'operations'
        ordering  = ['next_due_date']

    def __str__(self):
        return f"PM: {self.task_name} ({self.get_maintenance_type_display()}) – Due: {self.next_due_date}"

    @property
    def is_overdue(self):
        from django.utils import timezone
        return self.status == self.Status.ACTIVE and self.next_due_date < timezone.now().date()

    @property
    def alert_due(self):
        """True if within reminder lead time window."""
        from django.utils import timezone
        import datetime
        threshold = timezone.now().date() + datetime.timedelta(days=self.reminder_lead_days)
        return self.status == self.Status.ACTIVE and self.next_due_date <= threshold


class WorkOrder(models.Model):
    """Work order generated from a fault ticket or PM schedule."""
    class Type(models.TextChoices):
        CORRECTIVE  = 'CORRECTIVE',  'Corrective (Fault)'
        PREVENTIVE  = 'PREVENTIVE',  'Preventive (PM)'
        INSPECTION  = 'INSPECTION',  'Inspection'

    class Status(models.TextChoices):
        DRAFT       = 'DRAFT',       'Draft'
        OPEN        = 'OPEN',        'Open'
        ASSIGNED    = 'ASSIGNED',    'Assigned'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED   = 'COMPLETED',   'Completed'
        CANCELLED   = 'CANCELLED',   'Cancelled'

    tenant       = models.ForeignKey('tenants.Tenant', on_delete=models.PROTECT, related_name='work_orders')
    asset        = models.ForeignKey(TenantAsset, on_delete=models.PROTECT, related_name='work_orders')
    fault_ticket = models.ForeignKey(FaultTicket, on_delete=models.SET_NULL, null=True, blank=True, related_name='work_orders')
    pm_schedule  = models.ForeignKey(PMSchedule,  on_delete=models.SET_NULL, null=True, blank=True, related_name='work_orders')
    wo_number    = models.CharField(max_length=50, blank=True, unique=True)
    type         = models.CharField(max_length=15, choices=Type.choices, default=Type.CORRECTIVE)
    description  = models.TextField()
    scope_of_work = models.TextField(blank=True, help_text='Detailed scope / instructions for the technician')
    status       = models.CharField(max_length=15, choices=Status.choices, default=Status.DRAFT)

    # Assignment
    assigned_to        = models.CharField(max_length=200, blank=True, help_text='Vendor / Technician name')
    assigned_timestamp = models.DateTimeField(null=True, blank=True)

    # Schedule & Completion
    scheduled_date = models.DateField(null=True, blank=True)
    completed_date = models.DateField(null=True, blank=True)

    # Costs
    labour_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    parts_cost  = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    actual_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Any additional miscellaneous cost')
    total_cost  = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Parts & Invoice
    parts_used        = models.TextField(blank=True, help_text='Comma-separated or freetext parts list')
    vendor_invoice_no = models.CharField(max_length=100, blank=True)
    vendor_invoice    = models.FileField(upload_to='maintenance/invoices/', blank=True, null=True)
    attachment        = models.FileField(upload_to='maintenance/work_orders/', blank=True, null=True)
    notes             = models.TextField(blank=True)

    entered_by  = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'operations'
        ordering  = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.wo_number:
            from django.utils import timezone
            self.wo_number = f"WO-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        self.total_cost = self.labour_cost + self.parts_cost + self.actual_cost
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.wo_number} – {self.asset} – {self.status}"


class AMCContract(models.Model):
    """Annual Maintenance / Warranty contract covering one or more assets."""
    class Status(models.TextChoices):
        ACTIVE   = 'ACTIVE',   'Active'
        EXPIRING = 'EXPIRING', 'Expiring Soon'
        EXPIRED  = 'EXPIRED',  'Expired'
        RENEWED  = 'RENEWED',  'Renewed'
        LAPSED   = 'LAPSED',   'Lapsed'

    class CoverageType(models.TextChoices):
        AMC_COMPREHENSIVE = 'AMC_COMPREHENSIVE', 'AMC – Comprehensive'
        AMC_NON_COMP      = 'AMC_NON_COMP',      'AMC – Non-Comprehensive'
        WARRANTY_OEM      = 'WARRANTY_OEM',       'OEM Warranty'
        WARRANTY_EXTENDED = 'WARRANTY_EXTENDED',  'Extended Warranty'
        SERVICE_CONTRACT  = 'SERVICE_CONTRACT',   'Annual Service Contract'

    class RenewalStatus(models.TextChoices):
        NOT_INITIATED = 'NOT_INITIATED', 'Not Initiated'
        IN_PROGRESS   = 'IN_PROGRESS',   'Renewal In Progress'
        RENEWED       = 'RENEWED',       'Renewed'
        NOT_RENEWING  = 'NOT_RENEWING',  'Not Renewing'

    tenant           = models.ForeignKey('tenants.Tenant', on_delete=models.PROTECT, related_name='amc_contracts')
    contract_no      = models.CharField(max_length=100)
    vendor_name      = models.CharField(max_length=200)
    vendor_contact   = models.CharField(max_length=200, blank=True, help_text='Support contact name / phone / email')
    assets           = models.ManyToManyField(TenantAsset, related_name='amc_contracts', blank=True)

    # Coverage period
    start_date       = models.DateField()
    end_date         = models.DateField(help_text='AMC / contract end date')
    warranty_end_date = models.DateField(null=True, blank=True, help_text='OEM warranty expiry (may differ from AMC)')

    coverage_type    = models.CharField(max_length=25, choices=CoverageType.choices, default=CoverageType.AMC_COMPREHENSIVE)
    coverage_details = models.TextField(blank=True, help_text='What is covered under this contract')
    contract_value   = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Status & renewal
    status           = models.CharField(max_length=15, choices=Status.choices, default=Status.ACTIVE)
    renewal_status   = models.CharField(max_length=15, choices=RenewalStatus.choices, default=RenewalStatus.NOT_INITIATED)
    renewal_history  = models.JSONField(default=list, blank=True, help_text='Auto-appended log of renewal events')

    attachment       = models.FileField(upload_to='maintenance/amc/agreements/', blank=True, null=True)
    notes            = models.TextField(blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'operations'
        ordering  = ['end_date']

    @property
    def days_to_expiry(self):
        from django.utils import timezone
        delta = self.end_date - timezone.now().date()
        return delta.days

    @property
    def warranty_days_remaining(self):
        from django.utils import timezone
        if self.warranty_end_date:
            return (self.warranty_end_date - timezone.now().date()).days
        return None

    @property
    def is_expiring_soon(self):
        return 0 < self.days_to_expiry <= 60

    def __str__(self):
        return f"AMC {self.contract_no} – {self.vendor_name} [{self.get_coverage_type_display()}] (Expires: {self.end_date})"


class ServiceHistory(models.Model):
    """
    Immutable longitudinal service log appended whenever a WorkOrder is completed.
    Provides the full lifecycle record for each asset — from first fault to last PM.
    """
    class ServiceType(models.TextChoices):
        CORRECTIVE  = 'CORRECTIVE',  'Corrective Repair'
        PREVENTIVE  = 'PREVENTIVE',  'Preventive Maintenance'
        INSPECTION  = 'INSPECTION',  'Inspection'
        WARRANTY    = 'WARRANTY',    'Warranty Service'
        AMC         = 'AMC',         'AMC Service'

    tenant       = models.ForeignKey('tenants.Tenant', on_delete=models.PROTECT, related_name='service_history')
    asset        = models.ForeignKey(TenantAsset, on_delete=models.PROTECT, related_name='service_history')
    work_order   = models.OneToOneField(WorkOrder, on_delete=models.PROTECT, related_name='service_record', null=True, blank=True)
    fault_ticket = models.ForeignKey(FaultTicket, on_delete=models.SET_NULL, null=True, blank=True, related_name='service_history')
    amc_contract = models.ForeignKey(AMCContract, on_delete=models.SET_NULL, null=True, blank=True, related_name='service_history')

    service_date = models.DateField()
    service_type = models.CharField(max_length=15, choices=ServiceType.choices, default=ServiceType.CORRECTIVE)
    vendor_name  = models.CharField(max_length=200, blank=True)

    cost            = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    downtime_hours  = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    attachment      = models.FileField(upload_to='maintenance/service_history/', blank=True, null=True)
    notes           = models.TextField(blank=True)

    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'operations'
        ordering  = ['-service_date', '-created_at']
        verbose_name_plural = 'Service History'

    def __str__(self):
        return f"{self.asset} | {self.service_date} | {self.get_service_type_display()} | ₹{self.cost}"


class WaterLog(models.Model):
    """
    Log to track water utility usage, tanker purchases, municipal bills and vendor costs.
    Logically tied to utility cost tracking and expense flows.
    """
    tenant          = models.ForeignKey('tenants.Tenant', on_delete=models.PROTECT, related_name='water_logs')
    date            = models.DateField()
    meter           = models.ForeignKey(UtilityMeter, on_delete=models.PROTECT, limit_choices_to={'meter_type': UtilityMeter.MeterType.WATER}, related_name='water_logs')
    
    opening_reading = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    closing_reading = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    consumption     = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Metered consumption (calculated: closing - opening)")
    
    tanker_purchase_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Tanker purchase quantity (in Liters)")
    tanker_cost         = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    municipal_bill      = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    attachment      = models.FileField(upload_to='maintenance/water_logs/', blank=True, null=True)
    linked_vendor   = models.CharField(max_length=200, blank=True)
    expense_ref     = models.CharField(max_length=100, blank=True, help_text="Linked expense entry code/ID")
    notes           = models.TextField(blank=True)
    
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'operations'
        ordering  = ['-date']

    def save(self, *args, **kwargs):
        # Auto-calculate consumption
        self.consumption = max(self.closing_reading - self.opening_reading, 0)
        super().save(*args, **kwargs)

    def __str__(self):
        total_cost = self.tanker_cost + self.municipal_bill
        return f"Water Log {self.date} | Meter: {self.meter.name} | Total Cost: ₹{total_cost}"


class OperationalAlert(models.Model):
    """
    Central operational alert inbox model for low stock, lamp lifetime, 
    maintenance events, parking issues, variance logs and sync failures.
    """
    class AlertType(models.TextChoices):
        LOW_STOCK          = 'LOW_STOCK',          'Low Stock'
        LAMP_THRESHOLD     = 'LAMP_THRESHOLD',     'Lamp Threshold'
        ASSET_PM_DUE       = 'ASSET_PM_DUE',       'Asset Maintenance Due'
        UTILITY_ANOMALY    = 'UTILITY_ANOMALY',    'Utility Anomaly'
        DCR_MISMATCH       = 'DCR_MISMATCH',       'DCR Mismatch'
        SETTLEMENT_OVERDUE = 'SETTLEMENT_OVERDUE', 'Settlement Overdue'
        PARKING_OVERFLOW   = 'PARKING_OVERFLOW',   'Parking Overflow'
        PENDING_APPROVAL   = 'PENDING_APPROVAL',   'Pending Approval'
        GENERATOR_VARIANCE = 'GENERATOR_VARIANCE', 'Generator Variance'
        HR_SYNC_FAILURE    = 'HR_SYNC_FAILURE',    'HR Sync Failure'

    class Severity(models.TextChoices):
        INFO     = 'INFO',     'Info'
        WARNING  = 'WARNING',  'Warning'
        CRITICAL = 'CRITICAL', 'Critical'

    class Status(models.TextChoices):
        TRIGGERED    = 'TRIGGERED',    'Triggered'
        ACKNOWLEDGED = 'ACKNOWLEDGED', 'Acknowledged'
        RESOLVED     = 'RESOLVED',     'Resolved'
        SNOOZED      = 'SNOOZED',      'Snoozed'

    tenant          = models.ForeignKey('tenants.Tenant', on_delete=models.PROTECT, related_name='operational_alerts')
    alert_type      = models.CharField(max_length=30, choices=AlertType.choices)
    source_module   = models.CharField(max_length=50, help_text="e.g. Revenue, Screens, Maintenance, Utilities")
    severity        = models.CharField(max_length=15, choices=Severity.choices, default=Severity.WARNING)
    triggered_time  = models.DateTimeField(auto_now_add=True)
    reference_record = models.CharField(max_length=150, blank=True, help_text="Reference table and primary key e.g. BookingCorrection-4")
    
    assigned_user   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_alerts')
    status          = models.CharField(max_length=15, choices=Status.choices, default=Status.TRIGGERED)
    
    acknowledged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='acknowledged_alerts')
    resolved_by     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_alerts')
    resolution_note = models.TextField(blank=True)
    
    audit_ref       = models.CharField(max_length=50, blank=True, unique=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'operations'
        ordering  = ['-triggered_time']

    def save(self, *args, **kwargs):
        if not self.audit_ref:
            from django.utils import timezone
            ts = timezone.now().strftime('%Y%m%d%H%M%S')
            self.audit_ref = f"AL-{self.alert_type[:3]}-{ts}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.audit_ref} | {self.get_alert_type_display()} | {self.status}"


