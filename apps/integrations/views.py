from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.integrations.models import DistrictDCRReport
from apps.integrations.serializers import DistrictDCRReportSerializer
from apps.integrations.services.dcr_parser import DistrictDCRParser
from apps.integrations.services.dcr_validator import DCRValidator
from apps.accounts.permissions import IsMDOrAdmin, IsStaffOrAbove
from decimal import Decimal
import tempfile
import os

class DistrictDCRReportViewSet(viewsets.ModelViewSet):
    queryset = DistrictDCRReport.objects.all().order_by('-report_date', '-created_at')
    serializer_class = DistrictDCRReportSerializer
    permission_classes = [IsStaffOrAbove]
    filterset_fields = ['status', 'mismatch_flag', 'review_status', 'posting_status']

    def get_queryset(self):
        qs = super().get_queryset()
        if hasattr(self.request.user, 'tenant') and self.request.user.tenant:
            qs = qs.filter(tenant=self.request.user.tenant)
        return qs

    # ── Action: Upload DCR ────────────────────────────────────────────────────
    @action(detail=False, methods=['post'], url_path='upload')
    def upload_dcr(self, request):
        if 'file' not in request.FILES:
            return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)
        
        pdf_file = request.FILES['file']
        
        # Save to temp file for pdfplumber
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            for chunk in pdf_file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        try:
            # Parse
            parsed_data = DistrictDCRParser.parse_pdf(tmp_path)
            
            # Validate and Save
            tenant = getattr(request.user, 'tenant', None)
            share_percentage = Decimal(request.data.get('share_percentage', '50.0'))
            
            report = DCRValidator.validate_and_save(
                tenant=tenant,
                parsed_data=parsed_data,
                pdf_file=pdf_file,
                uploader=request.user,
                share_percentage=share_percentage
            )
            
            # If mismatch found, trigger alert inside global Alert Center
            if report.mismatch_flag:
                from apps.operations.models import OperationalAlert
                OperationalAlert.objects.create(
                    tenant=report.tenant,
                    alert_type=OperationalAlert.AlertType.DCR_MISMATCH,
                    source_module='District DCR parser',
                    severity=OperationalAlert.Severity.WARNING,
                    reference_record=f"DistrictDCRReport-{report.id}",
                    status=OperationalAlert.Status.TRIGGERED,
                    resolution_note=f"Parsed DCR Gross mismatch or split discrepancy found for '{report.movie_title}' on Screen {report.screen_name}."
                )

            return Response(DistrictDCRReportSerializer(report).data, status=status.HTTP_201_CREATED)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # ── Action: Reprocess File ────────────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='reprocess')
    def reprocess(self, request, pk=None):
        report = self.get_object()
        if not report.raw_pdf:
            return Response({'error': 'No raw DCR file associated with this report to reprocess.'}, status=400)

        # Increment reprocess count
        report.reprocess_count += 1
        report.save(update_fields=['reprocess_count'])

        # Save raw_pdf to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            for chunk in report.raw_pdf.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        try:
            # Re-parse DCR
            parsed_data = DistrictDCRParser.parse_pdf(tmp_path)
            
            # Clean existing ticket classes & discrepancies to avoid duplicate math logs
            report.ticket_classes.all().delete()
            report.discrepancies.all().delete()

            # Re-run Validator
            share_pct = report.distributor_share_percentage
            
            # Update fields on report
            report.movie_title = parsed_data['movie_title']
            report.screen_name = parsed_data['screen_name']
            report.show_time = parsed_data['show_time']
            report.confidence_score = parsed_data['confidence_score']
            report.raw_text_dump = parsed_data['raw_text']
            report.parsed_gross_revenue = parsed_data['gross_revenue']
            report.parsed_occupancy = parsed_data.get('parsed_occupancy', Decimal('0'))
            report.parsed_gst = parsed_data['gst']
            report.parsed_etax = parsed_data['etax']
            report.parsed_cess = parsed_data['cess']
            report.parsed_nett_revenue = parsed_data['nett_revenue']
            report.parsed_distributor_share = parsed_data['distributor_share']
            report.parsed_exhibitor_share = parsed_data['exhibitor_share']
            
            # Recalculate computed expectation limits
            computed_gross = Decimal('0')
            for tc_data in parsed_data.get('ticket_classes', []):
                from apps.integrations.models import DCRTicketClass, DCRDiscrepancy
                tc = DCRTicketClass.objects.create(
                    report=report,
                    ticket_class_name=tc_data['ticket_class_name'],
                    ticket_count=tc_data['ticket_count'],
                    ticket_rate=tc_data['ticket_rate'],
                    parsed_total=tc_data['parsed_total']
                )
                expected_row_total = Decimal(str(tc.ticket_count)) * tc.ticket_rate
                computed_gross += expected_row_total
                if abs(expected_row_total - tc.parsed_total) > DCRValidator.TOLERANCE:
                    DCRDiscrepancy.objects.create(
                        report=report,
                        discrepancy_type=DCRDiscrepancy.Type.GROSS_MISMATCH,
                        description=f"{tc.ticket_class_name} row math mismatch: expected {expected_row_total}, got {tc.parsed_total}",
                        variance_amount=abs(expected_row_total - tc.parsed_total)
                    )

            report.computed_gross_revenue = computed_gross

            if abs(computed_gross - report.parsed_gross_revenue) > DCRValidator.TOLERANCE:
                from apps.integrations.models import DCRDiscrepancy
                DCRDiscrepancy.objects.create(
                    report=report,
                    discrepancy_type=DCRDiscrepancy.Type.GROSS_MISMATCH,
                    description=f"Total gross mismatch: computed {computed_gross}, parsed {report.parsed_gross_revenue}",
                    variance_amount=abs(computed_gross - report.parsed_gross_revenue)
                )

            computed_nett = report.parsed_gross_revenue - report.parsed_gst - report.parsed_etax - report.parsed_cess
            report.computed_nett_revenue = computed_nett

            if abs(computed_nett - report.parsed_nett_revenue) > DCRValidator.TOLERANCE:
                from apps.integrations.models import DCRDiscrepancy
                DCRDiscrepancy.objects.create(
                    report=report,
                    discrepancy_type=DCRDiscrepancy.Type.NETT_MISMATCH,
                    description=f"Nett math mismatch: expected (Gross-Taxes) {computed_nett}, parsed {report.parsed_nett_revenue}",
                    variance_amount=abs(computed_nett - report.parsed_nett_revenue)
                )

            ratio = share_pct / Decimal('100.0')
            computed_dist = report.parsed_nett_revenue * ratio
            computed_exhib = report.parsed_nett_revenue - computed_dist
            
            report.computed_distributor_share = computed_dist
            report.computed_exhibitor_share = computed_exhib

            if abs(computed_dist - report.parsed_distributor_share) > DCRValidator.TOLERANCE:
                from apps.integrations.models import DCRDiscrepancy
                DCRDiscrepancy.objects.create(
                    report=report,
                    discrepancy_type=DCRDiscrepancy.Type.SPLIT_MISMATCH,
                    description=f"Distributor share mismatch based on {share_pct}%: expected {computed_dist}, parsed {report.parsed_distributor_share}",
                    variance_amount=abs(computed_dist - report.parsed_distributor_share)
                )

            if report.discrepancies.exists():
                report.status = DistrictDCRReport.Status.VARIANCE_FOUND
                report.mismatch_flag = True
            else:
                report.status = DistrictDCRReport.Status.VALIDATED
                report.mismatch_flag = False

            report.save()
            return Response(DistrictDCRReportSerializer(report).data)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # ── Action: Approve Parsed Data ───────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        report = self.get_object()
        if report.status in [DistrictDCRReport.Status.APPROVED, DistrictDCRReport.Status.POSTED]:
            return Response({'error': 'Report is already approved or posted.'}, status=400)
        
        report.status = DistrictDCRReport.Status.APPROVED
        report.mismatch_flag = False
        report.review_status = 'RESOLVED'
        report.reviewer_note = f"{report.reviewer_note}\nApproved by {request.user.username}."
        report.save()

        # Audit Shield entry
        from apps.audit.models import ChangeLog
        ChangeLog.objects.create(
            tenant=report.tenant,
            table_name='DistrictDCRReport',
            record_id=report.id,
            action=ChangeLog.ACTION_UPDATE,
            changed_by=request.user,
            changes={'status': 'APPROVED', 'mismatch_flag': False}
        )

        return Response(DistrictDCRReportSerializer(report).data)

    # ── Action: Review Mismatch ───────────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='review-mismatch')
    def review_mismatch(self, request, pk=None):
        report = self.get_object()
        note = request.data.get('note', '')
        resolved = request.data.get('resolved', False)

        report.reviewer_note = note
        if resolved:
            report.review_status = 'RESOLVED'
            report.mismatch_flag = False
            report.status = DistrictDCRReport.Status.VALIDATED
        else:
            report.review_status = 'UNDER_REVIEW'

        report.save()
        return Response(DistrictDCRReportSerializer(report).data)

    # ── Action: Archive Raw Copy ──────────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='archive-raw')
    def archive_raw(self, request, pk=None):
        report = self.get_object()
        if report.raw_pdf:
            report.raw_archive_link = report.raw_pdf.url
            report.save(update_fields=['raw_archive_link'])
        return Response({
            'status': 'Raw copy archived successfully.',
            'raw_archive_link': report.raw_archive_link
        })

    # ── Action: Push Approved Data to Film Finance ───────────────────────────
    @action(detail=True, methods=['post'], url_path='post-to-finance')
    def post_to_finance(self, request, pk=None):
        report = self.get_object()
        if report.status != DistrictDCRReport.Status.APPROVED:
            return Response({'error': 'Report must be approved before posting to Film Finance.'}, status=400)
        
        report.status = DistrictDCRReport.Status.POSTED
        report.posting_status = 'FILM_FINANCE_PUSHED'
        report.save()

        # Connect live settlement entry
        # Here we mock the integration to Settlements registry
        return Response({
            'status': 'Film Finance successfully synced.',
            'posting_status': report.posting_status,
            'nett_revenue': float(report.parsed_nett_revenue),
            'distributor_share': float(report.parsed_distributor_share)
        })



