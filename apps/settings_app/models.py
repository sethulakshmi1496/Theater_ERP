"""AEC Cinemas – Global Settings Model"""

from django.db import models
from decimal import Decimal


class TenantSetting(models.Model):
    """Editable system-wide configuration values stored in DB per tenant."""
    # ── Tenant Foundation ──────────────────────────────────────────────────
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='settings'
    )
    # ── End Tenant Foundation ──────────────────────────────────────────────
    key = models.CharField(max_length=100)
    value = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'settings_app'
        verbose_name = 'Tenant Setting'
        verbose_name_plural = 'Tenant Settings'
        unique_together = ('tenant', 'key')

    def __str__(self):
        return f"[{self.tenant.slug}] {self.key} = {self.value}"

    @classmethod
    def get(cls, tenant, key, default=None):
        if not tenant:
            return default
        try:
            obj = cls.objects.get(tenant=tenant, key=key)
            return Decimal(obj.value)
        except cls.DoesNotExist:
            return default

    @classmethod
    def get_str(cls, tenant, key, default=''):
        if not tenant:
            return default
        try:
            return cls.objects.get(tenant=tenant, key=key).value
        except cls.DoesNotExist:
            return default


class Vendor(models.Model):
    class Category(models.TextChoices):
        MAINTENANCE = 'MAINTENANCE', 'Maintenance Services'
        UTILITIES   = 'UTILITIES',   'Utility Provider'
        CAFE        = 'CAFE',        'Cafe Purchases'
        OPERATIONS  = 'OPERATIONS',  'General Operations'
        DISTRIBUTOR = 'DISTRIBUTOR', 'Film Distributor'
        EXPENSES    = 'EXPENSES',    'General Expenses'
        OTHERS      = 'OTHERS',      'Others'

    tenant              = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='vendors')
    name                = models.CharField(max_length=200, verbose_name='Vendor Name')
    category            = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHERS)
    contact_person      = models.CharField(max_length=150, blank=True)
    phone               = models.CharField(max_length=20, blank=True)
    email               = models.EmailField(blank=True)
    gst_number          = models.CharField(max_length=15, blank=True, verbose_name='GST Number')
    address             = models.TextField(blank=True)
    default_payment_terms = models.CharField(max_length=100, blank=True, help_text="e.g. Net 30, COD, Net 15")
    bank_details_ref    = models.TextField(blank=True, verbose_name='Bank Details Reference', help_text="Bank Account Number, IFSC, UPI info")
    is_active           = models.BooleanField(default=True, verbose_name='Active')
    notes               = models.TextField(blank=True)
    
    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'settings_app'
        unique_together = ('tenant', 'name')
        ordering  = ['name']

    def __str__(self):
        return f"{self.name} [{self.get_category_display()}]"


class AlertRule(models.Model):
    """
    Custom operational rules and limits for automated alerting.
    """
    tenant          = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='alert_rules')
    rule_name       = models.CharField(max_length=200, help_text="e.g. Lamp Hours Life, Daily Diesel Burn")
    module          = models.CharField(max_length=100, help_text="e.g. OPERATIONS, GENERATOR, LAMPS, UTILITY")
    threshold_value = models.DecimalField(max_digits=12, decimal_places=2, help_text="Value that triggers warning/alert")
    is_enabled      = models.BooleanField(default=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'settings_app'
        ordering = ['module', 'rule_name']

    def __str__(self):
        return f"[{self.module}] {self.rule_name} = {self.threshold_value} (Enabled: {self.is_enabled})"


