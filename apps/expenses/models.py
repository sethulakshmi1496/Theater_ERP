from django.db import models
from django.utils import timezone

class ExpenseSubcategory(models.Model):
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE, related_name='expense_subcategories'
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = 'expenses'
        verbose_name_plural = 'Expense Subcategories'
        unique_together = ('tenant', 'name')

    def __str__(self):
        return f"{self.name}"

class Expense(models.Model):
    class ExpenseType(models.TextChoices):
        PETTY_EXPENSE = 'PETTY', 'Petty Expense'
        REPRESENTATIVE_BATA = 'BATA', 'Representative Bata'
        PUBLICITY_PAYMENT = 'PUBLICITY', 'Publicity Payment'
        CLEANING = 'CLEANING', 'Cleaning'
        WATER = 'WATER', 'Water'
        REPAIR_MAINTENANCE = 'REPAIR', 'Repair & Maintenance'
        MISCELLANEOUS = 'MISC', 'Miscellaneous'

    class PaymentMode(models.TextChoices):
        CASH = 'CASH', 'Cash'
        UPI = 'UPI', 'UPI'
        BANK_TRANSFER = 'BANK', 'Bank Transfer'
        CHEQUE = 'CHEQUE', 'Cheque'

    class ApprovalStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PENDING = 'PENDING', 'Pending Approval'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    class PostingStatus(models.TextChoices):
        UNPOSTED = 'UNPOSTED', 'Unposted'
        POSTED = 'POSTED', 'Posted to P&L'

    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.PROTECT, related_name='expenses'
    )
    date = models.DateField(default=timezone.now)
    expense_type = models.CharField(max_length=20, choices=ExpenseType.choices)
    subcategory = models.ForeignKey(ExpenseSubcategory, on_delete=models.PROTECT, related_name='expenses', null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_to = models.CharField(max_length=255)
    payment_mode = models.CharField(max_length=20, choices=PaymentMode.choices)
    reference_no = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    attachment = models.FileField(upload_to='expenses/attachments/', blank=True, null=True)
    
    approval_status = models.CharField(max_length=20, choices=ApprovalStatus.choices, default=ApprovalStatus.DRAFT)
    entered_by = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name='entered_expenses')
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_expenses')
    approval_timestamp = models.DateTimeField(null=True, blank=True)
    
    posting_status = models.CharField(max_length=20, choices=PostingStatus.choices, default=PostingStatus.UNPOSTED)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'expenses'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.expense_type} - {self.amount} ({self.date})"
