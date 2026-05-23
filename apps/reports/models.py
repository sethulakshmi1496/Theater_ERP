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

class AIInsightReport(models.Model):
    PERIOD_CHOICES = [
        ('DAILY', 'Daily'),
        ('MONTHLY', 'Monthly'),
        ('YEARLY', 'Yearly'),
    ]
    
    MODULE_CHOICES = [
        ('EXECUTIVE', 'Executive Suite'),
        ('MOVIES', 'Movies'),
        ('BOOKINGS', 'Bookings'),
        ('REFUNDS', 'Refunds & Adjustments'),
        ('CAFE', 'Cafe Sales'),
        ('INVENTORY', 'Inventory Management'),
        ('ADVERTISING', 'Advertising'),
        ('UTILITY', 'Utility Readings'),
        ('WATER', 'Water Log'),
        ('GENERATOR', 'Generator'),
        ('LAMPS', 'Projection Lamps'),
        ('ASSETS', 'Asset Registry'),
        ('MAINTENANCE', 'Maintenance Desk'),
        ('PARKING', 'Parking Analytics'),
        ('FINANCE', 'Distributor Finance'),
        ('DCR', 'District DCR'),
        ('EXPENSE', 'Expense Register'),
        ('STAFF', 'Staff Report / HR Sync'),
        ('PNL', 'P&L Reports'),
        ('ALERTS', 'Alert Center'),
        ('AUDIT', 'Audit Shield'),
    ]

    SEVERITY_CHOICES = [
        ('INFO', 'Information'),
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]

    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='ai_reports')
    report_type = models.CharField(max_length=100) # e.g. Executive Daily Brief
    period_type = models.CharField(max_length=20, choices=PERIOD_CHOICES)
    module = models.CharField(max_length=50, choices=MODULE_CHOICES)
    
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    
    summary = models.TextField()
    suggestions = models.JSONField(default=list, blank=True)
    risks = models.JSONField(default=list, blank=True)
    opportunities = models.JSONField(default=list, blank=True)
    benchmark_notes = models.TextField(blank=True)
    
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='INFO')
    source_metadata = models.JSONField(default=dict, blank=True)
    
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='acknowledged_reports')
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'reports'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_module_display()} {self.get_period_type_display()} Insight - {self.created_at.date()}"

class AIActionItem(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('DISMISSED', 'Dismissed'),
    ]

    report = models.ForeignKey(AIInsightReport, on_delete=models.CASCADE, related_name='action_items')
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    assigned_to = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='ai_action_items')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='completed_ai_actions')

    class Meta:
        app_label = 'reports'
        ordering = ['-created_at']

    def __str__(self):
        return f"Action Item for {self.report.get_module_display()} - {self.status}"
