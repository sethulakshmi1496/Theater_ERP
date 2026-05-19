from django.db import models
from decimal import Decimal

class DistrictDCRReport(models.Model):
    class Status(models.TextChoices):
        PARSED = 'PARSED', 'Parsed'
        VALIDATED = 'VALIDATED', 'Validated'
        VARIANCE_FOUND = 'VARIANCE_FOUND', 'Variance Found'
        APPROVED = 'APPROVED', 'Approved'
        POSTED = 'POSTED', 'Posted'

    # ── Tenant Foundation ──────────────────────────────────────────────────
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.PROTECT,
        null=True, blank=True, related_name='dcr_reports'
    )
    # ── End Tenant Foundation ──────────────────────────────────────────────

    report_date = models.DateField()
    movie_title = models.CharField(max_length=255)
    screen_name = models.CharField(max_length=100)
    show_time = models.TimeField(null=True, blank=True)

    # File and parsing
    raw_pdf = models.FileField(upload_to='dcr_pdfs/%Y/%m/', null=True, blank=True)
    parser_version = models.CharField(max_length=50, default='1.0')
    confidence_score = models.FloatField(default=1.0)
    raw_text_dump = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PARSED)
    
    # ── Raw Parsed Values (from PDF) ──────────────────────────────────────
    parsed_gross_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    parsed_occupancy = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Parsed occupancy percentage or count")
    
    parsed_gst = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    parsed_etax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    parsed_cess = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    parsed_nett_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    parsed_distributor_share = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    parsed_exhibitor_share = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # ── Mismatch and Reprocessing ──────────────────────────────────────────
    mismatch_flag = models.BooleanField(default=False)
    review_status = models.CharField(
        max_length=30,
        choices=[('PENDING', 'Pending'), ('UNDER_REVIEW', 'Under Review'), ('RESOLVED', 'Resolved')],
        default='PENDING'
    )
    reviewer_note = models.TextField(blank=True)
    raw_archive_link = models.CharField(max_length=500, blank=True)
    reprocess_count = models.IntegerField(default=0)
    posting_status = models.CharField(
        max_length=30,
        choices=[('DRAFT', 'Draft'), ('POSTED', 'Posted'), ('FILM_FINANCE_PUSHED', 'Film Finance Pushed')],
        default='DRAFT'
    )

    # ── Computed Expected Values (System math) ────────────────────────────
    computed_gross_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    computed_nett_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    computed_distributor_share = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    computed_exhibitor_share = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    distributor_share_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=50.00, help_text='Expected share ratio e.g., 50.0')

    uploaded_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='dcr_uploads')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        app_label = 'integrations'
        ordering = ['-report_date', '-created_at']

    def __str__(self):
        return f"DCR: {self.movie_title} ({self.report_date}) - {self.status}"


class DCRTicketClass(models.Model):
    report = models.ForeignKey(DistrictDCRReport, on_delete=models.CASCADE, related_name='ticket_classes')
    ticket_class_name = models.CharField(max_length=100) # Platinum, Gold, Silver
    ticket_count = models.PositiveIntegerField(default=0)
    ticket_rate = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    # The total for this row in PDF
    parsed_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        app_label = 'integrations'

    def __str__(self):
        return f"{self.ticket_class_name}: {self.ticket_count} @ ₹{self.ticket_rate}"


class DCRDiscrepancy(models.Model):
    class Type(models.TextChoices):
        GROSS_MISMATCH = 'GROSS_MISMATCH', 'Gross Mismatch'
        TAX_MISMATCH = 'TAX_MISMATCH', 'Tax Mismatch'
        NETT_MISMATCH = 'NETT_MISMATCH', 'Nett Mismatch'
        SPLIT_MISMATCH = 'SPLIT_MISMATCH', 'Split Mismatch'
        MISSING_FIELDS = 'MISSING_FIELDS', 'Missing Fields'

    report = models.ForeignKey(DistrictDCRReport, on_delete=models.CASCADE, related_name='discrepancies')
    discrepancy_type = models.CharField(max_length=50, choices=Type.choices)
    description = models.TextField()
    variance_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        app_label = 'integrations'

    def __str__(self):
        return f"{self.discrepancy_type} for {self.report}"


