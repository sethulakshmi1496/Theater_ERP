"""AEC Cinemas – Payroll Models"""

from django.db import models


class Staff(models.Model):
    class Department(models.TextChoices):
        OPERATIONS = 'OPERATIONS', 'Operations'
        FRONT_DESK = 'FRONT_DESK', 'Front Desk'
        CANTEEN = 'CANTEEN', 'Canteen'
        SECURITY = 'SECURITY', 'Security'
        TECHNICAL = 'TECHNICAL', 'Technical'
        MANAGEMENT = 'MANAGEMENT', 'Management'
        CLEANING = 'CLEANING', 'Cleaning'

    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.PROTECT,
        null=True, blank=True, related_name='staff_members'
    )
    name = models.CharField(max_length=150)
    employee_id = models.CharField(max_length=20, unique=True)
    department = models.CharField(max_length=20, choices=Department.choices)
    designation = models.CharField(max_length=100)
    base_salary = models.DecimalField(max_digits=10, decimal_places=2)
    phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    join_date = models.DateField()
    is_active = models.BooleanField(default=True)
    user_account = models.OneToOneField(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='staff_profile'
    )
    
    # ── Enhanced staffing indicators ──────────────────────────────────────────
    shift             = models.CharField(max_length=50, blank=True, default='Morning', help_text="Current Scheduled Shift")
    attendance_status = models.CharField(max_length=50, blank=True, default='PRESENT', help_text="Today's Attendance Status")
    payroll_status    = models.CharField(max_length=50, blank=True, default='READY', help_text="Payroll Readiness Status")
    sync_status       = models.CharField(max_length=50, blank=True, default='SYNCED', help_text="HR System Sync Status")
    supervisor        = models.CharField(max_length=150, blank=True, default='', help_text="Direct Supervisor Name")
    notes             = models.TextField(blank=True, default='', help_text="Operational notes or exceptions")

    class Meta:
        app_label = 'payroll'
        ordering = ['department', 'name']

    def __str__(self):
        return f"{self.name} – {self.designation}"


class PayrollEntry(models.Model):
    class PayStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PAID = 'PAID', 'Paid'
        HOLD = 'HOLD', 'On Hold'

    staff = models.ForeignKey(Staff, on_delete=models.PROTECT, related_name='payroll_entries')
    month = models.PositiveSmallIntegerField()  # 1-12
    year = models.PositiveSmallIntegerField()
    base_salary = models.DecimalField(max_digits=10, decimal_places=2)
    allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=PayStatus.choices, default=PayStatus.PENDING)
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    entered_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'payroll'
        unique_together = ('staff', 'month', 'year')
        ordering = ['-year', '-month']

    def save(self, *args, **kwargs):
        self.net_salary = self.base_salary + self.allowances - self.deductions
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.staff.name} – {self.month}/{self.year} – ₹{self.net_salary} [{self.status}]"


# ─── STAFF REPORT CHILD MODULES (INTEGRATION MIRRORS) ─────────────────────────

class AttendanceMirror(models.Model):
    tenant          = models.ForeignKey('tenants.Tenant', on_delete=models.PROTECT, related_name='attendance_records')
    staff           = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='attendance_records')
    date            = models.DateField()
    check_in        = models.TimeField(null=True, blank=True)
    check_out       = models.TimeField(null=True, blank=True)
    status          = models.CharField(max_length=30, default='PRESENT', help_text="e.g. Present, Absent, Half-day, Late")
    exception_flag  = models.BooleanField(default=False, help_text="True if there is an anomaly (e.g. missed check-out)")
    exception_note  = models.TextField(blank=True)
    synced_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'payroll'
        unique_together = ('staff', 'date')
        ordering = ['-date', 'staff__name']

    def __str__(self):
        return f"{self.staff.name} Attendance ({self.date}) – {self.status}"


class ShiftMirror(models.Model):
    tenant          = models.ForeignKey('tenants.Tenant', on_delete=models.PROTECT, related_name='shift_records')
    staff           = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='shift_records')
    date            = models.DateField()
    shift_name      = models.CharField(max_length=50) # Morning, Evening, Night
    start_time      = models.TimeField()
    end_time        = models.TimeField()
    is_exception    = models.BooleanField(default=False, help_text="Unscheduled shift or double shift alert")
    exception_note  = models.TextField(blank=True)
    synced_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'payroll'
        unique_together = ('staff', 'date')
        ordering = ['-date', 'staff__name']

    def __str__(self):
        return f"{self.staff.name} Shift ({self.date}) – {self.shift_name}"


class HRSyncLog(models.Model):
    class SyncStatus(models.TextChoices):
        SUCCESS  = 'SUCCESS',  'Success'
        PARTIAL  = 'PARTIAL',  'Partial Success'
        FAILED   = 'FAILED',   'Failed'
        RETRYING = 'RETRYING', 'Retrying'

    tenant          = models.ForeignKey('tenants.Tenant', on_delete=models.PROTECT, related_name='hr_sync_logs')
    sync_time       = models.DateTimeField(auto_now_add=True)
    source_system   = models.CharField(max_length=100, default='External HR API')
    records_received = models.IntegerField(default=0)
    failed_records  = models.IntegerField(default=0)
    error_log       = models.TextField(blank=True)
    last_successful_sync = models.DateTimeField(null=True, blank=True)
    retry_count     = models.IntegerField(default=0)
    sync_status     = models.CharField(max_length=20, choices=SyncStatus.choices, default=SyncStatus.SUCCESS)

    class Meta:
        app_label = 'payroll'
        ordering = ['-sync_time']

    def __str__(self):
        return f"HR Sync Log {self.sync_time} | Status: {self.sync_status}"

