"""AEC Cinemas – Reports Views (P&L, Alerts, Export, Drill-down, and Snapshots)"""

import csv
from datetime import date
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework import viewsets, serializers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .services import PLReportEngine
from .models import ManagementSnapshot
from apps.accounts.permissions import IsMDOrAdmin, IsMD
from apps.tenants.mixins import TenantSafeMixin


# ─── SERIALIZERS ──────────────────────────────────────────────────────────────

class ManagementSnapshotSerializer(serializers.ModelSerializer):
    saved_by_username = serializers.CharField(source='saved_by.username', read_only=True)

    class Meta:
        model = ManagementSnapshot
        fields = '__all__'
        read_only_fields = ['tenant', 'saved_by']


# ─── EXISTING VIEWS ───────────────────────────────────────────────────────────

class DailyPLView(APIView):
    permission_classes = [IsMDOrAdmin]

    def get(self, request):
        date_str = request.query_params.get('date', str(date.today()))
        try:
            report_date = date.fromisoformat(date_str)
        except ValueError:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)
        tenant = getattr(request.user, 'tenant', None)
        return Response(PLReportEngine.get_daily_report(report_date, tenant=tenant))


class MonthlyPLView(APIView):
    permission_classes = [IsMDOrAdmin]

    def get(self, request):
        today = date.today()
        month = int(request.query_params.get('month', today.month))
        year = int(request.query_params.get('year', today.year))
        tenant = getattr(request.user, 'tenant', None)
        return Response(PLReportEngine.get_monthly_report(month, year, tenant=tenant))


class AlertsView(APIView):
    permission_classes = [IsMDOrAdmin]

    def get(self, request):
        today = date.today()
        tenant = getattr(request.user, 'tenant', None)
        report = PLReportEngine.get_daily_report(today, tenant=tenant)
        # Add screen lamp alerts
        from apps.screens.models import Screen
        lamp_alerts = []
        screen_qs = Screen.objects.filter(is_active=True)
        if tenant: screen_qs = screen_qs.filter(tenant=tenant)
        for screen in screen_qs:
            if screen.lamp_alert:
                lamp_alerts.append({
                    'type': 'LAMP_ALERT',
                    'screen': screen.name,
                    'balance': float(screen.lamp_balance),
                    'severity': 'critical',
                    'message': f"{screen.name}: {screen.lamp_balance:.1f} hrs remaining on projection lamp!",
                })
        return Response({
            'daily_alerts': report.get('alerts', []),
            'lamp_alerts': lamp_alerts,
            'total_alerts': len(report.get('alerts', [])) + len(lamp_alerts),
        })


class ExportDailyCSVView(APIView):
    permission_classes = [IsMD]

    def get(self, request):
        date_str = request.query_params.get('date', str(date.today()))
        report_date = date.fromisoformat(date_str)
        tenant = getattr(request.user, 'tenant', None)
        report = PLReportEngine.get_daily_report(report_date, tenant=tenant)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="AEC_PL_{date_str}.csv"'
        writer = csv.writer(response)
        writer.writerow(['AEC CINEMAS – Daily P&L Report', date_str])
        writer.writerow([])
        writer.writerow(['INCOME', ''])
        writer.writerow(['Ticket Revenue', f"₹{report['income']['ticket_revenue']:,.2f}"])
        writer.writerow(['Canteen Revenue', f"₹{report['income']['canteen_revenue']:,.2f}"])
        writer.writerow(['Advertising Revenue', f"₹{report['income']['ad_revenue']:,.2f}"])
        writer.writerow(['Total Income', f"₹{report['income']['total']:,.2f}"])
        writer.writerow([])
        writer.writerow(['EXPENSES', ''])
        writer.writerow(['Electricity', f"₹{report['expenses']['electricity']:,.2f}"])
        writer.writerow(['Diesel/Generator', f"₹{report['expenses']['diesel']:,.2f}"])
        writer.writerow(['Distributor Share', f"₹{report['expenses']['distributor_share']:,.2f}"])
        writer.writerow(['Daily Payroll', f"₹{report['expenses']['daily_payroll']:,.2f}"])
        writer.writerow(['Cafe Stock / Wastage', f"₹{report['expenses']['cafe_expenses']:,.2f}"])
        writer.writerow(['General Register Expenses', f"₹{report['expenses']['general_expenses']:,.2f}"])
        writer.writerow(['Total Expenses', f"₹{report['expenses']['total']:,.2f}"])
        writer.writerow([])
        writer.writerow(['NET PROFIT/LOSS', f"₹{report['net_profit']:,.2f}"])
        return response