class IntegrationConnector(models.Model):
    class ConnectorName(models.TextChoices):
        DISTRICT      = 'DISTRICT',      'District DCR'
        BOOKMYSHOW    = 'BOOKMYSHOW',    'BookMyShow Ticketing'
        PETPOOJA      = 'PETPOOJA',      'Petpooja POS'
        HR_APP        = 'HR_APP',        'External HR App'
        TEAMS         = 'TEAMS',         'Microsoft Teams Alerts'
        PERPLEXITY    = 'PERPLEXITY',    'Perplexity AI Analytics'

    class Status(models.TextChoices):
        ACTIVE   = 'ACTIVE',   'Active / Healthy'
        INACTIVE = 'INACTIVE', 'Inactive'
        ERROR    = 'ERROR',    'Error'
        SYNCING  = 'SYNCING',  'Syncing'
        PAUSED   = 'PAUSED',   'Paused'

    class AuthType(models.TextChoices):
        API_KEY      = 'API_KEY',      'API Key'
        OAUTH2       = 'OAUTH2',       'OAuth 2.0'
        BEARER_TOKEN = 'BEARER_TOKEN', 'Bearer Token'
        BASIC        = 'BASIC',        'Basic Auth'
        CREDENTIALS  = 'CREDENTIALS',  'Username / Password'

    class SyncFrequency(models.TextChoices):
        REAL_TIME = 'REAL_TIME', 'Real-time'
        HOURLY    = 'HOURLY',    'Hourly'
        DAILY     = 'DAILY',     'Daily'
        WEEKLY    = 'WEEKLY',    'Weekly'
        MANUAL    = 'MANUAL',    'Manual'

    tenant            = models.ForeignKey('tenants.Tenant', on_delete=models.PROTECT, related_name='connectors')
    connector_name    = models.CharField(max_length=30, choices=ConnectorName.choices)
    status            = models.CharField(max_length=15, choices=Status.choices, default=Status.INACTIVE)
    auth_type         = models.CharField(max_length=20, choices=AuthType.choices, default=AuthType.API_KEY)
    sync_frequency    = models.CharField(max_length=15, choices=SyncFrequency.choices, default=SyncFrequency.DAILY)
    
    last_sync         = models.DateTimeField(null=True, blank=True)
    last_error        = models.TextField(blank=True)
    test_conn_result  = models.TextField(blank=True, verbose_name='Test Connection Result')
    
    # Store credentials in a JSON field (e.g. key, secret, url)
    credentials_json  = models.JSONField(default=dict, blank=True, help_text="Store API keys, URLs, and token info securely")
    is_active         = models.BooleanField(default=False, verbose_name='Activation Status')

    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'integrations'
        unique_together = ('tenant', 'connector_name')
        ordering = ['connector_name']

    def __str__(self):
        return f"{self.get_connector_name_display()} - {self.get_status_display()}"

    @property
    def masked_credentials(self):
        """Returns a credentials dictionary with sensitive values masked."""
        masked = {}
        if not self.credentials_json:
            return masked
        for k, v in self.credentials_json.items():
            if any(term in k.lower() for term in ['key', 'secret', 'password', 'token']):
                val_str = str(v)
                if len(val_str) > 8:
                    masked[k] = val_str[:4] + "****" + val_str[-4:]
                else:
                    masked[k] = "****"
            else:
                masked[k] = v
        return masked

class PetpoojaItemMap(models.Model):
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.PROTECT, related_name='petpooja_item_maps')
    external_item_id = models.CharField(max_length=100)
    item_name = models.CharField(max_length=200)
    sku = models.CharField(max_length=100, blank=True)
    category = models.CharField(max_length=100, blank=True)
    sub_category = models.CharField(max_length=100, blank=True)
    unit = models.CharField(max_length=50, blank=True)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_rule = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    in_stock = models.BooleanField(default=True)
    
    last_synced_at = models.DateTimeField(auto_now=True)
    is_mapped = models.BooleanField(default=False)
    aec_item = models.ForeignKey('revenue.CanteenItem', on_delete=models.SET_NULL, null=True, blank=True, related_name='petpooja_mappings')
    
    class Meta:
        app_label = 'integrations'
        unique_together = ('tenant', 'external_item_id')

class PetpoojaSalesBill(models.Model):
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.PROTECT, related_name='petpooja_bills')
    business_date = models.DateField()
    bill_datetime = models.DateTimeField()
    bill_number = models.CharField(max_length=100)
    external_order_id = models.CharField(max_length=100)
    shift = models.CharField(max_length=50, blank=True)
    counter = models.CharField(max_length=100, blank=True)
    
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_mode = models.CharField(max_length=100, blank=True)
    
    is_cancelled = models.BooleanField(default=False)
    sync_timestamp = models.DateTimeField(auto_now_add=True)
    is_imported_to_aec = models.BooleanField(default=False)

    class Meta:
        app_label = 'integrations'
        unique_together = ('tenant', 'external_order_id')

class PetpoojaSalesLineItem(models.Model):
    bill = models.ForeignKey(PetpoojaSalesBill, on_delete=models.CASCADE, related_name='line_items')
    item_name = models.CharField(max_length=200)
    external_item_id = models.CharField(max_length=100)
    category = models.CharField(max_length=100, blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        app_label = 'integrations'

class PetpoojaSyncJob(models.Model):
    class SyncType(models.TextChoices):
        ITEM_SYNC = 'ITEM_SYNC', 'Item Sync'
        SALES_SYNC = 'SALES_SYNC', 'Sales Sync'
    
    class Status(models.TextChoices):
        RUNNING = 'RUNNING', 'Running'
        SUCCESS = 'SUCCESS', 'Success'
        FAILED = 'FAILED', 'Failed'
        PARTIAL = 'PARTIAL', 'Partial Success'

    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.PROTECT, related_name='petpooja_sync_jobs')
    sync_type = models.CharField(max_length=20, choices=SyncType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RUNNING)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    records_processed = models.IntegerField(default=0)
    records_failed = models.IntegerField(default=0)
    error_log = models.TextField(blank=True)
    
    class Meta:
        app_label = 'integrations'

class PetpoojaFailedSync(models.Model):
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.PROTECT)
    job = models.ForeignKey(PetpoojaSyncJob, on_delete=models.CASCADE)
    external_id = models.CharField(max_length=100)
    record_type = models.CharField(max_length=50) # ITEM or BILL
    payload = models.JSONField(default=dict)
    error_reason = models.TextField()
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'integrations'

