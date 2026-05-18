"""AEC Cinemas – Revenue Models (Canteen + Advertising) with Inventory Logic"""

from django.db import models
from django.db import transaction
from decimal import Decimal

class CafeUnit(models.Model):
    """Multi-counter support for cafe/canteen operations."""
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.PROTECT,
        null=True, blank=True, related_name='cafe_units'
    )
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = 'revenue'

    def __str__(self):
        return self.name

class CanteenItem(models.Model):
    """Menu items and inventory catalog."""
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.PROTECT,
        null=True, blank=True, related_name='canteen_items'
    )
    name = models.CharField(max_length=100)
    sku = models.CharField(max_length=50, blank=True, help_text="SKU/Item Code")
    category = models.CharField(max_length=50, default='Snacks')
    unit = models.CharField(max_length=20, default='PCS', help_text="e.g., PCS, KG, LTR")
    
    # Pricing & Margin
    unit_price = models.DecimalField(max_digits=8, decimal_places=2, help_text="Selling price")
    unit_cost = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text="Average purchase cost")
    tax_rule = models.CharField(max_length=50, blank=True, help_text="e.g., GST 5%")
    
    # Inventory Governance
    is_track_stock = models.BooleanField(default=True)
    current_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reorder_level = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    supplier_name = models.CharField(max_length=200, blank=True)
    recipe_mapping = models.TextField(blank=True, help_text="Recipe/Consumption Mapping rules")
    notes = models.TextField(blank=True)
    
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = 'revenue'

    def __str__(self):
        return f"{self.name} ({self.sku}) – ₹{self.unit_price} (Stock: {self.current_stock})"

    @property
    def stock_risk(self):
        if self.is_track_stock and self.current_stock <= self.reorder_level:
            return True
        return False

class CafeInward(models.Model):
    """Inward stock movement (Purchases)."""
    class PostingStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PENDING = 'PENDING', 'Pending Approval'
        APPROVED = 'APPROVED', 'Approved'

    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.PROTECT, null=True, blank=True
    )
    cafe_unit = models.ForeignKey(CafeUnit, on_delete=models.PROTECT, null=True, blank=True)
    date = models.DateField()
    item = models.ForeignKey(CanteenItem, on_delete=models.PROTECT, related_name='inwards')
    
    invoice_no = models.CharField(max_length=100, blank=True)
    batch = models.CharField(max_length=50, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=8, decimal_places=2)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    vendor_name = models.CharField(max_length=200, blank=True, help_text="Link to Vendor Master conceptually")
    attachment = models.FileField(upload_to='revenue/inwards/bills/', blank=True, null=True)
    
    posting_status = models.CharField(max_length=20, choices=PostingStatus.choices, default=PostingStatus.DRAFT)
    
    entered_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='inwards_entered')
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='inwards_approved')
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'revenue'
        ordering = ['-date', '-created_at']

    def save(self, *args, **kwargs):
        self.total_cost = self.quantity * self.unit_cost
        super().save(*args, **kwargs)

class CafeWastage(models.Model):
    """Stock reduced via damage, expiry, or spillage."""
    class WastageCategory(models.TextChoices):
        SPOILAGE = 'SPOILAGE', 'Spoilage/Damage'
        EXPIRED = 'EXPIRED', 'Expired'
        INTERNAL_LOSS = 'INTERNAL_LOSS', 'Internal Loss'
        
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        APPROVED = 'APPROVED', 'Approved'

    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.PROTECT, null=True, blank=True
    )
    cafe_unit = models.ForeignKey(CafeUnit, on_delete=models.PROTECT, null=True, blank=True)
    date = models.DateField()
    item = models.ForeignKey(CanteenItem, on_delete=models.PROTECT, related_name='wastage_logs')
    category = models.CharField(max_length=50, choices=WastageCategory.choices, default=WastageCategory.SPOILAGE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=255)
    value = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Cost Impact")
    
    attachment = models.FileField(upload_to='revenue/wastage/proofs/', blank=True, null=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    
    entered_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='wastage_entered')
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='wastage_approved')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'revenue'
        ordering = ['-date', '-created_at']

    def save(self, *args, **kwargs):
        if not self.value and self.item:
            self.value = self.quantity * self.item.unit_cost

        super().save(*args, **kwargs)

class CanteenSale(models.Model):
    """Daily canteen counter sales entry."""
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.PROTECT,
        null=True, blank=True, related_name='canteen_sales'
    )
    cafe_unit = models.ForeignKey(CafeUnit, on_delete=models.PROTECT, null=True, blank=True, related_name='sales')
    date = models.DateField()
    item = models.ForeignKey(CanteenItem, on_delete=models.PROTECT, null=True, blank=True)
    item_name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cogs = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Cost of goods sold for margin logic")
    entered_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'revenue'
        ordering = ['-date', '-created_at']

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        self.total = self.quantity * self.unit_price
        
        if is_new and self.item:
            self.cogs = Decimal(self.quantity) * self.item.unit_cost

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.date} – {self.item_name} x{self.quantity} = ₹{self.total}"

class CafeDailyConsumption(models.Model):
    """Daily reconciliation of stock against sales."""
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        APPROVED = 'APPROVED', 'Approved'

    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.PROTECT, null=True, blank=True
    )
    date = models.DateField()
    item = models.ForeignKey(CanteenItem, on_delete=models.PROTECT, related_name='consumptions')
    
    opening_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sold_qty = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    recipe_consumption_qty = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    manual_adjustment_qty = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    closing_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    variance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    entered_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='consumptions_approved')

    class Meta:
        app_label = 'revenue'
        unique_together = ('tenant', 'date', 'item')
        ordering = ['-date']

