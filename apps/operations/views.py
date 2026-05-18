"""AEC Cinemas – Operations Views
Electricity, Generator, Lamp – with Predictive Defaults & Audit Shield
"""

from rest_framework import serializers, viewsets, filters, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import (
    ElectricityReading, GeneratorLog, LampLog, LampInventory,
    UtilityMeter, UtilityConfig, UtilityReading,
    AssetCategory, AssetTemplate, TenantAsset, AssetLog,
    FaultTicket, PMSchedule, WorkOrder, AMCContract, ServiceHistory, WaterLog, OperationalAlert
)
from apps.accounts.permissions import IsStaffOrAbove, IsMDOrAdmin
from apps.tenants.mixins import TenantAuditMixin, TenantSafeMixin


# ─── SERIALIZERS ──────────────────────────────────────────────────────────────

class UtilityMeterSerializer(serializers.ModelSerializer):
    class Meta:
        model = UtilityMeter
        fields = '__all__'


class UtilityConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = UtilityConfig
        fields = '__all__'


class UtilityReadingSerializer(serializers.ModelSerializer):
    meter_name = serializers.CharField(source='meter.name', read_only=True)
    meter_type = serializers.CharField(source='meter.meter_type', read_only=True)
    unit_label = serializers.CharField(source='meter.unit_label', read_only=True)
    utility_type_display = serializers.CharField(source='get_utility_type_display', read_only=True)
    anomaly_status_display = serializers.CharField(source='get_anomaly_status_display', read_only=True)
    posting_status_display = serializers.CharField(source='get_posting_status_display', read_only=True)

    class Meta:
        model = UtilityReading
        fields = [
            'id', 'meter', 'meter_name', 'meter_type', 'unit_label', 'utility_type', 'utility_type_display',
            'reading_date', 'opening', 'closing', 'initial_reading', 'final_reading', 'consumption', 
            'billed_units', 'total_cost', 'bill_amount', 'bill_attachment', 'trend_variance',
            'anomaly_status', 'anomaly_status_display', 'review_note', 'posting_status', 'posting_status_display',
            'override_reason', 'entered_by', 'notes', 'created_at'
        ]
        read_only_fields = ['consumption', 'billed_units', 'total_cost', 'trend_variance', 'created_at']

    def validate(self, data):
        # Support fallback mapping for opening / closing
        if 'opening' not in data and 'initial_reading' in data:
            data['opening'] = data['initial_reading']
        if 'closing' not in data and 'final_reading' in data:
            data['closing'] = data['final_reading']

        open_val = data.get('opening', 0)
        close_val = data.get('closing', 0)
        
        if open_val is not None and close_val is not None and close_val < open_val:
            raise serializers.ValidationError({"closing": "Closing reading cannot be less than opening reading."})
        
        meter = data.get('meter')
        date = data.get('reading_date')
        if meter and date and not self.instance:
            prev = UtilityReading.objects.filter(meter=meter, reading_date__lt=date).order_by('-reading_date').first()
            if prev and open_val != prev.closing and not data.get('override_reason'):
                raise serializers.ValidationError({
                    "override_reason": f"Opening reading ({open_val}) differs from previous closing reading ({prev.closing}). Override reason is required."
                })
        return data



class GeneratorLogSerializer(serializers.ModelSerializer):
    variance_status_display = serializers.CharField(source='get_variance_status_display', read_only=True)
    entered_by_username      = serializers.CharField(source='entered_by.username', read_only=True)

    class Meta:
        model = GeneratorLog
        fields = [
            'id', 'tenant', 'date', 'opening_hours', 'closing_hours', 'runtime', 'hours_run',
            'opening_diesel_stock', 'refill_qty', 'refill_vendor', 'refill_cost',
            'consumed_qty', 'closing_diesel_stock', 'consumption', 'diesel_added', 'diesel_rate', 'diesel_cost',
            'outage_tag', 'attachment', 'variance_status', 'variance_status_display', 'entered_by', 'entered_by_username', 'notes', 'created_at'
        ]
        read_only_fields = [
            'tenant', 'runtime', 'hours_run', 'closing_diesel_stock', 'consumption', 'diesel_added', 'diesel_rate', 'diesel_cost', 'created_at'
        ]



class LampInventorySerializer(serializers.ModelSerializer):
    screen_name             = serializers.CharField(source='screen.name', read_only=True)
    lamp_type_display       = serializers.CharField(source='get_lamp_type_display', read_only=True)
    status_display          = serializers.CharField(source='get_status_display', read_only=True)
    hours_used              = serializers.ReadOnlyField()
    remaining_hours         = serializers.ReadOnlyField()
    depreciation_per_hour   = serializers.ReadOnlyField()

    class Meta:
        model = LampInventory
        fields = '__all__'
        read_only_fields = ['opening_hours', 'closing_hours', 'working_hours', 'balance_life', 'created_at']



class LampLogSerializer(serializers.ModelSerializer):
    screen_name = serializers.CharField(source='screen.name', read_only=True)
    lamp_serial = serializers.CharField(source='lamp.serial_number', read_only=True)
    lamp_alert = serializers.SerializerMethodField()

    class Meta:
        model = LampLog
        fields = ['id', 'screen', 'screen_name', 'lamp', 'lamp_serial', 'date',
                  'opening_hours', 'working_hours', 'closing_hours', 'balance',
                  'lamp_alert', 'entered_by', 'created_at']
        read_only_fields = ['working_hours', 'balance', 'lamp', 'created_at']

    def get_lamp_alert(self, obj):
        return obj.screen.lamp_alert


class AssetCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetCategory
        fields = '__all__'


class AssetTemplateSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source='category.label', read_only=True)
    
    class Meta:
        model = AssetTemplate
        fields = '__all__'


class TenantAssetSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.__str__', read_only=True)
    category_key = serializers.CharField(source='template.category.key', read_only=True)
    screen_name = serializers.CharField(source='screen.name', read_only=True)
    remaining_hours = serializers.ReadOnlyField()
    life_percentage = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = TenantAsset
        fields = [
            'id', 'tenant', 'template', 'template_name', 'category_key', 'screen', 'screen_name',
            'asset_id', 'asset_name', 'location', 'serial_number', 'purchase_date', 'vendor',
            'warranty', 'status', 'status_display', 'service_due_date', 'notes',
            'installed_date', 'current_hours', 'alert_threshold_hours', 'life_percentage', 'remaining_hours', 'is_active'
        ]
        read_only_fields = ['tenant', 'asset_id', 'current_hours', 'life_percentage', 'remaining_hours']



class AssetLogSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source='asset.__str__', read_only=True)
    override = serializers.BooleanField(write_only=True, required=False)
    
    class Meta:
        model = AssetLog
        fields = '__all__'
        read_only_fields = ['delta', 'entered_by', 'created_at']

    def validate(self, data):
        opening = data.get('opening_value')
        closing = data.get('closing_value')
        if opening is not None and closing is not None and closing < opening:
            raise serializers.ValidationError({"closing_value": "Closing value cannot be less than opening value."})
        
        asset = data.get('asset')
        if asset and asset.template.rated_life_hours and asset.template.category.tracks_hours:
            delta = closing - opening
            if asset.remaining_hours - delta < 0 and not data.get('override'):
                raise serializers.ValidationError({
                    "non_field_errors": "This log exceeds the asset's rated life. Provide 'override=true' to force."
                })
        return data


# ─── VIEWSETS ─────────────────────────────────────────────────────────────────

# AuditShieldMixin is now provided by apps.tenants.mixins.TenantAuditMixin
# Keeping this alias here to avoid breaking any direct imports from other modules.
AuditShieldMixin = TenantAuditMixin


class UtilityMeterViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = UtilityMeter.objects.all()
    serializer_class = UtilityMeterSerializer
    filterset_fields = ['meter_type', 'is_active']
    permission_classes = [IsMDOrAdmin]


class UtilityConfigViewSet(viewsets.ModelViewSet):
    # This doesn't have a tenant field directly, but we can filter by meter__tenant
    queryset = UtilityConfig.objects.all()
    serializer_class = UtilityConfigSerializer
    filterset_fields = ['meter']
    permission_classes = [IsMDOrAdmin]
    
    def get_queryset(self):
        qs = super().get_queryset()
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            return qs.filter(meter__tenant=tenant)
        return qs


