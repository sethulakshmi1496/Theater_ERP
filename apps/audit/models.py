"""
AEC Cinemas – Audit Shield Models
Paper Trail: DeletedLog, StaffSession, ChangeLog
"""
from django.db import models
import json


class DeletedLog(models.Model):
    """
    Every deleted record is mirrored here before deletion.
    Staff CANNOT delete; Admin must confirm with password.
    MD has unconditional delete access.
    """
    # ── Tenant Foundation ──────────────────────────────────────────────────
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.PROTECT,
        null=True, blank=True, related_name='deleted_logs'
    )
    # ── End Tenant Foundation ──────────────────────────────────────────────
    table_name = models.CharField(max_length=100)
    record_id = models.IntegerField()
    record_repr = models.CharField(max_length=500, blank=True)
    original_data = models.JSONField()                             # Full snapshot
    deleted_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL,
        null=True, related_name='deletion_logs'
    )
    deletion_reason = models.TextField(blank=True)
    deleted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'audit'
        ordering = ['-deleted_at']
        verbose_name = 'Deleted Record Log'
        verbose_name_plural = 'Deleted Record Logs'

    def __str__(self):
        return f"[DELETED] {self.table_name}#{self.record_id} by {self.deleted_by} at {self.deleted_at}"


class ChangeLog(models.Model):
    """
    Tracks every CREATE and UPDATE operation for the paper trail.
    """
    ACTION_CREATE = 'CREATE'
    ACTION_UPDATE = 'UPDATE'
    ACTION_CHOICES = [(ACTION_CREATE, 'Create'), (ACTION_UPDATE, 'Update')]

    # ── Tenant Foundation ──────────────────────────────────────────────────
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.PROTECT,
        null=True, blank=True, related_name='change_logs'
    )
    # ── End Tenant Foundation ──────────────────────────────────────────────

    table_name = models.CharField(max_length=100)
    record_id = models.IntegerField()
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    changed_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL,
        null=True, related_name='change_logs'
    )
    changes = models.JSONField(default=dict)       # legacy support or structured diff
    before_json = models.JSONField(null=True, blank=True)
    after_json = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        app_label = 'audit'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.action} {self.table_name}#{self.record_id} by {self.changed_by}"


class StaffSession(models.Model):
    """
    Tracks active staff shift sessions for handover accountability.
    Records who was responsible during each time window.
    """
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_CLOSED = 'CLOSED'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_CLOSED, 'Closed'),
    ]

    user = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE,
        related_name='sessions'
    )
    shift_date = models.DateField()
    check_in = models.DateTimeField()
    check_out = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    notes = models.TextField(blank=True)
    entries_count = models.PositiveIntegerField(default=0)    # Incremented on each data entry

    class Meta:
        app_label = 'audit'
        ordering = ['-check_in']

    def __str__(self):
        return f"{self.user} shift {self.shift_date} ({self.status})"

    @property
    def duration_hours(self):
        if self.check_out:
            delta = self.check_out - self.check_in
            return round(delta.total_seconds() / 3600, 2)
        return None


class AuditShieldLog(models.Model):
    """
    Exposes approval audit trails, alert acknowledgment logs, financial corrections,
    sync activity references, and settlement approval tracking centrally.
    """
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.PROTECT,
        null=True, blank=True, related_name='audit_shield_logs'
    )
    module          = models.CharField(max_length=100, help_text="e.g. Movies, Settings, HR, Alert Center, Generator, Lamps, DCR")
    record_id       = models.IntegerField(null=True, blank=True)
    action_type     = models.CharField(max_length=50) # e.g. CREATE, UPDATE, DELETE, APPROVAL, ACKNOWLEDGE, CORRECTION, SYNC, SETTLEMENT_APPROVE
    user            = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_shield_actions')
    
    old_value       = models.JSONField(default=dict, blank=True, null=True)
    new_value       = models.JSONField(default=dict, blank=True, null=True)
    approval_status = models.CharField(max_length=50, blank=True, default='') # PENDING, APPROVED, REJECTED
    alert_status    = models.CharField(max_length=50, blank=True, default='') # TRIGGERED, ACKNOWLEDGED, RESOLVED, SNOOZED
    sync_ref        = models.CharField(max_length=100, blank=True, default='')
    remarks         = models.TextField(blank=True, default='')
    timestamp       = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'audit'
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.action_type}] {self.module} Record {self.record_id} by {self.user} at {self.timestamp}"