class ExportMonthlyCSVView(APIView):
    permission_classes = [IsMD]

    def get(self, request):
        today = date.today()
        month = int(request.query_params.get('month', today.month))
        year = int(request.query_params.get('year', today.year))
        tenant = getattr(request.user, 'tenant', None)
        report = PLReportEngine.get_monthly_report(month, year, tenant=tenant)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="AEC_Monthly_PL_{year}_{month:02d}.csv"'
        writer = csv.writer(response)
        writer.writerow([f'AEC CINEMAS – Monthly P&L Report {month}/{year}'])
        writer.writerow([])
        writer.writerow(['INCOME'])
        for k, v in report['income'].items():
            writer.writerow([k.replace('_', ' ').title(), f"₹{v:,.2f}"])
        writer.writerow([])
        writer.writerow(['EXPENSES'])
        for k, v in report['expenses'].items():
            writer.writerow([k.replace('_', ' ').title(), f"₹{v:,.2f}"])
        writer.writerow([])
        writer.writerow(['NET PROFIT/LOSS', f"₹{report['net_profit']:,.2f}"])
        writer.writerow([])
        writer.writerow(['Date', 'Income', 'Expenses', 'Net'])
        for d in report['daily_breakdown']:
            writer.writerow([d['date'], f"₹{d['income']:,.2f}", f"₹{d['expenses']:,.2f}", f"₹{d['net']:,.2f}"])
        return response


# ─── ENHANCED P&L DRILL-DOWN & VARIANCE VIEWS ─────────────────────────────────

class PLCompareView(APIView):
    """Compare performance across two custom dates."""
    permission_classes = [IsMDOrAdmin]

    def get(self, request):
        d1_str = request.query_params.get('date_1')
        d2_str = request.query_params.get('date_2')
        if not d1_str or not d2_str:
            return Response({'error': 'Both date_1 and date_2 query parameters are required.'}, status=400)
        
        try:
            d1 = date.fromisoformat(d1_str)
            d2 = date.fromisoformat(d2_str)
        except ValueError:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)

        tenant = getattr(request.user, 'tenant', None)
        result = PLReportEngine.compare_periods(d1, d2, tenant=tenant)
        return Response(result)


class PLDrillDownView(APIView):
    """Trace specific transaction logs backing a P&L line item."""
    permission_classes = [IsMDOrAdmin]

    def get(self, request):
        p_start_str = request.query_params.get('period_start')
        p_end_str = request.query_params.get('period_end')
        source_module = request.query_params.get('source_module') # BOOKINGS, UTILITY_READINGS, FILM_FINANCE, EXPENSES, CAFE_WASTAGE
        category = request.query_params.get('category') # optional filter for expense type

        if not p_start_str or not p_end_str or not source_module:
            return Response({'error': 'period_start, period_end, and source_module parameters are required.'}, status=400)

        try:
            p_start = date.fromisoformat(p_start_str)
            p_end = date.fromisoformat(p_end_str)
        except ValueError:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)

        tenant = getattr(request.user, 'tenant', None)
        transactions = PLReportEngine.drill_down_source(
            period_start=p_start,
            period_end=p_end,
            source_module=source_module,
            category=category,
            tenant=tenant
        )
        return Response({
            'period_start': p_start_str,
            'period_end': p_end_str,
            'source_module': source_module,
            'transactions_count': len(transactions),
            'transactions': transactions
        })


class PLVarianceDriversView(APIView):
    """Exposes high-impact drivers causing drift compared to standard 30-day baseline average."""
    permission_classes = [IsMDOrAdmin]

    def get(self, request):
        target_str = request.query_params.get('date', str(date.today()))
        try:
            target_date = date.fromisoformat(target_str)
        except ValueError:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)

        tenant = getattr(request.user, 'tenant', None)
        result = PLReportEngine.get_variance_drivers(target_date, tenant=tenant)
        return Response(result)


class ManagementSnapshotViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    """Exposes saving and viewing historical aggregated P&L snapshots for reporting."""
    queryset = ManagementSnapshot.objects.all().order_by('-created_at')
    serializer_class = ManagementSnapshotSerializer
    permission_classes = [IsMDOrAdmin]
    filterset_fields = ['period_type', 'year', 'month']

    def perform_create(self, serializer):
        tenant = getattr(self.request.user, 'tenant', None)
        
        # Pull actual aggregated report to store in snapshot_data
        period_type = serializer.validated_data.get('period_type')
        comments = serializer.validated_data.get('comments', '')
        
        snapshot_data = {}
        if period_type == 'DAILY':
            period_date = serializer.validated_data.get('period_date') or date.today()
            snapshot_data = PLReportEngine.get_daily_report(period_date, tenant=tenant)
        else:
            month = serializer.validated_data.get('month') or date.today().month
            year = serializer.validated_data.get('year') or date.today().year
            snapshot_data = PLReportEngine.get_monthly_report(month, year, tenant=tenant)

        serializer.save(
            tenant=tenant,
            saved_by=self.request.user,
            snapshot_data=snapshot_data
        )

        # Audit Shield entry
        from apps.audit.models import ChangeLog
        ChangeLog.objects.create(
            tenant=tenant,
            table_name='ManagementSnapshot',
            record_id=serializer.instance.id if serializer.instance else 0,
            action=ChangeLog.ACTION_CREATE,
            changed_by=self.request.user,
            changes={'period_type': period_type, 'comments': comments}
        )