class UtilityReadingViewSet(TenantAuditMixin, viewsets.ModelViewSet):
    queryset = UtilityReading.objects.select_related('meter', 'entered_by').order_by('-reading_date')
    serializer_class = UtilityReadingSerializer
    filterset_fields = ['meter', 'reading_date', 'utility_type', 'anomaly_status', 'posting_status']
    permission_classes = [IsStaffOrAbove]

    def get_queryset(self):
        qs = super().get_queryset()
        from apps.tenants.mixins import get_tenant_from_request
        tenant = get_tenant_from_request(self.request)
        if tenant:
            return qs.filter(meter__tenant=tenant)
        return qs.none()

    def perform_create(self, serializer):
        from apps.tenants.mixins import get_tenant_from_request
        from rest_framework.exceptions import PermissionDenied
        tenant = get_tenant_from_request(self.request)
        meter = serializer.validated_data.get('meter')
        if meter and meter.tenant_id != tenant.id:
            raise PermissionDenied("You do not have permission to add readings for this meter.")
        
        # Determine utility type from meter
        u_type = UtilityReading.UtilityType.ELECTRICITY
        if meter.meter_type == 'WATER':
            u_type = UtilityReading.UtilityType.WATER
        elif meter.meter_type == 'GENERATOR':
            u_type = UtilityReading.UtilityType.GENERATOR

        serializer.save(
            entered_by=self.request.user,
            utility_type=u_type
        )

    @action(detail=False, methods=['get'], url_path='predictive-defaults')
    def predictive_defaults(self, request):
        """
        Returns the most recent closing reading as today's opening reading for each active meter.
        """
        defaults = {}
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({})

        meters = UtilityMeter.objects.filter(tenant=tenant, is_active=True)
        for meter in meters:
            prev = UtilityReading.objects.filter(meter=meter).order_by('-reading_date').first()
            if prev:
                defaults[meter.id] = {
                    'meter_name': meter.name,
                    'suggested_initial_reading': float(prev.closing),
                    'previous_date': str(prev.reading_date),
                    'previous_final_reading': float(prev.closing),
                }
            else:
                defaults[meter.id] = {
                    'meter_name': meter.name,
                    'suggested_initial_reading': None,
                    'message': 'No previous reading found. Enter manually.'
                }
        return Response(defaults)

    # ── Action: Upload Bill ───────────────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='upload-bill')
    def upload_bill(self, request, pk=None):
        reading = self.get_object()
        file_obj = request.FILES.get('bill')
        amount_val = request.data.get('bill_amount')

        if file_obj:
            reading.bill_attachment = file_obj
        if amount_val is not None:
            reading.bill_amount = amount_val
        
        reading.posting_status = UtilityReading.PostingStatus.POSTED
        reading.save()

        # Direct integration to Expense Register if posted
        from apps.expenses.models import ExpenseEntry, ExpenseCategory
        tenant = reading.meter.tenant
        
        # Get or create Utility Expense category
        cat, _ = ExpenseCategory.objects.get_or_create(
            tenant=tenant,
            name='Utility Bills',
            defaults={'key_code': 'UTIL'}
        )

        ExpenseEntry.objects.create(
            tenant=tenant,
            category=cat,
            date=reading.reading_date,
            amount=reading.bill_amount,
            description=f"Utility bill posted for {reading.get_utility_type_display()} Meter: {reading.meter.name}",
            posting_status='APPROVED',
            payment_status='UNPAID',
            reference_code=f"UTIL-READ-{reading.id}"
        )

        return Response(UtilityReadingSerializer(reading).data)

    # ── Action: Compare to Baseline ───────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='compare-baseline')
    def compare_baseline(self, request, pk=None):
        reading = self.get_object()
        
        # Calculate historical 30-day baseline consumption for this meter
        from django.db.models import Avg
        from datetime import timedelta
        
        start_dt = reading.reading_date - timedelta(days=30)
        avg_cons = UtilityReading.objects.filter(
            meter=reading.meter,
            reading_date__gte=start_dt,
            reading_date__lt=reading.reading_date
        ).aggregate(a=Avg('consumption'))['a'] or 1.0
        
        # Calculate percentage variance
        current = float(reading.consumption)
        baseline = float(avg_cons)
        variance = 0.0
        if baseline > 0:
            variance = round(((current - baseline) / baseline) * 100.0, 2)
        
        reading.trend_variance = variance
        if variance >= 30.0:
            reading.anomaly_status = UtilityReading.AnomalyStatus.WARNING
        if variance >= 50.0:
            reading.anomaly_status = UtilityReading.AnomalyStatus.ANOMALY
            
        reading.save(update_fields=['trend_variance', 'anomaly_status'])
        
        return Response({
            'current_consumption': current,
            'baseline_avg_30d': baseline,
            'trend_variance_percentage': variance,
            'anomaly_status': reading.anomaly_status
        })

    # ── Action: Mark Anomaly ──────────────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='mark-anomaly')
    def mark_anomaly(self, request, pk=None):
        reading = self.get_object()
        review = request.data.get('review_note', 'Manual alert triggered by operator.')
        
        reading.anomaly_status = UtilityReading.AnomalyStatus.ANOMALY
        reading.review_note = review
        reading.save(update_fields=['anomaly_status', 'review_note'])

        # Register alert inside Alert Center
        from apps.operations.models import OperationalAlert
        OperationalAlert.objects.create(
            tenant=reading.meter.tenant,
            alert_type=OperationalAlert.AlertType.UTILITY_ANOMALY,
            source_module='Utilities',
            severity=OperationalAlert.Severity.CRITICAL,
            reference_record=f"UtilityReading-{reading.id}",
            status=OperationalAlert.Status.TRIGGERED,
            resolution_note=f"Utility critical alert. Consumption: {reading.consumption}. Review note: {review}"
        )

        return Response(UtilityReadingSerializer(reading).data)

    # ── Action: Open Drill-down (Show Analytics & Charge Efficiency) ──────────
    @action(detail=True, methods=['get'], url_path='drill-down')
    def drill_down(self, request, pk=None):
        reading = self.get_object()
        tenant = reading.meter.tenant
        
        # Calculate total shows hosted on this date to support unit-per-show comparisons
        from apps.screens.models import Show
        shows_count = Show.objects.filter(
            screen__tenant=tenant,
            show_date=reading.reading_date,
            status='SCHEDULED'
        ).count() or 1
        
        units_per_show = round(float(reading.consumption) / float(shows_count), 2)
        cost_per_show = round(float(reading.bill_amount) / float(shows_count), 2)

        return Response({
            'reading_date': reading.reading_date,
            'utility_type': reading.utility_type,
            'meter_name': reading.meter.name,
            'total_consumption': float(reading.consumption),
            'shows_hosted_today': shows_count,
            'unit_consumption_per_show': units_per_show,
            'cost_per_show': cost_per_show,
            'trend_variance': float(reading.trend_variance),
            'anomaly_status': reading.anomaly_status
        })

    # ── Action: Export Utility Register ───────────────────────────────────────
    @action(detail=False, methods=['get'], url_path='export-register')
    def export_register(self, request):
        import csv
        from django.http import HttpResponse
        qs = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="utility_readings_register.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'Utility Type', 'Meter Name', 'Reading Date', 'Opening', 'Closing',
            'Consumption', 'Bill Amount', 'Trend Variance %', 'Anomaly Status', 'Posting Status'
        ])
        for r in qs:
            writer.writerow([
                r.get_utility_type_display(), r.meter.name, r.reading_date,
                r.opening, r.closing, r.consumption, r.bill_amount,
                r.trend_variance, r.get_anomaly_status_display(), r.get_posting_status_display()
            ])
        return response



