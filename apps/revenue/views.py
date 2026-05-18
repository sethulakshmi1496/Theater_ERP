"""AEC Cinemas – Revenue Views (Canteen + Advertising) with Inventory"""

from rest_framework import serializers, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from django.utils import timezone
from .models import (
    CanteenItem, CanteenSale, AdvertisingSlot, 
    CafeExpense, CafeUnit, CafeInward, CafeWastage, CafeDailyConsumption, CafeReorderAlert,
    Advertiser, AdCampaign
)
from apps.accounts.permissions import IsStaffOrAbove, IsMDOrAdmin
from apps.tenants.mixins import TenantSafeMixin


class CafeUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = CafeUnit
        fields = '__all__'


class CanteenItemSerializer(serializers.ModelSerializer):
    stock_risk = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = CanteenItem
        fields = '__all__'


class CafeInwardSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    
    class Meta:
        model = CafeInward
        fields = '__all__'
        read_only_fields = ['total_cost', 'created_at']


class CafeWastageSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    
    class Meta:
        model = CafeWastage
        fields = '__all__'
        read_only_fields = ['value', 'created_at']


class CanteenSaleSerializer(serializers.ModelSerializer):
    cafe_unit_name = serializers.CharField(source='cafe_unit.name', read_only=True)
    margin = serializers.SerializerMethodField()

    class Meta:
        model = CanteenSale
        fields = '__all__'
        read_only_fields = ['total', 'cogs', 'created_at']
        
    def get_margin(self, obj):
        if obj.total and obj.cogs:
            return obj.total - obj.cogs
        return 0


class AdvertisingSlotSerializer(serializers.ModelSerializer):
    show_info = serializers.SerializerMethodField()

    class Meta:
        model = AdvertisingSlot
        fields = '__all__'
        read_only_fields = ['created_at']

    def get_show_info(self, obj):
        return f"{obj.show.movie.title} | {obj.show.show_date} {obj.show.start_time}"


class CafeExpenseSerializer(serializers.ModelSerializer):
    cafe_unit_name = serializers.CharField(source='cafe_unit.name', read_only=True)

    class Meta:
        model = CafeExpense
        fields = '__all__'
        read_only_fields = ['created_at']


class CafeUnitViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = CafeUnit.objects.filter(is_active=True).order_by('name')
    serializer_class = CafeUnitSerializer
    permission_classes = [IsStaffOrAbove]


class CanteenItemViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = CanteenItem.objects.all().order_by('name')
    serializer_class = CanteenItemSerializer
    permission_classes = [IsStaffOrAbove]
    filterset_fields = ['category', 'is_track_stock', 'is_active']
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        item = self.get_object()
        item.is_active = False
        item.save(update_fields=['is_active'])
        return Response({'status': 'Item deactivated'})

    @action(detail=True, methods=['post'])
    def set_reorder_rule(self, request, pk=None):
        item = self.get_object()
        reorder_level = request.data.get('reorder_level')
        if reorder_level is not None:
            item.reorder_level = reorder_level
            item.save(update_fields=['reorder_level'])
            return Response({'status': 'Reorder level updated', 'reorder_level': item.reorder_level})
        return Response({'error': 'reorder_level is required'}, status=400)

    @action(detail=True, methods=['post'])
    def link_supplier(self, request, pk=None):
        item = self.get_object()
        supplier_name = request.data.get('supplier_name')
        if supplier_name is not None:
            item.supplier_name = supplier_name
            item.save(update_fields=['supplier_name'])
            return Response({'status': 'Supplier linked', 'supplier_name': item.supplier_name})
        return Response({'error': 'supplier_name is required'}, status=400)

    @action(detail=False, methods=['get'])
    def export(self, request):
        import csv
        from django.http import HttpResponse
        qs = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="item_master.csv"'
        writer = csv.writer(response)
        writer.writerow(['SKU', 'Name', 'Category', 'Unit', 'Stock', 'Reorder Level', 'Supplier', 'Cost', 'Price', 'Tax Rule', 'Active'])
        for i in qs:
            writer.writerow([
                i.sku, i.name, i.category, i.unit, i.current_stock, i.reorder_level, 
                i.supplier_name, i.unit_cost, i.unit_price, i.tax_rule, i.is_active
            ])
        return response


class CafeInwardViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = CafeInward.objects.select_related('item', 'cafe_unit').order_by('-date', '-created_at')
    serializer_class = CafeInwardSerializer
    filterset_fields = ['date', 'cafe_unit', 'item']
    permission_classes = [IsStaffOrAbove]
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant, entered_by=self.request.user)

    @action(detail=True, methods=['post'])
    def approve_inward(self, request, pk=None):
        from django.db import transaction
        inward = self.get_object()
        
        if inward.posting_status == CafeInward.PostingStatus.APPROVED:
            return Response({'error': 'Already approved'}, status=400)
            
        with transaction.atomic():
            inward.posting_status = CafeInward.PostingStatus.APPROVED
            inward.approved_by = request.user
            inward.save(update_fields=['posting_status', 'approved_by'])
            
            # Update stock and unit cost
            item = CanteenItem.objects.select_for_update().get(pk=inward.item_id)
            if item.is_track_stock:
                old_val = item.current_stock * item.unit_cost
                new_val = inward.total_cost
                item.current_stock += inward.quantity
                if item.current_stock > 0:
                    item.unit_cost = (old_val + new_val) / item.current_stock
                item.save(update_fields=['current_stock', 'unit_cost'])
                
        return Response({'status': 'Approved and stock updated'})

    @action(detail=False, methods=['get'])
    def export(self, request):
        import csv
        from django.http import HttpResponse
        qs = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="stock_inwards.csv"'
        writer = csv.writer(response)
        writer.writerow(['Date', 'Unit', 'Item', 'Invoice No', 'Batch', 'Expiry', 'Quantity', 'Unit Cost', 'Total Cost', 'Vendor', 'Status'])
        for i in qs:
            writer.writerow([
                i.date, i.cafe_unit.name if i.cafe_unit else '', i.item.name, 
                i.invoice_no, i.batch, i.expiry_date, i.quantity, i.unit_cost, i.total_cost, 
                i.vendor_name, i.posting_status
            ])
        return response


class CafeWastageViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = CafeWastage.objects.select_related('item', 'cafe_unit').order_by('-date', '-created_at')
    serializer_class = CafeWastageSerializer
    filterset_fields = ['date', 'cafe_unit', 'item']
    permission_classes = [IsStaffOrAbove]
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant, entered_by=self.request.user)

    @action(detail=True, methods=['post'])
    def approve_wastage(self, request, pk=None):
        from django.db import transaction
        wastage = self.get_object()
        if wastage.status == CafeWastage.Status.APPROVED:
            return Response({'error': 'Already approved'}, status=400)
            
        with transaction.atomic():
            wastage.status = CafeWastage.Status.APPROVED
            wastage.approved_by = request.user
            wastage.save(update_fields=['status', 'approved_by'])
            
            # Post Stock Reduction
            item = CanteenItem.objects.select_for_update().get(pk=wastage.item_id)
            if item.is_track_stock:
                item.current_stock -= wastage.quantity
                item.save(update_fields=['current_stock'])
                
            from apps.audit.models import ChangeLog
            ChangeLog.objects.create(
                tenant=self.request.tenant,
                table_name='CafeWastage',
                record_id=wastage.id,
                action=ChangeLog.ACTION_UPDATE,
                changed_by=request.user,
                changes={'status': 'APPROVED', 'quantity': str(wastage.quantity), 'cost_impact': str(wastage.value)}
            )
            
        return Response({'status': 'Approved and stock reduced'})

    @action(detail=False, methods=['get'])
    def export(self, request):
        import csv
        from django.http import HttpResponse
        qs = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="wastage_register.csv"'
        writer = csv.writer(response)
        writer.writerow(['Date', 'Unit', 'Item', 'Category', 'Quantity', 'Reason', 'Cost Impact', 'Status'])
        for w in qs:
            writer.writerow([
                w.date, w.cafe_unit.name if w.cafe_unit else '', w.item.name, 
                w.get_category_display(), w.quantity, w.reason, w.value, w.status
            ])
        return response


class CanteenSaleViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = CanteenSale.objects.select_related('item', 'cafe_unit').order_by('-date', '-created_at')
    serializer_class = CanteenSaleSerializer
    filterset_fields = ['date', 'cafe_unit']
    permission_classes = [IsStaffOrAbove]
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant, entered_by=self.request.user)


class AdvertisingSlotViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = AdvertisingSlot.objects.select_related('show__movie').order_by('-show__show_date')
    serializer_class = AdvertisingSlotSerializer
    filterset_fields = ['slot_type', 'show']
    permission_classes = [IsMDOrAdmin]


class CafeExpenseViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = CafeExpense.objects.select_related('cafe_unit').order_by('-date', '-created_at')
    serializer_class = CafeExpenseSerializer
    filterset_fields = ['date', 'cafe_unit']
    permission_classes = [IsStaffOrAbove]


class CafeDashboardViewSet(viewsets.ViewSet):
    permission_classes = [IsStaffOrAbove]
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        tenant = request.tenant
        today = timezone.now().date()
        
        # Today Sales
        today_sales_qs = CanteenSale.objects.filter(tenant=tenant, date=today)
        today_sales = today_sales_qs.aggregate(t=Sum('total'))['t'] or 0
        today_cogs = today_sales_qs.aggregate(t=Sum('cogs'))['t'] or 0
        
        # Gross Margin Estimate
        gross_margin = today_sales - today_cogs
        
        # Fast-moving Items
        fast_moving = list(today_sales_qs.values('item_name').annotate(qty=Sum('quantity')).order_by('-qty')[:5])
        
        # Stock Risk & Reorder Warnings
        risk_items = CanteenItem.objects.filter(
            tenant=tenant, 
            is_track_stock=True, 
            is_active=True,
            current_stock__lte=F('reorder_level')
        )
        stock_risk_count = risk_items.count()
        reorder_warnings = list(risk_items.values('name', 'current_stock', 'reorder_level'))
        
        # Wastage Value (Today)
        wastage = CafeWastage.objects.filter(tenant=tenant, date=today).aggregate(t=Sum('value'))['t'] or 0
        
        return Response({
            'today_sales': today_sales,
            'gross_margin_estimate': gross_margin,
            'fast_moving_items': fast_moving,
            'stock_risk_count': stock_risk_count,
            'reorder_warnings': reorder_warnings,
            'wastage_value': wastage
        })

class CafeDailyConsumptionSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    
    class Meta:
        model = CafeDailyConsumption
        fields = '__all__'
        read_only_fields = ['closing_stock', 'variance', 'created_at', 'status']


class CafeDailyConsumptionViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = CafeDailyConsumption.objects.select_related('item').order_by('-date')
    serializer_class = CafeDailyConsumptionSerializer
    filterset_fields = ['date', 'item', 'status']
    permission_classes = [IsStaffOrAbove]

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant, entered_by=self.request.user)

    @action(detail=False, methods=['post'])
    def run_consumption_engine(self, request):
        from decimal import Decimal
        date = request.data.get('date')
        if not date:
            return Response({'error': 'date is required'}, status=400)
            
        items = CanteenItem.objects.filter(tenant=self.request.tenant, is_track_stock=True)
        results = []
        for item in items:
            sales_qs = CanteenSale.objects.filter(tenant=self.request.tenant, item=item, date=date)
            sold_qty = sales_qs.aggregate(t=Sum('quantity'))['t'] or Decimal('0')
            
            if sold_qty > 0:
                consumption, created = CafeDailyConsumption.objects.get_or_create(
                    tenant=self.request.tenant,
                    date=date,
                    item=item,
                    defaults={
                        'opening_stock': item.current_stock,
                        'sold_qty': sold_qty,
                        'recipe_consumption_qty': sold_qty,
                        'entered_by': request.user
                    }
                )
                if not created and consumption.status == CafeDailyConsumption.Status.DRAFT:
                    consumption.sold_qty = sold_qty
                    consumption.recipe_consumption_qty = sold_qty
                    consumption.opening_stock = item.current_stock
                    consumption.save()
                results.append(consumption.id)
                
        return Response({'status': 'Engine run complete', 'records_generated': len(results)})

    @action(detail=True, methods=['post'])
    def recalculate(self, request, pk=None):
        cons = self.get_object()
        if cons.status == CafeDailyConsumption.Status.APPROVED:
            return Response({'error': 'Cannot recalculate approved record'}, status=400)
            
        cons.variance = cons.manual_adjustment_qty
        cons.closing_stock = cons.opening_stock - cons.recipe_consumption_qty + cons.variance
        cons.save()
        return Response({'status': 'Recalculated', 'closing_stock': cons.closing_stock, 'variance': cons.variance})

    @action(detail=True, methods=['post'])
    def approve_variance(self, request, pk=None):
        from django.db import transaction
        cons = self.get_object()
        if cons.status == CafeDailyConsumption.Status.APPROVED:
            return Response({'error': 'Already approved'}, status=400)
            
        cons.variance = cons.manual_adjustment_qty
        cons.closing_stock = cons.opening_stock - cons.recipe_consumption_qty + cons.variance
        
        with transaction.atomic():
            cons.status = CafeDailyConsumption.Status.APPROVED
            cons.approved_by = request.user
            cons.save()
            
            item = CanteenItem.objects.select_for_update().get(pk=cons.item_id)
            item.current_stock = cons.closing_stock
            item.save(update_fields=['current_stock'])
            
            from apps.audit.models import ChangeLog
            ChangeLog.objects.create(
                tenant=self.request.tenant,
                table_name='CafeDailyConsumption',
                record_id=cons.id,
                action=ChangeLog.ACTION_UPDATE,
                changed_by=request.user,
                changes={'status': 'APPROVED', 'variance': str(cons.variance), 'closing_stock': str(cons.closing_stock)}
            )
            
        return Response({'status': 'Approved and stock updated'})

    @action(detail=False, methods=['get'])
    def export(self, request):
        import csv
        from django.http import HttpResponse
        qs = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="stock_usage.csv"'
        writer = csv.writer(response)
        writer.writerow(['Date', 'Item', 'Opening Stock', 'Sold Qty', 'Recipe Qty', 'Manual Adjustment', 'Variance', 'Closing Stock', 'Status'])
        for i in qs:
            writer.writerow([
                i.date, i.item.name, i.opening_stock, i.sold_qty, i.recipe_consumption_qty,
                i.manual_adjustment_qty, i.variance, i.closing_stock, i.status
            ])
        return response


class CafeReorderAlertSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    item_category = serializers.CharField(source='item.category', read_only=True)
    current_live_stock = serializers.DecimalField(source='item.current_stock', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CafeReorderAlert
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class CafeReorderAlertViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = CafeReorderAlert.objects.select_related('item').order_by('-created_at')
    serializer_class = CafeReorderAlertSerializer
    filterset_fields = ['status', 'item']
    permission_classes = [IsStaffOrAbove]

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)

    @action(detail=False, methods=['post'])
    def generate_alerts(self, request):
        """Scan all tracked items and raise ACTIVE alerts for stock below reorder level."""
        from django.utils import timezone
        today = timezone.now().date()
        tenant = request.tenant

        risk_items = CanteenItem.objects.filter(
            tenant=tenant,
            is_track_stock=True,
            is_active=True,
            current_stock__lte=F('reorder_level')
        )
        created_count = 0
        for item in risk_items:
            # Skip if a non-resolved alert already exists for this item
            if CafeReorderAlert.objects.filter(
                tenant=tenant, item=item
            ).exclude(status=CafeReorderAlert.Status.RESOLVED).exists():
                continue

            last_inward = CafeInward.objects.filter(
                tenant=tenant, item=item,
                posting_status=CafeInward.PostingStatus.APPROVED
            ).order_by('-date').first()

            suggested_qty = max(item.reorder_level * 2 - item.current_stock, item.reorder_level)

            CafeReorderAlert.objects.create(
                tenant=tenant,
                item=item,
                current_stock_at_alert=item.current_stock,
                reorder_level_at_alert=item.reorder_level,
                suggested_reorder_qty=suggested_qty,
                last_purchase_date=last_inward.date if last_inward else None,
                supplier_name=item.supplier_name,
            )
            created_count += 1

        return Response({'status': 'Done', 'alerts_raised': created_count})

    @action(detail=True, methods=['post'])
    def snooze(self, request, pk=None):
        alert = self.get_object()
        snooze_until = request.data.get('snooze_until')
        if not snooze_until:
            return Response({'error': 'snooze_until date is required (YYYY-MM-DD)'}, status=400)
        alert.status = CafeReorderAlert.Status.SNOOZED
        alert.snooze_until = snooze_until
        alert.save(update_fields=['status', 'snooze_until', 'updated_at'])
        return Response({'status': 'Snoozed until', 'snooze_until': snooze_until})

    @action(detail=True, methods=['post'])
    def mark_ordered(self, request, pk=None):
        alert = self.get_object()
        alert.status = CafeReorderAlert.Status.ORDERED
        alert.save(update_fields=['status', 'updated_at'])
        return Response({'status': 'Marked as Ordered'})

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        alert = self.get_object()
        alert.status = CafeReorderAlert.Status.RESOLVED
        alert.save(update_fields=['status', 'updated_at'])
        return Response({'status': 'Alert resolved'})

    @action(detail=True, methods=['post'])
    def create_purchase_intent(self, request, pk=None):
        """Create a Draft CafeInward record from this alert as a purchase intent."""
        from django.utils import timezone
        alert = self.get_object()
        inward = CafeInward.objects.create(
            tenant=alert.tenant,
            item=alert.item,
            date=timezone.now().date(),
            quantity=alert.suggested_reorder_qty,
            unit_cost=alert.item.unit_cost,
            vendor_name=alert.supplier_name,
            posting_status=CafeInward.PostingStatus.DRAFT,
            entered_by=request.user,
        )
        alert.status = CafeReorderAlert.Status.ORDERED
        alert.save(update_fields=['status', 'updated_at'])
        return Response({'status': 'Purchase intent created', 'inward_id': inward.id})


# ─── ADVERTISER MASTER & CAMPAIGN MANAGEMENT ─────────────────────────────────

class AdvertiserSerializer(serializers.ModelSerializer):
    class Meta:
        model = Advertiser
        fields = '__all__'
        read_only_fields = ['tenant', 'created_at']


class AdCampaignSerializer(serializers.ModelSerializer):
    advertiser_name = serializers.CharField(source='advertiser.name', read_only=True)
    screen_name     = serializers.CharField(source='screen_mapping.name', read_only=True)
    show_name       = serializers.CharField(source='show_mapping.movie.title', read_only=True)
    
    ad_type_display = serializers.CharField(source='get_ad_type_display', read_only=True)
    delivery_status_display = serializers.CharField(source='get_delivery_status_display', read_only=True)
    billing_status_display  = serializers.CharField(source='get_billing_status_display', read_only=True)

    class Meta:
        model = AdCampaign
        fields = '__all__'
        read_only_fields = ['tenant', 'created_at', 'updated_at']


class AdvertiserViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = Advertiser.objects.all().order_by('name')
    serializer_class = AdvertiserSerializer
    filterset_fields = ['is_active']
    search_fields = ['name', 'contact_person', 'phone', 'email']
    permission_classes = [IsMDOrAdmin]

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)


class AdCampaignViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = AdCampaign.objects.select_related('advertiser', 'screen_mapping', 'show_mapping').order_by('-campaign_start')
    serializer_class = AdCampaignSerializer
    filterset_fields = ['advertiser', 'ad_type', 'delivery_status', 'billing_status']
    search_fields = ['campaign_name', 'advertiser__name']
    permission_classes = [IsMDOrAdmin]

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)

    # ── Action: Upload Creative ───────────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='upload-creative')
    def upload_creative(self, request, pk=None):
        campaign = self.get_object()
        file_obj = request.FILES.get('file')
        rate_val = request.data.get('rate')

        if file_obj:
            campaign.file_attachment = file_obj
        if rate_val is not None:
            campaign.rate = rate_val
        
        campaign.save()

        # Audit Shield entry
        from apps.audit.models import ChangeLog
        ChangeLog.objects.create(
            tenant=campaign.tenant,
            table_name='AdCampaign',
            record_id=campaign.id,
            action=ChangeLog.ACTION_UPDATE,
            changed_by=request.user,
            changes={'uploaded_creative': file_obj.name if file_obj else 'None', 'rate': str(campaign.rate)}
        )

        return Response(AdCampaignSerializer(campaign).data)

    # ── Action: Map to Screen/Show ────────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='map-screen-show')
    def map_screen_show(self, request, pk=None):
        campaign = self.get_object()
        screen_id = request.data.get('screen_id')
        show_id = request.data.get('show_id')

        if screen_id is not None:
            campaign.screen_mapping_id = screen_id if screen_id != '' else None
        if show_id is not None:
            campaign.show_mapping_id = show_id if show_id != '' else None

        campaign.save()
        return Response(AdCampaignSerializer(campaign).data)

    # ── Action: Close Campaign ────────────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='close')
    def close_campaign(self, request, pk=None):
        campaign = self.get_object()
        campaign.delivery_status = AdCampaign.DeliveryStatus.COMPLETED
        campaign.billing_status = AdCampaign.BillingStatus.INVOICED
        campaign.save(update_fields=['delivery_status', 'billing_status', 'updated_at'])

        # Audit Shield entry
        from apps.audit.models import ChangeLog
        ChangeLog.objects.create(
            tenant=campaign.tenant,
            table_name='AdCampaign',
            record_id=campaign.id,
            action=ChangeLog.ACTION_UPDATE,
            changed_by=request.user,
            changes={'delivery_status': 'COMPLETED', 'billing_status': 'INVOICED'}
        )

        return Response(AdCampaignSerializer(campaign).data)

    # ── Action: Export Billing Sheet ──────────────────────────────────────────
    @action(detail=False, methods=['get'], url_path='export-billing')
    def export_billing(self, request):
        import csv
        from django.http import HttpResponse
        qs = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="advertising_billing_sheet.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'Advertiser', 'Campaign Name', 'Ad Type', 'Start Date', 'End Date',
            'Screen Mapping', 'Linked Show', 'Billing Rate', 'Delivery Status', 'Billing Status'
        ])
        for c in qs:
            writer.writerow([
                c.advertiser.name, c.campaign_name, c.get_ad_type_display(),
                c.campaign_start, c.campaign_end,
                c.screen_mapping.name if c.screen_mapping else 'None',
                str(c.show_mapping) if c.show_mapping else 'None',
                c.rate, c.get_delivery_status_display(), c.get_billing_status_display()
            ])
        return response