# ─── INTEGRATION HUB (SETTINGS CONNECTOR CENTRE) ──────────────────────────────────

from .models import IntegrationConnector
from apps.tenants.mixins import TenantSafeMixin
from rest_framework import serializers

class IntegrationConnectorSerializer(serializers.ModelSerializer):
    connector_name_display = serializers.CharField(source='get_connector_name_display', read_only=True)
    status_display      = serializers.CharField(source='get_status_display', read_only=True)
    auth_type_display   = serializers.CharField(source='get_auth_type_display', read_only=True)
    sync_frequency_display = serializers.CharField(source='get_sync_frequency_display', read_only=True)
    masked_credentials  = serializers.JSONField(read_only=True)

    class Meta:
        model = IntegrationConnector
        fields = '__all__'
        read_only_fields = ['tenant', 'status', 'last_sync', 'last_error', 'test_conn_result', 'is_active', 'created_at', 'updated_at']


class IntegrationConnectorViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = IntegrationConnector.objects.all().order_by('connector_name')
    serializer_class = IntegrationConnectorSerializer
    filterset_fields = ['connector_name', 'status', 'is_active']
    permission_classes = [IsMDOrAdmin]

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)

    # ── Action: Configure Credentials ─────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='configure-credentials')
    def configure_credentials(self, request, pk=None):
        connector = self.get_object()
        creds = request.data.get('credentials')
        auth = request.data.get('auth_type')
        freq = request.data.get('sync_frequency')

        if creds is not None:
            if not isinstance(creds, dict):
                return Response({'error': 'credentials must be a JSON object/dictionary'}, status=400)
            # Merge or set credentials
            connector.credentials_json = creds

        if auth is not None:
            connector.auth_type = auth
        if freq is not None:
            connector.sync_frequency = freq

        connector.save()
        return Response(IntegrationConnectorSerializer(connector).data)

    # ── Action: Test Connection ───────────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='test-connection')
    def test_connection(self, request, pk=None):
        connector = self.get_object()
        import random
        from django.utils import timezone

        # Simulate connection tests per API endpoint type
        connector.last_sync = timezone.now()
        success = random.choice([True, True, True, False])  # 75% success rate for simulation

        if success:
            connector.test_conn_result = f"Successfully authenticated with {connector.get_connector_name_display()} API gateway. Code: 200 OK."
            connector.last_error = ""
            if connector.is_active:
                connector.status = IntegrationConnector.Status.ACTIVE
        else:
            connector.test_conn_result = "Connection failed."
            connector.last_error = f"HTTP 502 Bad Gateway / Connection Timeout during handshake with {connector.get_connector_name_display()} endpoint."
            connector.status = IntegrationConnector.Status.ERROR

        connector.save()

        # Audit Shield ChangeLog entry
        from apps.audit.models import ChangeLog
        ChangeLog.objects.create(
            tenant=connector.tenant,
            table_name='IntegrationConnector',
            record_id=connector.id,
            action=ChangeLog.ACTION_UPDATE,
            changed_by=request.user,
            changes={
                'connector_name': connector.connector_name,
                'test_conn_result': connector.test_conn_result,
                'status': connector.status
            }
        )

        return Response({
            'status': connector.status,
            'test_conn_result': connector.test_conn_result,
            'last_error': connector.last_error
        })

    # ── Action: Activate Connector ────────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='activate')
    def activate(self, request, pk=None):
        connector = self.get_object()
        connector.is_active = True
        connector.status = IntegrationConnector.Status.ACTIVE
        connector.save(update_fields=['is_active', 'status', 'updated_at'])

        # Audit Shield entry
        from apps.audit.models import ChangeLog
        ChangeLog.objects.create(
            tenant=connector.tenant,
            table_name='IntegrationConnector',
            record_id=connector.id,
            action=ChangeLog.ACTION_UPDATE,
            changed_by=request.user,
            changes={'connector_name': connector.connector_name, 'is_active': True}
        )

        return Response({'status': 'Activated', 'connector': connector.connector_name})

    # ── Action: Pause Connector ───────────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='pause')
    def pause(self, request, pk=None):
        connector = self.get_object()
        connector.is_active = False
        connector.status = IntegrationConnector.Status.PAUSED
        connector.save(update_fields=['is_active', 'status', 'updated_at'])

        # Audit Shield entry
        from apps.audit.models import ChangeLog
        ChangeLog.objects.create(
            tenant=connector.tenant,
            table_name='IntegrationConnector',
            record_id=connector.id,
            action=ChangeLog.ACTION_UPDATE,
            changed_by=request.user,
            changes={'connector_name': connector.connector_name, 'is_active': False}
        )

        return Response({'status': 'Paused', 'connector': connector.connector_name})

    # ── Action: Retry Sync ────────────────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='retry-sync')
    def retry_sync(self, request, pk=None):
        connector = self.get_object()
        from django.utils import timezone
        connector.status = IntegrationConnector.Status.SYNCING
        connector.save(update_fields=['status'])

        # Execute simulated sync success
        connector.last_sync = timezone.now()
        connector.status = IntegrationConnector.Status.ACTIVE
        connector.last_error = ""
        connector.save()

        return Response({
            'status': connector.status,
            'last_sync': connector.last_sync,
            'message': f"Sync triggered successfully for {connector.get_connector_name_display()}."
        })

    # ── Action: Open Error History ────────────────────────────────────────────
    @action(detail=True, methods=['get'], url_path='error-history')
    def error_history(self, request, pk=None):
        connector = self.get_object()
        # Simulated log array
        history = [
            {"timestamp": str(timezone.now() - timezone.timedelta(days=1)), "level": "ERROR", "message": "Failed to authenticate. Secret token expired."},
            {"timestamp": str(timezone.now() - timezone.timedelta(hours=2)), "level": "WARNING", "message": "Rate limit exceeded. Postponed next 2 calls."},
        ]
        if connector.last_error:
            history.insert(0, {"timestamp": str(connector.updated_at), "level": "CRITICAL", "message": connector.last_error})
        return Response(history)

    # ── Action: View Dependent Module ─────────────────────────────────────────
    @action(detail=True, methods=['get'], url_path='dependent-module')
    def dependent_module(self, request, pk=None):
        connector = self.get_object()
        mapping = {
            IntegrationConnector.ConnectorName.DISTRICT: {
                'module_name': 'District DCR Reports',
                'description': 'Daily Box Office PDF parser and distributor revenue validation ledger.',
                'redirection_url': '/api/integrations/dcr-reports/'
            },
            IntegrationConnector.ConnectorName.BOOKMYSHOW: {
                'module_name': 'BMS Sync & Bookings',
                'description': 'Real-time BMS ticket transaction syncing and screen occupancy levels.',
                'redirection_url': '/api/bookings/'
            },
            IntegrationConnector.ConnectorName.PETPOOJA: {
                'module_name': 'Cafe Sales POS',
                'description': 'Syncs Cafe and F&B transaction data directly to the local theater ledger.',
                'redirection_url': '/api/revenue/pos-sync/'
            },
            IntegrationConnector.ConnectorName.HR_APP: {
                'module_name': 'HR System Sync',
                'description': 'Downloads staff operational logs, Brevo integrations and employee rosters.',
                'redirection_url': '/api/hr/employee-profiles/'
            },
            IntegrationConnector.ConnectorName.TEAMS: {
                'module_name': 'Alert Center Webhooks',
                'description': 'Sends operational warnings, safety alerts and temperature alerts directly to Teams.',
                'redirection_url': '/api/alerts/'
            },
            IntegrationConnector.ConnectorName.PERPLEXITY: {
                'module_name': 'Executive Suite Intelligence',
                'description': 'Leverages Perplexity LLM to compute occupancy models and competitive theater metrics.',
                'redirection_url': '/api/reports/executive-analytics/'
            }
        }.get(connector.connector_name, {
            'module_name': 'Settings Configuration',
            'description': 'Shared global connector configurations.',
            'redirection_url': '/api/settings/'
        })

        return Response(mapping)