class GeneratorLogViewSet(TenantAuditMixin, viewsets.ModelViewSet):
    queryset = GeneratorLog.objects.select_related('entered_by').order_by('-date')
    serializer_class = GeneratorLogSerializer
    filterset_fields = ['date', 'variance_status']
    permission_classes = [IsStaffOrAbove]

    def get_queryset(self):
        qs = super().get_queryset()
        from apps.tenants.mixins import get_tenant_from_request
        tenant = get_tenant_from_request(self.request)
        if tenant:
            return qs.filter(tenant=tenant)
        return qs.none()

    def perform_create(self, serializer):
        from apps.tenants.mixins import get_tenant_from_request
        tenant = get_tenant_from_request(self.request)
        
        # Pull predictive defaults: Opening Diesel Stock is yesterday's closing
        prev = GeneratorLog.objects.filter(tenant=tenant).order_by('-date').first()
        opening_stock = prev.closing_diesel_stock if prev else 0
        
        serializer.save(
            tenant=tenant,
            entered_by=self.request.user,
            opening_diesel_stock=opening_stock
        )

    # ── Action: Log Runtime ───────────────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='log-runtime')
    def log_runtime(self, request, pk=None):
        log = self.get_object()
        open_h = request.data.get('opening_hours')
        close_h = request.data.get('closing_hours')

        if open_h is not None:
            log.opening_hours = open_h
        if close_h is not None:
            log.closing_hours = close_h
            
        log.save()
        return Response(GeneratorLogSerializer(log).data)

    # ── Action: Add Refill ────────────────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='add-refill')
    def add_refill(self, request, pk=None):
        log = self.get_object()
        qty = request.data.get('refill_qty', 0)
        vendor = request.data.get('refill_vendor', '')
        cost = request.data.get('refill_cost', 0)

        log.refill_qty = qty
        log.refill_vendor = vendor
        log.refill_cost = cost
        log.save()

        return Response(GeneratorLogSerializer(log).data)

    # ── Action: Reconcile Diesel Inventory ────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='reconcile')
    def reconcile(self, request, pk=None):
        log = self.get_object()
        consumed = request.data.get('consumed_qty')

        if consumed is not None:
            log.consumed_qty = consumed
            
        # Calculate variance burn rate
        # Baseline burn rate = 3.5 liters per hour
        baseline_rate = 3.5
        run = float(log.runtime)
        actual_qty = float(log.consumed_qty)
        expected_qty = run * baseline_rate
        
        if run > 0:
            variance_pct = ((actual_qty - expected_qty) / expected_qty) * 100.0 if expected_qty > 0 else 0
            if variance_pct >= 25.0:
                log.variance_status = GeneratorLog.VarianceStatus.HIGH_BURN
            elif variance_pct <= -25.0:
                log.variance_status = GeneratorLog.VarianceStatus.LOW_BURN
            else:
                log.variance_status = GeneratorLog.VarianceStatus.NORMAL
        
        log.save()
        return Response(GeneratorLogSerializer(log).data)

    # ── Action: Upload Refill Bill ────────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='upload-bill')
    def upload_bill(self, request, pk=None):
        log = self.get_object()
        file_obj = request.FILES.get('attachment')
        cost_val = request.data.get('refill_cost')

        if file_obj:
            log.attachment = file_obj
        if cost_val is not None:
            log.refill_cost = cost_val
        log.save()

        # Connect direct expense entry
        if log.refill_cost > 0:
            from apps.expenses.models import ExpenseEntry, ExpenseCategory
            cat, _ = ExpenseCategory.objects.get_or_create(
                tenant=log.tenant,
                name='Generator Fuel',
                defaults={'key_code': 'FUEL'}
            )

            ExpenseEntry.objects.create(
                tenant=log.tenant,
                category=cat,
                date=log.date,
                amount=log.refill_cost,
                description=f"Refill bill posted. Vendor: {log.refill_vendor}. Qty: {log.refill_qty}L",
                posting_status='APPROVED',
                payment_status='UNPAID',
                reference_code=f"GEN-REFILL-{log.id}"
            )

        return Response(GeneratorLogSerializer(log).data)

    # ── Action: Raise Variance Alert ──────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='raise-alert')
    def raise_alert(self, request, pk=None):
        log = self.get_object()
        log.variance_status = GeneratorLog.VarianceStatus.HIGH_BURN
        log.save()

        # Push to Alert Center
        from apps.operations.models import OperationalAlert
        OperationalAlert.objects.create(
            tenant=log.tenant,
            alert_type=OperationalAlert.AlertType.GENERATOR_VARIANCE,
            source_module='Generator logs',
            severity=OperationalAlert.Severity.WARNING,
            reference_record=f"GeneratorLog-{log.id}",
            status=OperationalAlert.Status.TRIGGERED,
            resolution_note=f"High fuel burn rate discrepancy detected. Runtime: {log.runtime}h, Diesel consumed: {log.consumed_qty}L."
        )

        return Response({'status': 'Variance alert raised in Alert Center'})

    # ── Action: Export Generator Register ─────────────────────────────────────
    @action(detail=False, methods=['get'], url_path='export-register')
    def export_register(self, request):
        import csv
        from django.http import HttpResponse
        qs = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="generator_fuel_register.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'Date', 'Opening Hours', 'Closing Hours', 'Runtime',
            'Opening Diesel Stock', 'Refill Qty', 'Refill Vendor', 'Refill Cost',
            'Consumed Qty', 'Closing Diesel Stock', 'Outage Tag', 'Variance Status'
        ])
        for g in qs:
            writer.writerow([
                g.date, g.opening_hours, g.closing_hours, g.runtime,
                g.opening_diesel_stock, g.refill_qty, g.refill_vendor, g.refill_cost,
                g.consumed_qty, g.closing_diesel_stock, g.outage_tag, g.get_variance_status_display()
            ])
        return response



class LampInventoryViewSet(viewsets.ModelViewSet):
    """Lamp Lifecycle Registry – Admin/MD manage; Staff can only view."""
    queryset = LampInventory.objects.select_related('screen', 'entered_by').filter(archived_flag=False).order_by('-purchase_date')
    serializer_class = LampInventorySerializer
    filterset_fields = ['screen', 'is_current', 'status', 'lamp_type']
    search_fields = ['serial_number', 'vendor', 'manufacturer']

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'balance_trend', 'history']:
            return [IsStaffOrAbove()]
        return [IsMDOrAdmin()]

    def perform_create(self, serializer):
        # When a new lamp is installed as current, retire the previous one
        screen = serializer.validated_data.get('screen')
        is_current = serializer.validated_data.get('is_current', False)
        if is_current and screen:
            LampInventory.objects.filter(screen=screen, is_current=True).update(
                is_current=False,
                status=LampInventory.Status.REPLACED,
                retired_date=timezone.now().date()
            )
        serializer.save(
            entered_by=self.request.user,
            status=LampInventory.Status.INSTALLED
        )

    # ── Action: Update Hours ──────────────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='update-hours')
    def update_hours(self, request, pk=None):
        lamp = self.get_object()
        open_h = request.data.get('opening_hours')
        close_h = request.data.get('closing_hours')
        log_date = request.data.get('date', str(timezone.now().date()))

        if open_h is None or close_h is None:
            return Response({'error': 'opening_hours and closing_hours are required.'}, status=400)

        # Create the daily LampLog entry which automatically updates the lamp status/hours
        log = LampLog.objects.create(
            screen=lamp.screen,
            lamp=lamp,
            date=log_date,
            opening_hours=open_h,
            closing_hours=close_h,
            entered_by=request.user
        )

        return Response({
            'status': 'Hours updated and log entry recorded.',
            'lamp': LampInventorySerializer(lamp).data,
            'log_entry_id': log.id
        })

    # ── Action: View Balance Trend ────────────────────────────────────────────
    @action(detail=True, methods=['get'], url_path='balance-trend')
    def balance_trend(self, request, pk=None):
        lamp = self.get_object()
        logs = lamp.lamp_logs.order_by('date')
        
        trend = []
        for l in logs:
            trend.append({
                'date': l.date,
                'opening': float(l.opening_hours),
                'closing': float(l.closing_hours),
                'hours_run': float(l.working_hours),
                'remaining_balance_hours': float(l.balance)
            })
            
        return Response({
            'lamp_serial': lamp.serial_number,
            'screen_name': lamp.screen.name,
            'rated_lifespan': float(lamp.rated_lifespan_hours),
            'current_balance_life': float(lamp.balance_life),
            'trend': trend
        })

    # ── Action: Schedule Replacement ──────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='schedule-replacement')
    def schedule_replacement(self, request, pk=None):
        lamp = self.get_object()
        replace_date = request.data.get('replacement_date', str(timezone.now().date()))

        lamp.status = LampInventory.Status.REPLACED
        lamp.retired_date = replace_date
        lamp.is_current = False
        lamp.save(update_fields=['status', 'retired_date', 'is_current'])

        # Register alert inside global Maintenance / Alert Center
        from apps.operations.models import OperationalAlert
        OperationalAlert.objects.create(
            tenant=lamp.screen.tenant,
            alert_type=OperationalAlert.AlertType.LAMP_THRESHOLD,
            source_module='Projection Lamps',
            severity=OperationalAlert.Severity.WARNING,
            reference_record=f"LampInventory-{lamp.id}",
            status=OperationalAlert.Status.RESOLVED, # Marked as resolved because replacement is scheduled
            resolution_note=f"Projection Lamp S/N {lamp.serial_number} scheduled for replacement on {replace_date}."
        )

        return Response(LampInventorySerializer(lamp).data)

    # ── Action: Trigger Threshold Alert ───────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='trigger-threshold-alert')
    def trigger_threshold_alert(self, request, pk=None):
        lamp = self.get_object()
        
        # Manually trigger threshold alarm
        from apps.operations.models import OperationalAlert
        alert, created = OperationalAlert.objects.get_or_create(
            tenant=lamp.screen.tenant,
            alert_type=OperationalAlert.AlertType.LAMP_THRESHOLD,
            source_module='Projection Lamps',
            reference_record=f"LampInventory-{lamp.id}",
            defaults={
                'severity': OperationalAlert.Severity.CRITICAL,
                'status': OperationalAlert.Status.TRIGGERED,
                'resolution_note': f"Manual Threshold Alert triggered for Lamp S/N {lamp.serial_number}. Remaining: {lamp.balance_life}h."
            }
        )

        return Response({
            'status': 'Manual threshold alert processed.',
            'alert_id': alert.id,
            'is_new_alert': created
        })

    # ── Action: Archive Replaced Lamp ─────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='archive')
    def archive_lamp(self, request, pk=None):
        lamp = self.get_object()
        if lamp.status != LampInventory.Status.REPLACED and lamp.is_current:
            return Response({'error': 'Only non-current, replaced projection lamps can be archived.'}, status=400)

        lamp.archived_flag = True
        lamp.status = LampInventory.Status.ARCHIVED
        lamp.save(update_fields=['archived_flag', 'status'])

        return Response({
            'status': 'Lamp archived successfully.',
            'lamp_id': lamp.id,
            'archived': True
        })

    @action(detail=True, methods=['get'], url_path='history')
    def history(self, request, pk=None):
        """Back-trace: all daily lamp logs for this specific lamp."""
        lamp = self.get_object()
        logs = lamp.lamp_logs.order_by('-date')[:90]
        return Response(LampLogSerializer(logs, many=True).data)



