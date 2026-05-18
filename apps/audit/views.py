"""AEC Cinemas – Audit Shield API Views"""
from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import DeletedLog, ChangeLog, StaffSession
from apps.accounts.permissions import IsMDOrAdmin, IsMD
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate
from apps.tenants.mixins import TenantQuerysetMixin


class DeletedLogSerializer(serializers.ModelSerializer):
    deleted_by_name = serializers.CharField(source='deleted_by.full_name', read_only=True)

    class Meta:
        model = DeletedLog
        fields = '__all__'


class ChangeLogSerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source='changed_by.full_name', read_only=True)

    class Meta:
        model = ChangeLog
        fields = '__all__'


class StaffSessionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    duration_hours = serializers.ReadOnlyField()

    class Meta:
        model = StaffSession
        fields = '__all__'


class DeletedLogViewSet(TenantQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    """MD/Admin can VIEW the deletion shadow log. Nobody can delete it."""
    queryset = DeletedLog.objects.all().order_by('-deleted_at')
    serializer_class = DeletedLogSerializer
    permission_classes = [IsMDOrAdmin]
    filterset_fields = ['table_name', 'deleted_by']


class ChangeLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Full paper trail of all changes."""
    queryset = ChangeLog.objects.all().order_by('-timestamp')
    serializer_class = ChangeLogSerializer
    permission_classes = [IsMDOrAdmin]
    filterset_fields = ['table_name', 'action', 'changed_by']


class AuditShieldLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        from .models import AuditShieldLog
        model = AuditShieldLog
        fields = '__all__'
        read_only_fields = ['tenant', 'timestamp']


class AuditShieldLogViewSet(viewsets.ModelViewSet):
    """
    Central operational audit center for all sensitive transactions, approvals,
    acknowledgments, corrections, syncs, and settlement workflows.
    """
    from .models import AuditShieldLog
    queryset = AuditShieldLog.objects.all().order_by('-timestamp')
    serializer_class = AuditShieldLogSerializer
    permission_classes = [IsMDOrAdmin]
    filterset_fields = ['module', 'action_type', 'approval_status', 'alert_status', 'sync_ref']
    search_fields = ['remarks', 'user__username', 'module']

    def get_queryset(self):
        qs = super().get_queryset()
        if hasattr(self.request.user, 'tenant') and self.request.user.tenant:
            qs = qs.filter(tenant=self.request.user.tenant)
        return qs

    def perform_create(self, serializer):
        serializer.save(tenant=getattr(self.request.user, 'tenant', None), user=self.request.user)

    # ── Action: Open Source Record ────────────────────────────────────────────
    @action(detail=True, methods=['get'], url_path='source-record')
    def source_record(self, request, pk=None):
        log = self.get_object()
        
        # Determine redirection paths based on module
        m = log.module.upper()
        redir_path = "/api/audit/logs/"
        if "MOVIE" in m:
            redir_path = f"/api/operations/movies/{log.record_id}/"
        elif "ADVERTISING" in m or "CAMPAIGN" in m:
            redir_path = f"/api/revenue/advertising-campaigns/{log.record_id}/"
        elif "UTILITY" in m:
            redir_path = f"/api/operations/utility-readings/{log.record_id}/"
        elif "GENERATOR" in m:
            redir_path = f"/api/operations/generator-logs/{log.record_id}/"
        elif "LAMP" in m:
            redir_path = f"/api/operations/lamps/{log.record_id}/"
        elif "ASSET" in m:
            redir_path = f"/api/operations/assets/{log.record_id}/"
        elif "DCR" in m:
            redir_path = f"/api/integrations/dcr-reports/{log.record_id}/"
        elif "SETTLEMENT" in m:
            redir_path = f"/api/finance/settlements/{log.record_id}/"
        elif "ALERT" in m:
            redir_path = f"/api/operations/alerts/{log.record_id}/"

        return Response({
            'module': log.module,
            'record_id': log.record_id,
            'redirection_path': redir_path,
            'remarks': log.remarks
        })

    # ── Action: Export Log ────────────────────────────────────────────────────
    @action(detail=False, methods=['get'], url_path='export')
    def export_log(self, request):
        import csv
        from django.http import HttpResponse
        qs = self.filter_queryset(self.get_queryset())
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="audit_shield_export.csv"'
        writer = csv.writer(response)
        
        writer.writerow([
            'Timestamp', 'Module', 'Record ID', 'Action Type', 
            'User', 'Approval Status', 'Alert Status', 'Sync Ref', 'Remarks'
        ])
        
        for item in qs.select_related('user'):
            writer.writerow([
                item.timestamp, item.module, item.record_id, item.action_type,
                item.user.username if item.user else 'System',
                item.approval_status, item.alert_status, item.sync_ref, item.remarks
            ])
        
        return response

    # ── Action: Trace Approval Path ───────────────────────────────────────────
    @action(detail=True, methods=['get'], url_path='trace-approval')
    def trace_approval_path(self, request, pk=None):
        log = self.get_object()
        # Find all audit records affecting the same model record to display timeline
        from .models import AuditShieldLog
        related = AuditShieldLog.objects.filter(
            module=log.module, 
            record_id=log.record_id
        ).order_by('timestamp')
        
        timeline = []
        for r in related:
            timeline.append({
                'timestamp': r.timestamp,
                'action_type': r.action_type,
                'user': r.user.username if r.user else 'System',
                'approval_status': r.approval_status,
                'old_value': r.old_value,
                'new_value': r.new_value,
                'remarks': r.remarks
            })
            
        return Response({
            'module': log.module,
            'record_id': log.record_id,
            'timeline_steps': len(timeline),
            'timeline': timeline
        })

    # ── Action: View Alert Acknowledgment Trail ───────────────────────────────
    @action(detail=False, methods=['get'], url_path='alert-acknowledgments')
    def alert_acknowledgment_trail(self, request):
        from .models import AuditShieldLog
        qs = self.get_queryset().filter(action_type__in=['ACKNOWLEDGE', 'RESOLVE', 'SNOOZE'])
        serializer = AuditShieldLogSerializer(qs, many=True)
        return Response(serializer.data)


class StaffSessionViewSet(TenantQuerysetMixin, viewsets.ModelViewSet):
    queryset = StaffSession.objects.all().order_by('-check_in')
    serializer_class = StaffSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in ['MD', 'ADMIN']:
            return super().get_queryset()
        # Staff can only see their own sessions
        return super().get_queryset().filter(user=user)

    def perform_create(self, serializer):
        from django.utils import timezone
        serializer.save(user=self.request.user, check_in=timezone.now(),
                        shift_date=timezone.localdate())

    @action(detail=True, methods=['post'], url_path='check-out')
    def check_out(self, request, pk=None):
        from django.utils import timezone
        session = self.get_object()
        session.check_out = timezone.now()
        session.status = StaffSession.STATUS_CLOSED
        session.save()
        return Response(StaffSessionSerializer(session).data)


class AdminDeleteVerifyView(viewsets.ViewSet):
    """
    Two-Factor Delete: Admin must re-enter password before deletion is logged.
    Frontend calls this FIRST, then calls the actual delete endpoint.
    """
    permission_classes = [IsMDOrAdmin]

    @action(detail=False, methods=['post'], url_path='verify')
    def verify(self, request):
        password = request.data.get('password')
        if not password:
            return Response({'error': 'Password is required.'}, status=400)

        user = authenticate(request, email=request.user.email, password=password)
        if not user:
            return Response({'error': 'Incorrect password. Deletion aborted.'}, status=403)

        # Return a short-lived verification token stored in session
        request.session['delete_verified'] = True
        request.session['delete_verified_user'] = user.pk
        return Response({'verified': True, 'message': 'Password confirmed. You may proceed with deletion.'})
