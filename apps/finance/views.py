import csv
from django.db.models import Sum, Q, F
from django.utils import timezone
from django.http import HttpResponse
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    Distributor, FilmContract, FilmAdvance, 
    DistributorShare, Settlement, DistributorStatement
)
from .serializers import (
    DistributorSerializer, FilmContractSerializer, 
    FilmAdvanceSerializer, DistributorShareSerializer, 
    SettlementSerializer, DistributorStatementSerializer
)
from apps.accounts.permissions import IsMDOrAdmin
from apps.tenants.mixins import TenantSafeMixin
from apps.audit.models import ChangeLog

class DistributorViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = Distributor.objects.all()
    serializer_class = DistributorSerializer
    permission_classes = [permissions.IsAuthenticated, IsMDOrAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active']
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        distributor = self.get_object()
        distributor.is_active = True
        distributor.save()
        return Response({'status': 'activated'})

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        distributor = self.get_object()
        distributor.is_active = False
        distributor.save()
        return Response({'status': 'deactivated'})

    @action(detail=False, methods=['get'])
    def export(self, request):
        qs = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="distributor_master.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Name', 'Contact Person', 'Phone', 'Email', 'GST ID', 'Status'])
        for d in qs:
            writer.writerow([
                d.name, d.contact_person, d.phone, d.email, d.gst_id, 
                'Active' if d.is_active else 'Inactive'
            ])
            
        return response


class FilmContractViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = FilmContract.objects.select_related('distributor', 'movie')
    serializer_class = FilmContractSerializer
    permission_classes = [permissions.IsAuthenticated, IsMDOrAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['distributor', 'movie', 'status', 'contract_type']

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant, entered_by=self.request.user)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        contract = self.get_object()
        if contract.approval_status in [FilmContract.ApprovalStatus.APPROVED, FilmContract.ApprovalStatus.REJECTED]:
            return Response({'error': 'Contract already processed.'}, status=status.HTTP_400_BAD_REQUEST)
        
        contract.approval_status = FilmContract.ApprovalStatus.APPROVED
        contract.status = FilmContract.Status.ACTIVE
        contract.save()
        ChangeLog.objects.create(
            tenant=self.request.tenant,
            table_name='FilmContract',
            record_id=contract.id,
            action=ChangeLog.ACTION_UPDATE,
            changed_by=request.user,
            changes={'approval_status': 'APPROVED', 'status': 'ACTIVE'}
        )
        return Response({'status': 'Contract Approved and Active'})

    @action(detail=True, methods=['post'])
    def mark_closed(self, request, pk=None):
        contract = self.get_object()
        contract.status = FilmContract.Status.CLOSED
        contract.save()
        return Response({'status': 'Contract Closed'})

    @action(detail=True, methods=['get'])
    def linked_settlements(self, request, pk=None):
        contract = self.get_object()
        settlements = Settlement.objects.filter(contract=contract)
        return Response(SettlementSerializer(settlements, many=True).data)

class FilmAdvanceViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = FilmAdvance.objects.select_related('movie', 'screen', 'contract')
    serializer_class = FilmAdvanceSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['movie', 'screen', 'contract']
    permission_classes = [permissions.IsAuthenticated, IsMDOrAdmin]

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant, entered_by=self.request.user)

class DistributorShareViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = DistributorShare.objects.select_related('show__movie', 'contract')
    serializer_class = DistributorShareSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['show', 'is_settled', 'contract']
    permission_classes = [permissions.IsAuthenticated, IsMDOrAdmin]

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant, entered_by=self.request.user)

class SettlementViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = Settlement.objects.select_related('contract')
    serializer_class = SettlementSerializer
    permission_classes = [permissions.IsAuthenticated, IsMDOrAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['contract', 'status']

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant, generated_by=self.request.user)

    @action(detail=False, methods=['post'])
    def generate(self, request):
        from decimal import Decimal
        contract_id = request.data.get('contract')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')

        if not all([contract_id, start_date, end_date]):
            return Response({'error': 'contract, start_date, and end_date are required'}, status=status.HTTP_400_BAD_REQUEST)

        contract = FilmContract.objects.get(id=contract_id, tenant=self.request.tenant)
        shares = DistributorShare.objects.filter(
            contract=contract, 
            show__show_date__gte=start_date, 
            show__show_date__lte=end_date,
            is_settled=False
        )
        total_share = shares.aggregate(t=Sum('share_amount'))['t'] or Decimal('0')
        total_gross = shares.aggregate(t=Sum('gross_collection'))['t'] or Decimal('0')
        
        # Approximate tax for standard generation if not strictly parsed from DCR yet
        total_tax = total_gross * Decimal('0.18')
        total_nett = total_gross - total_tax

        advances = FilmAdvance.objects.filter(contract=contract)
        total_advance = advances.aggregate(t=Sum('advance_amount'))['t'] or Decimal('0')

        mg_recouped = Decimal('0')

        # MG Logic
        if contract.contract_type == FilmContract.ContractType.MG:
            payable = max(total_share, contract.mg_amount) - total_advance
            mg_recouped = total_share if total_share > 0 else Decimal('0') # Simplistic representation
        elif contract.contract_type == FilmContract.ContractType.FIXED:
            payable = contract.fixed_amount - total_advance
        else:
            payable = total_share - total_advance
            
        settlement = Settlement.objects.create(
            tenant=self.request.tenant,
            contract=contract,
            start_date=start_date,
            end_date=end_date,
            total_gross=total_gross,
            total_tax=total_tax,
            total_nett=total_nett,
            total_share=total_share,
            total_advance=total_advance,
            mg_recouped=mg_recouped,
            net_payable=payable,
            generated_by=request.user
        )
        
        # Mark shares as settled
        shares.update(is_settled=True, settlement_date=timezone.now().date())

        return Response(SettlementSerializer(settlement).data)

    @action(detail=True, methods=['post'])
    def validate_against_dcr(self, request, pk=None):
        from decimal import Decimal
        settlement = self.get_object()
        try:
            from apps.integrations.models import DistrictDCRReport
            dcrs = DistrictDCRReport.objects.filter(
                tenant=self.request.tenant,
                movie_title__iexact=settlement.contract.movie.title,
                report_date__gte=settlement.start_date,
                report_date__lte=settlement.end_date
            )
            dcr_gross = dcrs.aggregate(t=Sum('parsed_gross_revenue'))['t'] or Decimal('0')
            variance = settlement.total_gross - dcr_gross
            
            settlement.status = Settlement.Status.VALIDATED
            settlement.save()
            
            return Response({'status': 'Validated', 'dcr_gross': dcr_gross, 'variance': variance})
        except ImportError:
            return Response({'error': 'DCR module not found'}, status=400)

    @action(detail=True, methods=['patch'])
    def adjust_figures(self, request, pk=None):
        from decimal import Decimal
        settlement = self.get_object()
        if settlement.status in [Settlement.Status.APPROVED, Settlement.Status.PAID]:
            return Response({'error': 'Cannot adjust approved or paid settlements'}, status=400)
            
        other_adjustments = request.data.get('other_adjustments', 0)
        settlement.other_adjustments = Decimal(other_adjustments)
        settlement.net_payable = settlement.net_payable + settlement.other_adjustments
        settlement.save()
        
        ChangeLog.objects.create(
            tenant=self.request.tenant,
            table_name='Settlement',
            record_id=settlement.id,
            action=ChangeLog.ACTION_UPDATE,
            changed_by=request.user,
            changes={'other_adjustments': str(other_adjustments), 'net_payable': str(settlement.net_payable)}
        )
        
        return Response(SettlementSerializer(settlement).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        settlement = self.get_object()
        if settlement.status not in [Settlement.Status.GENERATED, Settlement.Status.VALIDATED]:
            return Response({'error': 'Can only approve GENERATED or VALIDATED settlements.'}, status=status.HTTP_400_BAD_REQUEST)
        
        settlement.status = Settlement.Status.APPROVED
        settlement.approved_by = request.user
        settlement.approval_timestamp = timezone.now()
        settlement.save()
        
        # Log Audit
        ChangeLog.objects.create(
            tenant=self.request.tenant,
            table_name='Settlement',
            record_id=settlement.id,
            action=ChangeLog.ACTION_UPDATE,
            changed_by=request.user,
            changes={'status': 'APPROVED', 'approval_timestamp': str(settlement.approval_timestamp)}
        )
        return Response({'status': 'Approved'})

    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        settlement = self.get_object()
        if settlement.status != Settlement.Status.APPROVED:
            return Response({'error': 'Only APPROVED settlements can be marked as PAID.'}, status=400)
            
        settlement.status = Settlement.Status.PAID
        settlement.save()
        
        ChangeLog.objects.create(
            tenant=self.request.tenant,
            table_name='Settlement',
            record_id=settlement.id,
            action=ChangeLog.ACTION_UPDATE,
            changed_by=request.user,
            changes={'status': 'PAID'}
        )
        return Response({'status': 'Paid'})

    @action(detail=False, methods=['get'])
    def export_settlement(self, request):
        qs = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="settlements.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Contract', 'Start Date', 'End Date', 'Gross', 'Taxes', 'Nett', 'Share', 'Advance', 'MG Recouped', 'Other Adjustments', 'Net Payable', 'Status'])
        for s in qs:
            writer.writerow([
                s.contract, s.start_date, s.end_date, s.total_gross, s.total_tax, s.total_nett,
                s.total_share, s.total_advance, s.mg_recouped, s.other_adjustments, s.net_payable,
                s.get_status_display()
            ])
            
        return response

class DistributorStatementViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = DistributorStatement.objects.select_related('distributor')
    serializer_class = DistributorStatementSerializer
    permission_classes = [permissions.IsAuthenticated, IsMDOrAdmin]

    @action(detail=False, methods=['post'])
    def generate_statement(self, request):
        distributor_id = request.data.get('distributor')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        
        if not all([distributor_id, start_date, end_date]):
            return Response({'error': 'Missing parameters'}, status=400)
            
        dist = Distributor.objects.get(id=distributor_id, tenant=self.request.tenant)
        
        # Bundle APPROVED settlements in this period
        settlements = Settlement.objects.filter(
            tenant=self.request.tenant,
            contract__distributor=dist,
            status__in=[Settlement.Status.APPROVED, Settlement.Status.PAID],
            start_date__gte=start_date,
            end_date__lte=end_date
        )
        
        from decimal import Decimal
        total_gross = settlements.aggregate(t=Sum('total_gross'))['t'] or Decimal('0')
        total_share = settlements.aggregate(t=Sum('total_share'))['t'] or Decimal('0')
        
        total_tax = settlements.aggregate(t=Sum('total_tax'))['t'] or Decimal('0')
        total_advance = settlements.aggregate(t=Sum('total_advance'))['t'] or Decimal('0')
        mg_recouped = settlements.aggregate(t=Sum('mg_recouped'))['t'] or Decimal('0')
        
        total_deductions = total_tax + total_advance + mg_recouped
        total_adjustments = settlements.aggregate(t=Sum('other_adjustments'))['t'] or Decimal('0')
        net_payable = settlements.aggregate(t=Sum('net_payable'))['t'] or Decimal('0')
        
        movies = list(settlements.values_list('contract__movie__title', flat=True).distinct())
        movies_included = ", ".join(movies)
        
        stmt = DistributorStatement.objects.create(
            tenant=self.request.tenant,
            distributor=dist,
            period_start=start_date,
            period_end=end_date,
            movies_included=movies_included,
            total_gross=total_gross,
            total_deductions=total_deductions,
            total_share=total_share,
            total_adjustments=total_adjustments,
            net_payable=net_payable,
            generated_by=request.user
        )
        stmt.settlements.set(settlements)
        
        return Response(DistributorStatementSerializer(stmt).data)

    @action(detail=True, methods=['post'])
    def mark_sent(self, request, pk=None):
        stmt = self.get_object()
        stmt.status = DistributorStatement.Status.SENT
        stmt.sent_timestamp = timezone.now()
        stmt.save()
        ChangeLog.objects.create(
            tenant=self.request.tenant,
            table_name='DistributorStatement',
            record_id=stmt.id,
            action=ChangeLog.ACTION_UPDATE,
            changed_by=request.user,
            changes={'status': 'SENT'}
        )
        return Response({'status': 'Marked Sent'})

    @action(detail=True, methods=['post'])
    def resend(self, request, pk=None):
        stmt = self.get_object()
        stmt.sent_timestamp = timezone.now()
        stmt.save()
        ChangeLog.objects.create(
            tenant=self.request.tenant,
            table_name='DistributorStatement',
            record_id=stmt.id,
            action=ChangeLog.ACTION_UPDATE,
            changed_by=request.user,
            changes={'event': 'RESENT'}
        )
        return Response({'status': 'Resent'})

    @action(detail=True, methods=['post'])
    def archive_statement(self, request, pk=None):
        stmt = self.get_object()
        stmt.status = DistributorStatement.Status.ARCHIVED
        stmt.save()
        ChangeLog.objects.create(
            tenant=self.request.tenant,
            table_name='DistributorStatement',
            record_id=stmt.id,
            action=ChangeLog.ACTION_UPDATE,
            changed_by=request.user,
            changes={'status': 'ARCHIVED'}
        )
        return Response({'status': 'Archived'})

    @action(detail=True, methods=['get'])
    def open_linked_settlements(self, request, pk=None):
        stmt = self.get_object()
        return Response(SettlementSerializer(stmt.settlements.all(), many=True).data)

    @action(detail=False, methods=['get'])
    def export(self, request):
        qs = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="distributor_statements.csv"'
        writer = csv.writer(response)
        writer.writerow(['Distributor', 'Period Start', 'Period End', 'Movies', 'Gross', 'Deductions', 'Share', 'Adjustments', 'Net Payable', 'Status', 'Sent Timestamp'])
        for s in qs:
            writer.writerow([
                s.distributor.name, s.period_start, s.period_end, s.movies_included,
                s.total_gross, s.total_deductions, s.total_share, s.total_adjustments, s.net_payable,
                s.status, s.sent_timestamp
            ])
        return response

class FinanceDashboardViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated, IsMDOrAdmin]

    @action(detail=False, methods=['get'])
    def summary(self, request):
        tenant = request.tenant
        
        advances_paid = FilmAdvance.objects.filter(tenant=tenant).aggregate(t=Sum('advance_amount'))['t'] or 0
        share_pending = DistributorShare.objects.filter(tenant=tenant, is_settled=False).aggregate(t=Sum('share_amount'))['t'] or 0
        
        # MG Exposure = Sum of MG - Advances paid (for MG contracts only)
        mg_contracts = FilmContract.objects.filter(tenant=tenant, contract_type=FilmContract.ContractType.MG, status=FilmContract.Status.ACTIVE)
        total_mg = mg_contracts.aggregate(t=Sum('mg_amount'))['t'] or 0
        mg_advances = FilmAdvance.objects.filter(contract__in=mg_contracts).aggregate(t=Sum('advance_amount'))['t'] or 0
        mg_exposure = total_mg - mg_advances
        
        upcoming_settlements = Settlement.objects.filter(tenant=tenant, status=Settlement.Status.GENERATED).count()
        
        # DCR Validation Pending
        try:
            from apps.integrations.models import DistrictDCRReport
            dcr_pending = DistrictDCRReport.objects.filter(tenant=tenant, status__in=['PARSED', 'VARIANCE_FOUND']).count()
        except ImportError:
            dcr_pending = 0
            
        overdue_statements = 0 # Requires more complex logic based on contract terms, default 0
        
        # Net Film Liability (Pending shares + MG Exposure)
        net_liability = share_pending + (mg_exposure if mg_exposure > 0 else 0)

        return Response({
            'advances_paid': advances_paid,
            'share_pending': share_pending,
            'mg_exposure': mg_exposure,
            'upcoming_settlements': upcoming_settlements,
            'dcr_validation_pending': dcr_pending,
            'overdue_statements': overdue_statements,
            'net_film_liability': net_liability
        })