class LampLogViewSet(TenantAuditMixin, viewsets.ModelViewSet):
    queryset = LampLog.objects.select_related('screen', 'entered_by', 'lamp').order_by('-date')
    serializer_class = LampLogSerializer
    filterset_fields = ['screen', 'date']
    permission_classes = [IsStaffOrAbove]

    @action(detail=False, methods=['get'], url_path='predictive-defaults')
    def predictive_defaults(self, request):
        """
        Returns the previous day's closing_hours as today's opening_hours for each screen.
        Staff simply confirms or adjusts the pre-filled value.
        """
        from datetime import date, timedelta
        from apps.screens.models import Screen

        yesterday = date.today() - timedelta(days=1)
        defaults = {}
        for screen in Screen.objects.filter(is_active=True):
            prev_log = LampLog.objects.filter(screen=screen, date=yesterday).first()
            defaults[screen.pk] = {
                'screen_name': screen.name,
                'suggested_opening_hours': float(prev_log.closing_hours) if prev_log else float(screen.lamp_balance),
                'previous_date': str(yesterday) if prev_log else None,
                'current_lamp_serial': getattr(
                    LampInventory.objects.filter(screen=screen, is_current=True).first(),
                    'serial_number', None
                ),
            }
        return Response(defaults)


# Service alert helper
def send_lamp_alert(screen):
    """Placeholder – extend to send push notification / email to MD."""
    print(f"[ALERT] {screen.name} lamp balance critically low: {screen.lamp_balance} hrs remaining!")


class AssetCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AssetCategory.objects.all()
    serializer_class = AssetCategorySerializer
    permission_classes = [IsAuthenticated]


class AssetTemplateViewSet(viewsets.ModelViewSet):
    queryset = AssetTemplate.objects.all()
    serializer_class = AssetTemplateSerializer
    filterset_fields = ['category']
    permission_classes = [IsMDOrAdmin]


class TenantAssetViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = TenantAsset.objects.select_related('template__category', 'screen').all()
    serializer_class = TenantAssetSerializer
    filterset_fields = ['is_active', 'template__category', 'screen', 'status', 'asset_id']
    search_fields = ['asset_name', 'asset_id', 'serial_number', 'vendor', 'location']
    permission_classes = [IsStaffOrAbove]

    @action(detail=False, methods=['get'], url_path='alerts')
    def low_life_alerts(self, request):
        """
        Returns all active assets whose remaining life is at or below their
        configured alert_threshold_hours.
        """
        qs = self.get_queryset().filter(is_active=True)
        alerts = []
        for asset in qs:
            if asset.template.rated_life_hours and asset.alert_threshold_hours:
                if asset.remaining_hours is not None and asset.remaining_hours <= asset.alert_threshold_hours:
                    alerts.append(TenantAssetSerializer(asset).data)
        return Response({'count': len(alerts), 'results': alerts})

    # ── Action: Change Status ─────────────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='change-status')
    def change_status(self, request, pk=None):
        asset = self.get_object()
        new_status = request.data.get('status')
        note = request.data.get('note', '')

        if not new_status or new_status not in TenantAsset.StatusChoices.values:
            return Response({'error': f'Valid status is required. Choose from: {TenantAsset.StatusChoices.values}'}, status=400)

        old_status = asset.status
        asset.status = new_status
        if note:
            asset.notes = f"{asset.notes}\n[Status Change] {old_status} -> {new_status}: {note}"
        asset.save(update_fields=['status', 'notes'])

        # Audit Shield entry
        from apps.audit.models import ChangeLog
        ChangeLog.objects.create(
            tenant=asset.tenant,
            table_name='TenantAsset',
            record_id=asset.id,
            action=ChangeLog.ACTION_UPDATE,
            changed_by=request.user,
            changes={'status': new_status, 'reason': note}
        )

        return Response(TenantAssetSerializer(asset).data)

    # ── Action: Open Maintenance Desk ─────────────────────────────────────────
    @action(detail=True, methods=['get'], url_path='maintenance-desk')
    def maintenance_desk(self, request, pk=None):
        asset = self.get_object()
        # Returns redirections for operations desk
        return Response({
            'asset_id': asset.asset_id,
            'asset_name': asset.asset_name,
            'screen_id': asset.screen_id,
            'redirections': {
                'fault_tickets': f"/api/operations/fault-tickets/?asset={asset.id}",
                'preventive_maintenance': f"/api/operations/preventive-maintenance/?asset={asset.id}",
                'warranty_amc': f"/api/operations/warranty-amc/?asset={asset.id}",
                'screen_builder': f"/api/screens/screens/{asset.screen_id}/" if asset.screen_id else None
            }
        })

    # ── Action: View Service History ──────────────────────────────────────────
    @action(detail=True, methods=['get'], url_path='service-history')
    def service_history(self, request, pk=None):
        asset = self.get_object()
        from apps.operations.models import FaultTicket
        tickets = FaultTicket.objects.filter(asset=asset).order_by('-reported_date')
        
        # We can dynamically serialize basic ticket info here or import serializer
        history = []
        for t in tickets:
            history.append({
                'ticket_id': t.id,
                'title': t.title,
                'description': t.description,
                'priority': t.priority,
                'status': t.status,
                'reported_date': t.reported_date,
                'resolved_date': t.resolved_date,
                'technician': t.technician_name
            })
            
        return Response({
            'asset_id': asset.asset_id,
            'asset_name': asset.asset_name,
            'service_history_count': len(history),
            'history': history
        })

    # ── Action: Export Asset Register ─────────────────────────────────────────
    @action(detail=False, methods=['get'], url_path='export-register')
    def export_register(self, request):
        import csv
        from django.http import HttpResponse
        qs = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="canonical_asset_register.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'Asset ID', 'Category', 'Asset Name', 'Location', 'Serial No',
            'Purchase Date', 'Vendor', 'Warranty', 'Status', 'Service Due Date', 'Screen'
        ])
        for a in qs:
            writer.writerow([
                a.asset_id, a.template.category.label, a.asset_name, a.location, a.serial_number,
                a.purchase_date, a.vendor, a.warranty, a.get_status_display(), a.service_due_date,
                a.screen.name if a.screen else 'None'
            ])
        return response



class AssetLogViewSet(TenantAuditMixin, viewsets.ModelViewSet):
    queryset = AssetLog.objects.select_related('asset', 'entered_by').all()
    serializer_class = AssetLogSerializer
    filterset_fields = ['asset', 'log_date']
    permission_classes = [IsStaffOrAbove]

    def get_queryset(self):
        qs = super().get_queryset()
        from apps.tenants.mixins import get_tenant_from_request
        tenant = get_tenant_from_request(self.request)
        if tenant:
            return qs.filter(asset__tenant=tenant)
        return qs.none()

    def perform_create(self, serializer):
        from apps.tenants.mixins import get_tenant_from_request
        from rest_framework.exceptions import PermissionDenied
        tenant = get_tenant_from_request(self.request)
        asset = serializer.validated_data.get('asset')
        if asset and asset.tenant_id != tenant.id:
            raise PermissionDenied("You do not have permission to add logs for this asset.")
        super().perform_create(serializer)


# ─── MAINTENANCE DESK ─────────────────────────────────────────────────────────

class FaultTicketSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source='asset.__str__', read_only=True)

    class Meta:
        model = FaultTicket
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class PMScheduleSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source='asset.__str__', read_only=True)

    class Meta:
        model = PMSchedule
        fields = '__all__'
        read_only_fields = ['created_at']


class WorkOrderSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source='asset.__str__', read_only=True)

    class Meta:
        model = WorkOrder
        fields = '__all__'
        read_only_fields = ['wo_number', 'total_cost', 'created_at', 'updated_at']


class AMCContractSerializer(serializers.ModelSerializer):
    days_to_expiry = serializers.IntegerField(read_only=True)

    class Meta:
        model = AMCContract
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class FaultTicketSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source='asset.__str__', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = FaultTicket
        fields = '__all__'
        read_only_fields = ['ticket_no', 'created_at', 'updated_at', 'closure_timestamp']


class FaultTicketViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = FaultTicket.objects.select_related('asset', 'reported_by').order_by('-reported_date', '-created_at')
    serializer_class = FaultTicketSerializer
    filterset_fields = ['status', 'priority', 'category', 'asset', 'is_escalated']
    permission_classes = [IsStaffOrAbove]

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant, reported_by=self.request.user)

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        ticket = self.get_object()
        assigned_to = request.data.get('assigned_to')
        if not assigned_to:
            return Response({'error': 'assigned_to is required'}, status=400)
        ticket.assigned_to = assigned_to
        if ticket.status == FaultTicket.Status.OPEN:
            ticket.status = FaultTicket.Status.IN_PROGRESS
        ticket.save(update_fields=['assigned_to', 'status', 'updated_at'])
        return Response({'status': 'Assigned', 'assigned_to': assigned_to})

    @action(detail=True, methods=['post'])
    def mark_in_progress(self, request, pk=None):
        ticket = self.get_object()
        ticket.status = FaultTicket.Status.IN_PROGRESS
        ticket.save(update_fields=['status', 'updated_at'])
        return Response({'status': FaultTicket.Status.IN_PROGRESS})

    @action(detail=True, methods=['post'])
    def escalate(self, request, pk=None):
        ticket = self.get_object()
        reason = request.data.get('escalation_reason', '')
        ticket.status = FaultTicket.Status.ESCALATED
        ticket.is_escalated = True
        ticket.escalation_reason = reason
        ticket.save(update_fields=['status', 'is_escalated', 'escalation_reason', 'updated_at'])
        from apps.audit.models import ChangeLog
        ChangeLog.objects.create(
            tenant=self.request.tenant,
            table_name='FaultTicket',
            record_id=ticket.id,
            action=ChangeLog.ACTION_UPDATE,
            changed_by=request.user,
            changes={'status': 'ESCALATED', 'reason': reason}
        )
        return Response({'status': 'Escalated', 'ticket_no': ticket.ticket_no})

    @action(detail=True, methods=['post'])
    def close_ticket(self, request, pk=None):
        from django.utils import timezone
        ticket = self.get_object()
        if ticket.status == FaultTicket.Status.CLOSED:
            return Response({'error': 'Ticket already closed'}, status=400)
        ticket.status = FaultTicket.Status.CLOSED
        ticket.closure_timestamp = timezone.now()
        ticket.resolved_date = timezone.now().date()
        ticket.resolution_note = request.data.get('resolution_note', ticket.resolution_note)
        ticket.cost = request.data.get('cost', ticket.cost)
        ticket.downtime_hours = request.data.get('downtime_hours', ticket.downtime_hours)
        ticket.save()
        from apps.audit.models import ChangeLog
        ChangeLog.objects.create(
            tenant=self.request.tenant,
            table_name='FaultTicket',
            record_id=ticket.id,
            action=ChangeLog.ACTION_UPDATE,
            changed_by=request.user,
            changes={'status': 'CLOSED', 'cost': str(ticket.cost), 'downtime_hours': str(ticket.downtime_hours)}
        )
        return Response({'status': 'Closed', 'ticket_no': ticket.ticket_no, 'closure_timestamp': str(ticket.closure_timestamp)})

    @action(detail=True, methods=['post'])
    def generate_work_order(self, request, pk=None):
        """Create a CORRECTIVE work order from this fault ticket."""
        ticket = self.get_object()
        wo = WorkOrder.objects.create(
            tenant=ticket.tenant,
            asset=ticket.asset,
            fault_ticket=ticket,
            type=WorkOrder.Type.CORRECTIVE,
            description=ticket.description,
            assigned_to=ticket.assigned_to,
            entered_by=request.user,
        )
        ticket.status = FaultTicket.Status.IN_PROGRESS
        ticket.save(update_fields=['status', 'updated_at'])
        return Response({'status': 'Work order created', 'work_order_id': wo.id, 'wo_number': wo.wo_number})


class PMScheduleSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source='asset.__str__', read_only=True)
    maintenance_type_display = serializers.CharField(source='get_maintenance_type_display', read_only=True)
    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    alert_due = serializers.BooleanField(read_only=True)

    class Meta:
        model = PMSchedule
        fields = '__all__'
        read_only_fields = ['completed_count', 'created_at', 'updated_at']


class PMScheduleViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = PMSchedule.objects.select_related('asset').order_by('next_due_date')
    serializer_class = PMScheduleSerializer
    filterset_fields = ['status', 'asset', 'frequency', 'maintenance_type']
    permission_classes = [IsStaffOrAbove]

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)

    @action(detail=False, methods=['get'])
    def due_today(self, request):
        from django.utils import timezone
        today = timezone.now().date()
        due = self.get_queryset().filter(next_due_date__lte=today, status=PMSchedule.Status.ACTIVE)
        return Response(PMScheduleSerializer(due, many=True).data)

    @action(detail=False, methods=['get'])
    def alert_window(self, request):
        """Return all PM schedules whose reminder window has been reached."""
        from django.utils import timezone
        today = timezone.now().date()
        qs = self.get_queryset().filter(status=PMSchedule.Status.ACTIVE)
        alert_list = [s for s in qs if s.alert_due]
        return Response(PMScheduleSerializer(alert_list, many=True).data)

    @action(detail=True, methods=['post'])
    def reschedule(self, request, pk=None):
        sched = self.get_object()
        new_date = request.data.get('next_due_date')
        reason = request.data.get('reason', '')
        if not new_date:
            return Response({'error': 'next_due_date is required (YYYY-MM-DD)'}, status=400)
        old_date = str(sched.next_due_date)
        sched.next_due_date = new_date
        sched.notes = f"{sched.notes}\n[Rescheduled from {old_date} to {new_date}: {reason}]".strip()
        sched.save(update_fields=['next_due_date', 'notes', 'updated_at'])
        from apps.audit.models import ChangeLog
        ChangeLog.objects.create(
            tenant=self.request.tenant,
            table_name='PMSchedule',
            record_id=sched.id,
            action=ChangeLog.ACTION_UPDATE,
            changed_by=request.user,
            changes={'rescheduled_from': old_date, 'rescheduled_to': new_date, 'reason': reason}
        )
        return Response({'status': 'Rescheduled', 'next_due_date': new_date})

    @action(detail=True, methods=['post'])
    def mark_completed(self, request, pk=None):
        """Mark this service cycle as completed and advance the next_due_date."""
        from django.utils import timezone
        from dateutil.relativedelta import relativedelta
        sched = self.get_object()
        today = timezone.now().date()
        sched.last_done_date = request.data.get('completed_date') or today
        sched.completed_count += 1
        freq_map = {
            PMSchedule.Frequency.DAILY:       relativedelta(days=1),
            PMSchedule.Frequency.WEEKLY:      relativedelta(weeks=1),
            PMSchedule.Frequency.MONTHLY:     relativedelta(months=1),
            PMSchedule.Frequency.QUARTERLY:   relativedelta(months=3),
            PMSchedule.Frequency.HALF_YEARLY: relativedelta(months=6),
            PMSchedule.Frequency.YEARLY:      relativedelta(years=1),
        }
        delta = freq_map.get(sched.frequency)
        if delta:
            sched.next_due_date = today + delta
        sched.save()
        from apps.audit.models import ChangeLog
        ChangeLog.objects.create(
            tenant=self.request.tenant,
            table_name='PMSchedule',
            record_id=sched.id,
            action=ChangeLog.ACTION_UPDATE,
            changed_by=request.user,
            changes={'completed_on': str(sched.last_done_date), 'next_due_date': str(sched.next_due_date), 'completed_count': sched.completed_count}
        )
        return Response({'status': 'Completed', 'next_due_date': str(sched.next_due_date), 'completed_count': sched.completed_count})

    @action(detail=True, methods=['post'])
    def generate_work_order(self, request, pk=None):
        """Create a PREVENTIVE work order from a PM schedule."""
        sched = self.get_object()
        wo = WorkOrder.objects.create(
            tenant=sched.tenant,
            asset=sched.asset,
            pm_schedule=sched,
            type=WorkOrder.Type.PREVENTIVE,
            description=sched.task_name,
            assigned_to=sched.assigned_to,
            scheduled_date=sched.next_due_date,
            entered_by=request.user,
        )
        return Response({'status': 'Work order created', 'work_order_id': wo.id, 'wo_number': wo.wo_number})

    @action(detail=False, methods=['get'])
    def export_due_list(self, request):
        import csv
        from django.http import HttpResponse
        from django.utils import timezone
        today = timezone.now().date()
        qs = self.get_queryset().filter(next_due_date__lte=today, status=PMSchedule.Status.ACTIVE)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="pm_due_list.csv"'
        writer = csv.writer(response)
        writer.writerow(['Task', 'Type', 'Asset', 'Frequency', 'Last Done', 'Next Due', 'Assigned To', 'Est. Cost', 'Status'])
        for s in qs:
            writer.writerow([
                s.task_name, s.get_maintenance_type_display(), str(s.asset),
                s.get_frequency_display(), s.last_done_date, s.next_due_date,
                s.assigned_to, s.estimated_cost, s.status
            ])
        return response


