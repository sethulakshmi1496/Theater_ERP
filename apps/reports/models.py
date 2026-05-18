from django.db import models

class ManagementSnapshot(models.Model):
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE, related_name='management_snapshots'
    )
    period_type = models.CharField(max_length=20, choices=[('DAILY', 'Daily'), ('MONTHLY', 'Monthly')])
    period_date = models.DateField(null=True, blank=True)
    month = models.PositiveSmallIntegerField(null=True, blank=True)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    
    snapshot_data = models.JSONField(help_text="Stores full aggregated P&L data")
    comments = models.TextField(blank=True)
    saved_by = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name='saved_snapshots')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'reports'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.period_type} Snapshot ({self.period_date or f'{self.month}/{self.year}'}) - {self.created_at.date()}"
