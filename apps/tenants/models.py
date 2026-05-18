"""
AEC Cinemas Platform – Tenant Model
The foundation of the multi-tenant SaaS architecture.
AEC Cinemas is Tenant Zero (id=1).
"""

from django.db import models


class Tenant(models.Model):
    """
    Represents a cinema or cinema chain using the platform.
    Every business entity has exactly one Tenant record.
    """

    class Plan(models.TextChoices):
        STARTER = 'starter', 'Starter'
        PRO = 'pro', 'Pro'
        ENTERPRISE = 'enterprise', 'Enterprise'

    name = models.CharField(max_length=200)
    slug = models.SlugField(
        unique=True,
        help_text='URL-safe identifier, used for subdomain routing.'
    )
    is_active = models.BooleanField(default=True)
    plan = models.CharField(
        max_length=20,
        choices=Plan.choices,
        default=Plan.STARTER
    )
    timezone = models.CharField(
        max_length=50,
        default='Asia/Kolkata',
        help_text='IANA timezone string, e.g. Asia/Kolkata'
    )
    currency = models.CharField(max_length=5, default='INR')
    working_days_per_month = models.PositiveSmallIntegerField(
        default=26,
        help_text='Standard working days used for payroll proration.'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'tenants'
        verbose_name = 'Tenant'
        verbose_name_plural = 'Tenants'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.slug})"


class TenantModule(models.Model):
    """
    Feature flag per tenant. Modules can be enabled or disabled
    at the tenant level without any code changes.
    """
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='modules'
    )
    module_key = models.CharField(
        max_length=50,
        help_text='e.g. CAFE, LAMP_REGISTRY, FINANCE, ADVERTISING'
    )
    is_enabled = models.BooleanField(default=True)
    config_json = models.JSONField(
        default=dict,
        blank=True,
        help_text='Module-specific configuration overrides.'
    )

    class Meta:
        app_label = 'tenants'
        unique_together = ('tenant', 'module_key')
        verbose_name = 'Tenant Module'
        verbose_name_plural = 'Tenant Modules'

    def __str__(self):
        status = 'ON' if self.is_enabled else 'OFF'
        return f"{self.tenant.slug} / {self.module_key} [{status}]"