class WorkOrderSerializer(serializers.ModelSerializer):
    asset_name     = serializers.CharField(source='asset.__str__', read_only=True)
    ticket_no      = serializers.CharField(source='fault_ticket.ticket_no', read_only=True)
    type_display   = serializers.CharField(source='get_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = WorkOrder
        fields = '__all__'
        read_only_fields = ['wo_number', 'total_cost', 'assigned_timestamp', 'created_at', 'updated_at']


class WorkOrderViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = WorkOrder.objects.select_related('asset', 'fault_ticket', 'pm_schedule').order_by('-created_at')
    serializer_class = WorkOrderSerializer
    filterset_fields = ['status', 'type', 'asset', 'fault_ticket']
    permission_classes = [IsStaffOrAbove]

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant, entered_by=self.request.user)

    @action(detail=True, methods=['post'])
    def assign_technician(self, request, pk=None):
        from django.utils import timezone
        wo = self.get_object()
        assigned_to = request.data.get('assigned_to')
        if not assigned_to:
            return Response({'error': 'assigned_to is required'}, status=400)
        wo.assigned_to = assigned_to
        wo.assigned_timestamp = timezone.now()
        wo.status = WorkOrder.Status.ASSIGNED
        wo.save(update_fields=['assigned_to', 'assigned_timestamp', 'status', 'updated_at'])
        return Response({'status': 'Assigned', 'assigned_to': assigned_to, 'wo_number': wo.wo_number})

    @action(detail=True, methods=['post'])
    def mark_complete(self, request, pk=None):
        from django.utils import timezone
        wo = self.get_object()
        if wo.status == WorkOrder.Status.COMPLETED:
            return Response({'error': 'Already completed'}, status=400)
        wo.status = WorkOrder.Status.COMPLETED
        wo.completed_date    = request.data.get('completed_date') or timezone.now().date()
        wo.labour_cost       = request.data.get('labour_cost', wo.labour_cost)
        wo.parts_cost        = request.data.get('parts_cost', wo.parts_cost)
        wo.actual_cost       = request.data.get('actual_cost', wo.actual_cost)
        wo.parts_used        = request.data.get('parts_used', wo.parts_used)
        wo.vendor_invoice_no = request.data.get('vendor_invoice_no', wo.vendor_invoice_no)
        wo.notes             = request.data.get('notes', wo.notes)
        wo.save()

        # Auto-resolve linked fault ticket if all its WOs are done
        if wo.fault_ticket:
            open_wos = wo.fault_ticket.work_orders.exclude(status=WorkOrder.Status.COMPLETED).count()
            if open_wos == 0:
                wo.fault_ticket.status       = FaultTicket.Status.RESOLVED
                wo.fault_ticket.resolved_date = wo.completed_date
                wo.fault_ticket.save(update_fields=['status', 'resolved_date'])

        # Advance PM schedule if linked
        if wo.pm_schedule:
            wo.pm_schedule.last_done_date   = wo.completed_date
            wo.pm_schedule.completed_count += 1
            wo.pm_schedule.save(update_fields=['last_done_date', 'completed_count', 'updated_at'])

        # Auto-append to Service History
        service_type = (
            ServiceHistory.ServiceType.PREVENTIVE
            if wo.type == WorkOrder.Type.PREVENTIVE
            else ServiceHistory.ServiceType.INSPECTION
            if wo.type == WorkOrder.Type.INSPECTION
            else ServiceHistory.ServiceType.CORRECTIVE
        )
        ServiceHistory.objects.get_or_create(
            work_order=wo,
            defaults=dict(
                tenant=wo.tenant,
                asset=wo.asset,
                fault_ticket=wo.fault_ticket,
                service_date=wo.completed_date,
                service_type=service_type,
                vendor_name=wo.assigned_to,
                cost=wo.total_cost,
                downtime_hours=wo.fault_ticket.downtime_hours if wo.fault_ticket else 0,
                notes=wo.notes,
            )
        )

        from apps.audit.models import ChangeLog
        ChangeLog.objects.create(
            tenant=self.request.tenant,
            table_name='WorkOrder',
            record_id=wo.id,
            action=ChangeLog.ACTION_UPDATE,
            changed_by=request.user,
            changes={
                'status': 'COMPLETED',
                'labour_cost': str(wo.labour_cost),
                'parts_cost': str(wo.parts_cost),
                'total_cost': str(wo.total_cost),
                'vendor_invoice_no': wo.vendor_invoice_no,
            }
        )
        return Response({'status': 'Completed', 'wo_number': wo.wo_number, 'total_cost': str(wo.total_cost)})

    @action(detail=False, methods=['get'])
    def export(self, request):
        import csv
        from django.http import HttpResponse
        qs = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="work_order_register.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'WO No', 'Type', 'Asset', 'Linked Ticket', 'Assigned To',
            'Scope', 'Scheduled Date', 'Completed Date',
            'Labour Cost', 'Parts Cost', 'Misc Cost', 'Total Cost',
            'Parts Used', 'Invoice No', 'Status'
        ])
        for w in qs:
            writer.writerow([
                w.wo_number, w.get_type_display(), str(w.asset),
                w.fault_ticket.ticket_no if w.fault_ticket else '',
                w.assigned_to, w.scope_of_work,
                w.scheduled_date, w.completed_date,
                w.labour_cost, w.parts_cost, w.actual_cost, w.total_cost,
                w.parts_used, w.vendor_invoice_no, w.status
            ])
        return response


class AMCContractSerializer(serializers.ModelSerializer):
    days_to_expiry       = serializers.IntegerField(read_only=True)
    warranty_days_remaining = serializers.IntegerField(read_only=True)
    is_expiring_soon     = serializers.BooleanField(read_only=True)
    coverage_type_display = serializers.CharField(source='get_coverage_type_display', read_only=True)
    renewal_status_display = serializers.CharField(source='get_renewal_status_display', read_only=True)

    class Meta:
        model = AMCContract
        fields = '__all__'
        read_only_fields = ['renewal_history', 'created_at', 'updated_at']


class AMCContractViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = AMCContract.objects.prefetch_related('assets').order_by('end_date')
    serializer_class = AMCContractSerializer
    filterset_fields = ['status', 'coverage_type', 'renewal_status', 'vendor_name']
    permission_classes = [IsStaffOrAbove]

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)

    @action(detail=True, methods=['post'])
    def renew(self, request, pk=None):
        from django.utils import timezone
        contract = self.get_object()
        new_start = request.data.get('start_date')
        new_end   = request.data.get('end_date')
        new_value = request.data.get('contract_value', contract.contract_value)
        if not (new_start and new_end):
            return Response({'error': 'start_date and end_date are required'}, status=400)

        # Snapshot renewal into history before overwriting
        history_entry = {
            'renewed_on': str(timezone.now().date()),
            'renewed_by': request.user.get_full_name() or request.user.username,
            'old_end_date': str(contract.end_date),
            'new_end_date': new_end,
            'new_value': str(new_value),
        }
        contract.renewal_history = (contract.renewal_history or []) + [history_entry]
        contract.start_date    = new_start
        contract.end_date      = new_end
        contract.contract_value = new_value
        contract.status         = AMCContract.Status.RENEWED
        contract.renewal_status = AMCContract.RenewalStatus.RENEWED
        contract.save()
        return Response({'status': 'Renewed', 'new_end_date': str(contract.end_date)})

    @action(detail=True, methods=['post'])
    def mark_expired(self, request, pk=None):
        contract = self.get_object()
        contract.status = AMCContract.Status.LAPSED
        contract.renewal_status = AMCContract.RenewalStatus.NOT_RENEWING
        contract.save(update_fields=['status', 'renewal_status', 'updated_at'])
        from apps.audit.models import ChangeLog
        ChangeLog.objects.create(
            tenant=self.request.tenant,
            table_name='AMCContract',
            record_id=contract.id,
            action=ChangeLog.ACTION_UPDATE,
            changed_by=request.user,
            changes={'status': 'LAPSED', 'contract_no': contract.contract_no}
        )
        return Response({'status': 'Marked as Lapsed/Expired', 'contract_no': contract.contract_no})

    @action(detail=True, methods=['post'])
    def push_expiry_alert(self, request, pk=None):
        """Flag the contract as EXPIRING and push a dashboard-level alert."""
        contract = self.get_object()
        if contract.status not in [AMCContract.Status.ACTIVE, AMCContract.Status.EXPIRING]:
            return Response({'error': 'Contract is not in an active state'}, status=400)
        contract.status = AMCContract.Status.EXPIRING
        contract.save(update_fields=['status', 'updated_at'])
        # Write to audit trail so Alert Center can surface it
        from apps.audit.models import ChangeLog
        ChangeLog.objects.create(
            tenant=self.request.tenant,
            table_name='AMCContract',
            record_id=contract.id,
            action=ChangeLog.ACTION_UPDATE,
            changed_by=request.user,
            changes={
                'alert': 'EXPIRY_WARNING',
                'days_to_expiry': contract.days_to_expiry,
                'contract_no': contract.contract_no,
                'vendor_name': contract.vendor_name,
            }
        )
        return Response({
            'status': 'Alert pushed',
            'contract_no': contract.contract_no,
            'days_to_expiry': contract.days_to_expiry,
        })

    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):
        from django.utils import timezone
        import datetime
        threshold = timezone.now().date() + datetime.timedelta(days=60)
        qs = self.get_queryset().filter(
            end_date__lte=threshold,
            status__in=[AMCContract.Status.ACTIVE, AMCContract.Status.EXPIRING]
        )
        for contract in qs:
            if contract.status == AMCContract.Status.ACTIVE:
                contract.status = AMCContract.Status.EXPIRING
                contract.save(update_fields=['status', 'updated_at'])
        return Response(AMCContractSerializer(qs, many=True).data)

    @action(detail=False, methods=['get'])
    def export(self, request):
        import csv
        from django.http import HttpResponse
        qs = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="amc_warranty_register.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'Contract No', 'Vendor', 'Support Contact', 'Coverage Type',
            'Start Date', 'End Date', 'Warranty End Date',
            'Contract Value', 'Days to Expiry', 'Status', 'Renewal Status'
        ])
        for c in qs:
            writer.writerow([
                c.contract_no, c.vendor_name, c.vendor_contact,
                c.get_coverage_type_display(), c.start_date, c.end_date,
                c.warranty_end_date, c.contract_value,
                c.days_to_expiry, c.status, c.renewal_status
            ])
        return response