class AdvertisingSlot(models.Model):
    """Pre-show and Interval advertising revenue."""
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.PROTECT,
        null=True, blank=True, related_name='ad_slots'
    )
    class SlotType(models.TextChoices):
        PRE_SHOW = 'PRE_SHOW', 'Pre-Show'
        INTERVAL = 'INTERVAL', 'Interval'

    show = models.ForeignKey('screens.Show', on_delete=models.PROTECT, related_name='ad_slots')
    slot_type = models.CharField(max_length=15, choices=SlotType.choices)
    advertiser_name = models.CharField(max_length=150)
    duration_seconds = models.PositiveIntegerField(default=30)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    invoice_number = models.CharField(max_length=50, blank=True)
    entered_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'revenue'
        ordering = ['-show__show_date']

class CafeExpense(models.Model):
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.PROTECT,
        null=True, blank=True, related_name='cafe_expenses'
    )
    cafe_unit = models.ForeignKey(CafeUnit, on_delete=models.PROTECT, null=True, blank=True, related_name='expenses')
    class Category(models.TextChoices):
        INVENTORY = 'INVENTORY', 'Inventory Purchase'
        WASTAGE = 'WASTAGE', 'Wastage'
        MISC = 'MISC', 'Miscellaneous'

    date = models.DateField()
    category = models.CharField(max_length=20, choices=Category.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    entered_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'revenue'
        ordering = ['-date', '-created_at']

class CafeReorderAlert(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        SNOOZED = 'SNOOZED', 'Snoozed'
        ORDERED = 'ORDERED', 'Marked Ordered'
        RESOLVED = 'RESOLVED', 'Resolved'

    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.PROTECT, null=True, blank=True
    )
    item = models.ForeignKey(CanteenItem, on_delete=models.PROTECT, related_name='reorder_alerts')
    
    current_stock_at_alert = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reorder_level_at_alert = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    suggested_reorder_qty = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    last_purchase_date = models.DateField(null=True, blank=True)
    supplier_name = models.CharField(max_length=200, blank=True)
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    snooze_until = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'revenue'
        ordering = ['-created_at']

    def __str__(self):
        return f"Alert for {self.item.name} - Status: {self.status}"


class Advertiser(models.Model):
    tenant         = models.ForeignKey('tenants.Tenant', on_delete=models.PROTECT, related_name='advertisers')
    name           = models.CharField(max_length=150)
    contact_person = models.CharField(max_length=100, blank=True)
    phone          = models.CharField(max_length=20, blank=True)
    email          = models.EmailField(blank=True)
    gst_number     = models.CharField(max_length=20, blank=True)
    is_active      = models.BooleanField(default=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'revenue'
        unique_together = ('tenant', 'name')
        ordering = ['name']

    def __str__(self):
        return self.name


class AdCampaign(models.Model):
    class AdType(models.TextChoices):
        SLIDES         = 'SLIDES',         'On-screen Slides'
        VIDEO_PROMO    = 'VIDEO_PROMO',    'Video Promo / Trailer'
        BANNER         = 'BANNER',         'Physical Banner'
        STANDEE        = 'STANDEE',        'Canteen Standee'
        COUNTER_AD     = 'COUNTER_AD',     'POS Counter Ad'

    class DeliveryStatus(models.TextChoices):
        PLANNED   = 'PLANNED',   'Planned'
        RUNNING   = 'RUNNING',   'Running'
        COMPLETED = 'COMPLETED', 'Completed'
        SUSPENDED = 'SUSPENDED', 'Suspended'

    class BillingStatus(models.TextChoices):
        UNBILLED    = 'UNBILLED',    'Unbilled'
        INVOICED    = 'INVOICED',    'Invoiced'
        PAID        = 'PAID',        'Paid'
        WRITTEN_OFF = 'WRITTEN_OFF', 'Written Off'

    tenant          = models.ForeignKey('tenants.Tenant', on_delete=models.PROTECT, related_name='campaigns')
    advertiser      = models.ForeignKey(Advertiser, on_delete=models.CASCADE, related_name='campaigns')
    campaign_name   = models.CharField(max_length=150)
    ad_type         = models.CharField(max_length=20, choices=AdType.choices, default=AdType.SLIDES)
    
    campaign_start  = models.DateField()
    campaign_end    = models.DateField()
    
    screen_mapping  = models.ForeignKey('screens.Screen', on_delete=models.SET_NULL, null=True, blank=True, related_name='campaigns')
    show_mapping    = models.ForeignKey('screens.Show', on_delete=models.SET_NULL, null=True, blank=True, related_name='campaigns')
    
    file_attachment = models.FileField(upload_to='revenue/ad_creatives/', blank=True, null=True)
    rate            = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    delivery_status = models.CharField(max_length=15, choices=DeliveryStatus.choices, default=DeliveryStatus.PLANNED)
    billing_status  = models.CharField(max_length=15, choices=BillingStatus.choices, default=BillingStatus.UNBILLED)

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'revenue'
        ordering = ['-campaign_start']

    def __str__(self):
        return f"{self.campaign_name} – {self.advertiser.name} ({self.delivery_status})"

