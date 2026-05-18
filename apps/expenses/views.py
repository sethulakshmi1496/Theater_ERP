import csv
from django.utils import timezone
from django.http import HttpResponse
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Expense, ExpenseSubcategory
from .serializers import ExpenseSerializer, ExpenseSubcategorySerializer
from apps.audit.models import ChangeLog

class ExpenseSubcategoryViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSubcategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ExpenseSubcategory.objects.filter(tenant=self.request.tenant)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)

class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['expense_type', 'approval_status', 'posting_status', 'date']
    search_fields = ['paid_to', 'reference_no', 'notes']
    ordering_fields = ['date', 'amount', 'created_at']

    def get_queryset(self):
        return Expense.objects.filter(tenant=self.request.tenant)

    def perform_create(self, serializer):
        serializer.save(
            tenant=self.request.tenant, 
            entered_by=self.request.user
        )
        self._log_audit(serializer.instance, ChangeLog.ACTION_CREATE)

    def perform_update(self, serializer):
        # Already validated by serializer that it's not approved/posted
        serializer.save()
        self._log_audit(serializer.instance, ChangeLog.ACTION_UPDATE)

    def _log_audit(self, instance, action_type):
        try:
            ChangeLog.objects.create(
                tenant=self.request.tenant,
                table_name='Expense',
                record_id=instance.id,
                action=action_type,
                changed_by=self.request.user,
                changes={'status': instance.approval_status, 'amount': str(instance.amount)}
            )
        except Exception:
            pass

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        expense = self.get_object()
        if expense.approval_status != Expense.ApprovalStatus.DRAFT:
            return Response({'error': 'Only draft expenses can be submitted.'}, status=status.HTTP_400_BAD_REQUEST)
        
        expense.approval_status = Expense.ApprovalStatus.PENDING
        expense.save()
        self._log_audit(expense, ChangeLog.ACTION_UPDATE)
        return Response({'status': 'submitted'})

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        expense = self.get_object()
        if expense.approval_status != Expense.ApprovalStatus.PENDING:
            return Response({'error': 'Only pending expenses can be approved.'}, status=status.HTTP_400_BAD_REQUEST)
        
        expense.approval_status = Expense.ApprovalStatus.APPROVED
        expense.approved_by = request.user
        expense.approval_timestamp = timezone.now()
        expense.save()
        self._log_audit(expense, ChangeLog.ACTION_UPDATE)
        return Response({'status': 'approved'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        expense = self.get_object()
        if expense.approval_status != Expense.ApprovalStatus.PENDING:
            return Response({'error': 'Only pending expenses can be rejected.'}, status=status.HTTP_400_BAD_REQUEST)
        
        expense.approval_status = Expense.ApprovalStatus.REJECTED
        expense.save()
        self._log_audit(expense, ChangeLog.ACTION_UPDATE)
        return Response({'status': 'rejected'})

    @action(detail=True, methods=['post'])
    def post_to_pl(self, request, pk=None):
        expense = self.get_object()
        if expense.approval_status != Expense.ApprovalStatus.APPROVED:
            return Response({'error': 'Expense must be approved before posting.'}, status=status.HTTP_400_BAD_REQUEST)
        if expense.posting_status == Expense.PostingStatus.POSTED:
            return Response({'error': 'Expense is already posted.'}, status=status.HTTP_400_BAD_REQUEST)
        
        expense.posting_status = Expense.PostingStatus.POSTED
        expense.save()
        self._log_audit(expense, ChangeLog.ACTION_UPDATE)
        return Response({'status': 'posted'})

    @action(detail=True, methods=['get'])
    def audit_trail(self, request, pk=None):
        logs = ChangeLog.objects.filter(table_name='Expense', record_id=pk).order_by('-timestamp')
        data = [{
            'action': log.action,
            'changed_by': log.changed_by.get_full_name() if log.changed_by else None,
            'timestamp': log.timestamp,
            'changes': log.changes
        } for log in logs]
        return Response(data)

    @action(detail=False, methods=['get'])
    def export(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="expense_register.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Type', 'Amount', 'Paid To', 'Status', 'Entered By', 'Approved By'])
        
        for expense in queryset:
            writer.writerow([
                expense.date,
                expense.get_expense_type_display(),
                expense.amount,
                expense.paid_to,
                expense.get_approval_status_display(),
                expense.entered_by.get_full_name() if expense.entered_by else '',
                expense.approved_by.get_full_name() if expense.approved_by else ''
            ])
            
        return response