class MaintenanceDashboardViewSet(viewsets.ViewSet):
    permission_classes = [IsStaffOrAbove]

    @action(detail=False, methods=['get'])
    def summary(self, request):
        from django.utils import timezone
        from django.db.models import Sum
        import datetime
        tenant = request.tenant
        today = timezone.now().date()
        month_start = today.replace(day=1)

        open_faults = FaultTicket.objects.filter(
            tenant=tenant, status__in=[FaultTicket.Status.OPEN, FaultTicket.Status.IN_PROGRESS]
        ).count()

        assets_due_pm = PMSchedule.objects.filter(
            tenant=tenant, status=PMSchedule.Status.ACTIVE, next_due_date__lte=today
        ).count()

        open_work_orders = WorkOrder.objects.filter(
            tenant=tenant
        ).exclude(status__in=[WorkOrder.Status.COMPLETED, WorkOrder.Status.CANCELLED]).count()

        amc_expiring_soon_threshold = today + datetime.timedelta(days=60)
        amc_expiring = AMCContract.objects.filter(
            tenant=tenant, end_date__lte=amc_expiring_soon_threshold,
            status__in=[AMCContract.Status.ACTIVE, AMCContract.Status.EXPIRING]
        ).count()

        maintenance_cost_month = WorkOrder.objects.filter(
            tenant=tenant, status=WorkOrder.Status.COMPLETED,
            completed_date__gte=month_start, completed_date__lte=today
        ).aggregate(t=Sum('total_cost'))['t'] or 0

        return Response({
            'open_fault_tickets': open_faults,
            'assets_due_for_pm': assets_due_pm,
            'open_work_orders': open_work_orders,
            'amc_expiring_soon': amc_expiring,
            'maintenance_cost_this_month': maintenance_cost_month,
        })


# ─── SERVICE HISTORY ──────────────────────────────────────────────────────────

class ServiceHistorySerializer(serializers.ModelSerializer):
    asset_name         = serializers.CharField(source='asset.__str__', read_only=True)
    wo_number          = serializers.CharField(source='work_order.wo_number', read_only=True)
    ticket_no          = serializers.CharField(source='fault_ticket.ticket_no', read_only=True)
    amc_contract_no    = serializers.CharField(source='amc_contract.contract_no', read_only=True)
    service_type_display = serializers.CharField(source='get_service_type_display', read_only=True)

    class Meta:
        model = ServiceHistory
        fields = '__all__'
        read_only_fields = ['created_at']


class ServiceHistoryViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    """
    Read-mostly viewset — records are auto-created on WorkOrder completion.
    Manual creation is allowed for warranty/AMC services not backed by a WO.
    """
    queryset = ServiceHistory.objects.select_related(
        'asset', 'work_order', 'fault_ticket', 'amc_contract'
    ).order_by('-service_date', '-created_at')
    serializer_class = ServiceHistorySerializer
    filterset_fields  = ['asset', 'service_type', 'amc_contract']
    permission_classes = [IsStaffOrAbove]

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)

    @action(detail=False, methods=['get'])
    def timeline(self, request):
        """Return service events for a specific asset sorted chronologically."""
        asset_id = request.query_params.get('asset')
        if not asset_id:
            return Response({'error': 'asset query param is required'}, status=400)
        qs = self.get_queryset().filter(asset_id=asset_id)
        return Response(ServiceHistorySerializer(qs, many=True).data)

    @action(detail=False, methods=['get'])
    def asset_summary(self, request):
        """Aggregate cost, downtime, and event counts per asset."""
        from django.db.models import Sum, Count
        qs = self.get_queryset()
        data = (
            qs.values('asset', 'asset__serial_number')
            .annotate(
                total_cost=Sum('cost'),
                total_downtime=Sum('downtime_hours'),
                event_count=Count('id')
            )
            .order_by('-total_cost')
        )
        return Response(list(data))

    @action(detail=False, methods=['get'])
    def export(self, request):
        import csv
        from django.http import HttpResponse
        qs = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="service_history.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'Service Date', 'Asset', 'Service Type', 'Ticket No', 'WO No',
            'Vendor', 'Cost', 'Downtime (hrs)', 'AMC Contract', 'Notes'
        ])
        for s in qs:
            writer.writerow([
                s.service_date, str(s.asset), s.get_service_type_display(),
                s.fault_ticket.ticket_no if s.fault_ticket else '',
                s.work_order.wo_number if s.work_order else '',
                s.vendor_name, s.cost, s.downtime_hours,
                s.amc_contract.contract_no if s.amc_contract else '',
                s.notes
            ])
        return response


# ─── WATER LOG ────────────────────────────────────────────────────────────────

class WaterLogSerializer(serializers.ModelSerializer):
    meter_name   = serializers.CharField(source='meter.name', read_only=True)
    total_cost   = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = WaterLog
        fields = '__all__'
        read_only_fields = ['consumption', 'created_at', 'updated_at']

    def get_total_cost(self, obj):
        return obj.tanker_cost + obj.municipal_bill


class WaterLogViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = WaterLog.objects.select_related('meter').order_by('-date')
    serializer_class = WaterLogSerializer
    filterset_fields = ['date', 'meter']
    permission_classes = [IsStaffOrAbove]

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)

    # ── Action: Add Reading (Meter-based) ─────────────────────────────────────
    @action(detail=False, methods=['post'], url_path='add-reading')
    def add_reading(self, request):
        date    = request.data.get('date')
        meter_id = request.data.get('meter')
        opening = request.data.get('opening_reading')
        closing = request.data.get('closing_reading')
        notes   = request.data.get('notes', '')

        if not (date and meter_id and opening is not None and closing is not None):
            return Response({'error': 'date, meter, opening_reading, and closing_reading are required'}, status=400)

        log, created = WaterLog.objects.update_or_create(
            tenant=request.tenant, date=date, meter_id=meter_id,
            defaults={
                'opening_reading': opening,
                'closing_reading': closing,
                'notes': notes,
            }
        )
        return Response(WaterLogSerializer(log).data)

    # ── Action: Add Tanker Entry ──────────────────────────────────────────────
    @action(detail=False, methods=['post'], url_path='add-tanker')
    def add_tanker(self, request):
        date      = request.data.get('date')
        meter_id  = request.data.get('meter')
        qty       = request.data.get('tanker_purchase_qty', 0)
        cost      = request.data.get('tanker_cost', 0)
        vendor    = request.data.get('linked_vendor', '')
        notes     = request.data.get('notes', '')

        if not (date and meter_id):
            return Response({'error': 'date and meter are required'}, status=400)

        # Retrieve or create WaterLog for this date to append tanker purchase
        log, created = WaterLog.objects.get_or_create(
            tenant=request.tenant, date=date, meter_id=meter_id,
            defaults={
                'tanker_purchase_qty': qty,
                'tanker_cost': cost,
                'linked_vendor': vendor,
                'notes': notes,
            }
        )
        if not created:
            log.tanker_purchase_qty = qty
            log.tanker_cost = cost
            log.linked_vendor = vendor
            if notes:
                log.notes = f"{log.notes}\n{notes}".strip()
            log.save()

        return Response(WaterLogSerializer(log).data)

    # ── Action: Upload Bill ───────────────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='upload-bill')
    def upload_bill(self, request, pk=None):
        log = self.get_object()
        bill_file = request.FILES.get('attachment')
        muni_bill = request.data.get('municipal_bill')

        if not bill_file and muni_bill is None:
            return Response({'error': 'attachment or municipal_bill is required'}, status=400)

        if bill_file:
            log.attachment = bill_file
        if muni_bill is not None:
            log.municipal_bill = muni_bill
        log.save()
        return Response(WaterLogSerializer(log).data)

    # ── Action: Link Expense Entry ────────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='link-expense')
    def link_expense(self, request, pk=None):
        log = self.get_object()
        expense_ref = request.data.get('expense_ref')
        if not expense_ref:
            return Response({'error': 'expense_ref is required'}, status=400)

        log.expense_ref = expense_ref
        log.save(update_fields=['expense_ref', 'updated_at'])
        return Response({'status': 'Expense entry linked', 'expense_ref': expense_ref})

    # ── Action: Auto-calculate Monthly Consumption ────────────────────────────
    @action(detail=False, methods=['get'], url_path='monthly-consumption')
    def monthly_consumption(self, request):
        """
        Aggregate total metered usage, tanker purchases, and utility cost for a month.
        Query params: ?year=YYYY&month=MM
        """
        year  = request.query_params.get('year')
        month = request.query_params.get('month')
        if not (year and month):
            from django.utils import timezone
            today = timezone.now().date()
            year, month = today.year, today.month

        qs = self.get_queryset().filter(date__year=year, date__month=month)

        from django.db.models import Sum
        summary = qs.aggregate(
            total_meter_consumption=Sum('consumption'),
            total_tanker_purchase=Sum('tanker_purchase_qty'),
            total_tanker_cost=Sum('tanker_cost'),
            total_muni_bill=Sum('municipal_bill'),
        )

        total_cost = (summary['total_tanker_cost'] or 0) + (summary['total_muni_bill'] or 0)

        return Response({
            'year': int(year),
            'month': int(month),
            'metered_consumption_liters': summary['total_meter_consumption'] or 0,
            'tanker_purchase_qty_liters': summary['total_tanker_purchase'] or 0,
            'tanker_cost': summary['total_tanker_cost'] or 0,
            'municipal_bill': summary['total_muni_bill'] or 0,
            'total_utility_cost': total_cost,
        })

    # ── Action: Export Utility Summary ────────────────────────────────────────
    @action(detail=False, methods=['get'], url_path='export-summary')
    def export_summary(self, request):
        import csv
        from django.http import HttpResponse
        qs = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="water_utility_summary.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'Date', 'Meter', 'Opening Reading', 'Closing Reading',
            'Metered Consumption', 'Tanker Qty', 'Tanker Cost',
            'Municipal Bill', 'Total Cost', 'Vendor Name', 'Expense Ref', 'Notes'
        ])
        for log in qs:
            total_cost = log.tanker_cost + log.municipal_bill
            writer.writerow([
                log.date, log.meter.name, log.opening_reading, log.closing_reading,
                log.consumption, log.tanker_purchase_qty, log.tanker_cost,
                log.municipal_bill, total_cost, log.linked_vendor, log.expense_ref, log.notes
            ])
        return response


