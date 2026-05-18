"""AEC Cinemas – Finance Models (Film Finance & Distributor Workspace)"""

from django.db import models
from decimal import Decimal

class Distributor(models.Model):
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.PROTECT, related_name='distributors', null=True, blank=True
    )
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    gst_id = models.CharField(max_length=50, blank=True, help_text="GST/Tax ID")
    address = models.TextField(blank=True)
    default_settlement_terms = models.TextField(blank=True)
    default_share_logic = models.TextField(blank=True)
    bank_details_reference = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    attached_document = models.FileField(upload_to='finance/distributors/documents/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'finance'
        unique_together = ('tenant', 'name')
        ordering = ['name']

    def __str__(self):
        return self.name

class FilmContract(models.Model):
    class ContractType(models.TextChoices):
        PERCENTAGE = 'PERCENTAGE', 'Percentage Only'
        MG = 'MG', 'Minimum Guarantee (MG)'
        FIXED = 'FIXED', 'Fixed Hire'

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        ACTIVE = 'ACTIVE', 'Active'
        SETTLED = 'SETTLED', 'Settled'
        CLOSED = 'CLOSED', 'Closed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    class SettlementFrequency(models.TextChoices):
        WEEKLY = 'WEEKLY', 'Weekly'
        FORTNIGHTLY = 'FORTNIGHTLY', 'Fortnightly'
        MONTHLY = 'MONTHLY', 'Monthly'
        END_OF_RUN = 'END_OF_RUN', 'End of Run'

    class ApprovalStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PENDING = 'PENDING', 'Pending Approval'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.PROTECT, related_name='film_contracts', null=True, blank=True
    )
    distributor = models.ForeignKey(Distributor, on_delete=models.PROTECT, related_name='contracts')
    movie = models.ForeignKey('screens.Movie', on_delete=models.PROTECT, related_name='contracts')
    contract_type = models.CharField(max_length=20, choices=ContractType.choices, default=ContractType.PERCENTAGE)
    
    mg_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Minimum Guarantee")
    fixed_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Fixed Hire")
    terms = models.TextField(blank=True)
    
    revenue_share_rule = models.TextField(blank=True, help_text="e.g. Week 1: 50%, Week 2: 40%")
    mg_recovery_logic = models.TextField(blank=True, help_text="e.g. Recovered from Week 1 net")
    settlement_frequency = models.CharField(max_length=20, choices=SettlementFrequency.choices, default=SettlementFrequency.WEEKLY)
    holdback_rule = models.TextField(blank=True, help_text="e.g. 10% held until final DCR")
    contract_attachment = models.FileField(upload_to='finance/contracts/', blank=True, null=True)
    approval_status = models.CharField(max_length=20, choices=ApprovalStatus.choices, default=ApprovalStatus.DRAFT)
    notes = models.TextField(blank=True)
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    entered_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        app_label = 'finance'
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.movie.title} - {self.distributor.name} ({self.contract_type})"

class FilmAdvance(models.Model):
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.PROTECT, null=True, blank=True, related_name='film_advances'
    )
    movie = models.ForeignKey('screens.Movie', on_delete=models.PROTECT, related_name='advances')
    
    # Newly linked to Contract
    contract = models.ForeignKey(FilmContract, on_delete=models.CASCADE, related_name='advances', null=True, blank=True)
    distributor_name = models.CharField(max_length=200, blank=True) # Kept for legacy
    
    advance_amount = models.DecimalField(max_digits=12, decimal_places=2)
    release_date = models.DateField()
    screen = models.ForeignKey('screens.Screen', on_delete=models.SET_NULL, null=True, blank=True)
    paid_date = models.DateField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    entered_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'finance'
        ordering = ['-release_date']

    def __str__(self):
        d_name = self.contract.distributor.name if self.contract else self.distributor_name
        return f"{self.movie.title} – {d_name} – ₹{self.advance_amount}"

class DistributorShare(models.Model):
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.PROTECT, null=True, blank=True, related_name='distributor_shares'
    )
    show = models.ForeignKey('screens.Show', on_delete=models.PROTECT, related_name='distributor_shares')
    
    # Newly linked to Contract
    contract = models.ForeignKey(FilmContract, on_delete=models.CASCADE, related_name='shares', null=True, blank=True)
    distributor_name = models.CharField(max_length=200, blank=True) # Kept for legacy
    
    gross_collection = models.DecimalField(max_digits=12, decimal_places=2)
    share_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    share_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    week_number = models.PositiveSmallIntegerField(default=1, help_text='Week of release (share % varies)')
    is_settled = models.BooleanField(default=False)
    settlement_date = models.DateField(null=True, blank=True)
    entered_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'finance'
        ordering = ['-show__show_date']

    def save(self, *args, **kwargs):
        self.share_amount = self.gross_collection * self.share_percentage / 100
        super().save(*args, **kwargs)

    def __str__(self):
        d_name = self.contract.distributor.name if self.contract else self.distributor_name
        return f"{self.show} – {d_name} – {self.share_percentage}% – ₹{self.share_amount}"

class Settlement(models.Model):
    class Status(models.TextChoices):
        GENERATED = 'GENERATED', 'Generated'
        VALIDATED = 'VALIDATED', 'Validated'
        APPROVED = 'APPROVED', 'Approved'
        PAID = 'PAID', 'Paid'

    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.PROTECT, related_name='settlements', null=True, blank=True)
    contract = models.ForeignKey(FilmContract, on_delete=models.PROTECT, related_name='settlements')
    start_date = models.DateField()
    end_date = models.DateField()
    
    total_gross = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_nett = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_share = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    total_advance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    mg_recouped = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_adjustments = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    net_payable = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.GENERATED)
    generated_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='generated_settlements')
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_settlements')
    approval_timestamp = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'finance'
        ordering = ['-created_at']

    def __str__(self):
        return f"Settlement {self.contract.movie.title} ({self.start_date} to {self.end_date})"

class DistributorStatement(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SENT = 'SENT', 'Sent'
        ARCHIVED = 'ARCHIVED', 'Archived'

    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.PROTECT, related_name='distributor_statements', null=True, blank=True)
    distributor = models.ForeignKey(Distributor, on_delete=models.PROTECT, related_name='statements')
    
    period_start = models.DateField()
    period_end = models.DateField()
    
    movies_included = models.TextField(blank=True)
    
    total_gross = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_share = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_adjustments = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_payable = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    statement_file = models.FileField(upload_to='finance/statements/', null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    sent_timestamp = models.DateTimeField(null=True, blank=True)
    
    settlements = models.ManyToManyField(Settlement, related_name='statements', blank=True)
    
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        app_label = 'finance'
        ordering = ['-generated_at']

    def __str__(self):
        return f"Statement for {self.distributor.name} ({self.period_start} - {self.period_end})"