# ─── ALERT CENTER ─────────────────────────────────────────────────────────────

from django.conf import settings

class OperationalAlertSerializer(serializers.ModelSerializer):
    alert_type_display = serializers.CharField(source='get_alert_type_display', read_only=True)
    severity_display   = serializers.CharField(source='get_severity_display', read_only=True)
    status_display     = serializers.CharField(source='get_status_display', read_only=True)
    assigned_username  = serializers.CharField(source='assigned_user.username', read_only=True)
    acknowledged_by_username = serializers.CharField(source='acknowledged_by.username', read_only=True)
    resolved_by_username     = serializers.CharField(source='resolved_by.username', read_only=True)

    class Meta:
        model = OperationalAlert
        fields = '__all__'
        read_only_fields = ['tenant', 'triggered_time', 'audit_ref', 'acknowledged_by', 'resolved_by']


class OperationalAlertViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = OperationalAlert.objects.select_related(
        'assigned_user', 'acknowledged_by', 'resolved_by'
    ).order_by('-triggered_time')
    serializer_class = OperationalAlertSerializer
    filterset_fields = ['alert_type', 'severity', 'status', 'assigned_user']
    search_fields = ['reference_record', 'audit_ref', 'resolution_note']
    permission_classes = [IsStaffOrAbove]

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)

    # ── Action: Acknowledge ───────────────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='acknowledge')
    def acknowledge(self, request, pk=None):
        alert = self.get_object()
        if alert.status in [OperationalAlert.Status.RESOLVED]:
            return Response({'error': 'Cannot acknowledge a resolved alert'}, status=400)

        alert.status = OperationalAlert.Status.ACKNOWLEDGED
        alert.acknowledged_by = request.user
        alert.save()

        # Audit Shield entry
        from apps.audit.models import ChangeLog
        ChangeLog.objects.create(
            tenant=alert.tenant,
            table_name='OperationalAlert',
            record_id=alert.id,
            action=ChangeLog.ACTION_UPDATE,
            changed_by=request.user,
            changes={'status': 'ACKNOWLEDGED', 'audit_ref': alert.audit_ref}
        )

        return Response(OperationalAlertSerializer(alert).data)

    # ── Action: Resolve ───────────────────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='resolve')
    def resolve(self, request, pk=None):
        alert = self.get_object()
        note = request.data.get('resolution_note', '')

        if not note:
            return Response({'error': 'resolution_note is required to resolve an alert'}, status=400)

        alert.status = OperationalAlert.Status.RESOLVED
        alert.resolved_by = request.user
        alert.resolution_note = note
        alert.save()

        # Audit Shield entry
        from apps.audit.models import ChangeLog
        ChangeLog.objects.create(
            tenant=alert.tenant,
            table_name='OperationalAlert',
            record_id=alert.id,
            action=ChangeLog.ACTION_UPDATE,
            changed_by=request.user,
            changes={'status': 'RESOLVED', 'resolution_note': note, 'audit_ref': alert.audit_ref}
        )

        return Response(OperationalAlertSerializer(alert).data)

    # ── Action: Snooze ────────────────────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='snooze')
    def snooze(self, request, pk=None):
        alert = self.get_object()
        alert.status = OperationalAlert.Status.SNOOZED
        alert.save(update_fields=['status', 'updated_at'])

        # Audit Shield entry
        from apps.audit.models import ChangeLog
        ChangeLog.objects.create(
            tenant=alert.tenant,
            table_name='OperationalAlert',
            record_id=alert.id,
            action=ChangeLog.ACTION_UPDATE,
            changed_by=request.user,
            changes={'status': 'SNOOZED', 'audit_ref': alert.audit_ref}
        )

        return Response(OperationalAlertSerializer(alert).data)

    # ── Action: Assign User ───────────────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='assign')
    def assign(self, request, pk=None):
        alert = self.get_object()
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'user_id is required'}, status=400)

        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user_obj = User.objects.get(pk=user_id)
            alert.assigned_user = user_obj
            alert.save(update_fields=['assigned_user', 'updated_at'])

            return Response(OperationalAlertSerializer(alert).data)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=44)

    # ── Action: Open Source Record (Redirection Details) ─────────────────────
    @action(detail=True, methods=['get'], url_path='source-record')
    def source_record(self, request, pk=None):
        alert = self.get_object()
        mapping = {
            OperationalAlert.AlertType.LOW_STOCK: {
                'module_name': 'Revenue & Cafe Purchases',
                'description': 'View low stock items and place coffee/popcorn purchases orders.',
                'redirection_url': '/api/revenue/items/'
            },
            OperationalAlert.AlertType.LAMP_THRESHOLD: {
                'module_name': 'Screens & Projection Lamp logs',
                'description': 'Projection lamp hours remaining is approaching replacement threshold.',
                'redirection_url': '/api/screens/'
            },
            OperationalAlert.AlertType.ASSET_PM_DUE: {
                'module_name': 'Preventive Maintenance',
                'description': 'Asset is approaching preventive maintenance due date schedule.',
                'redirection_url': '/api/operations/maintenance/pm-schedules/'
            },
            OperationalAlert.AlertType.UTILITY_ANOMALY: {
                'module_name': 'Utility Readings & Water Logs',
                'description': 'Metered readings or water consumption variances detected.',
                'redirection_url': '/api/operations/water-logs/'
            },
            OperationalAlert.AlertType.DCR_MISMATCH: {
                'module_name': 'District DCR Reports',
                'description': 'Box Office report data mismatch with ticketing systems.',
                'redirection_url': '/api/integrations/dcr/'
            },
            OperationalAlert.AlertType.SETTLEMENT_OVERDUE: {
                'module_name': 'Finance & Bookings',
                'description': 'BMS counter ticket cash settlement is overdue.',
                'redirection_url': '/api/finance/'
            },
            OperationalAlert.AlertType.PARKING_OVERFLOW: {
                'module_name': 'Parking Analytics',
                'description': 'Active parking zone occupancy exceeds overflow configuration limits.',
                'redirection_url': '/api/parking/'
            },
            OperationalAlert.AlertType.PENDING_APPROVAL: {
                'module_name': 'Booking Corrections',
                'description': 'Corrective refunds or compliments require MD/Admin approval.',
                'redirection_url': '/api/bookings/corrections/'
            },
            OperationalAlert.AlertType.GENERATOR_VARIANCE: {
                'module_name': 'Generator Logs',
                'description': 'Generator diesel usage variance detected vs power runtime.',
                'redirection_url': '/api/operations/generator/'
            },
            OperationalAlert.AlertType.HR_SYNC_FAILURE: {
                'module_name': 'HR Sync Log',
                'description': 'Failed roster or attendance sync from External HR API systems.',
                'redirection_url': '/api/payroll/sync-logs/'
            }
        }.get(alert.alert_type, {
            'module_name': 'Operations',
            'description': 'Global Operational logs.',
            'redirection_url': '/api/operations/'
        })

        return Response(mapping)

    # ── Action: Export Alert Log ──────────────────────────────────────────────
    @action(detail=False, methods=['get'], url_path='export')
    def export(self, request):
        import csv
        from django.http import HttpResponse
        qs = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="operational_alerts_log.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'Audit Ref', 'Alert Type', 'Source Module', 'Severity',
            'Triggered Time', 'Reference Record', 'Assigned User', 'Status',
            'Acknowledged By', 'Resolved By', 'Resolution Note'
        ])
        for a in qs:
            writer.writerow([
                a.audit_ref, a.get_alert_type_display(), a.source_module, a.get_severity_display(),
                a.triggered_time, a.reference_record,
                a.assigned_user.username if a.assigned_user else '',
                a.get_status_display(),
                a.acknowledged_by.username if a.acknowledged_by else '',
                a.resolved_by.username if a.resolved_by else '',
                a.resolution_note
            ])
        return response




