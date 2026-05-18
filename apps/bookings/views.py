"""AEC Cinemas – Booking Views"""

from rest_framework import serializers, generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Sum, Count
from .models import Booking, BookedSeat, ShowSeatStatus, BMSSyncLog
from .services import BookingService
from apps.accounts.permissions import IsMDOrAdmin


class BookedSeatSerializer(serializers.ModelSerializer):
    seat_label = serializers.SerializerMethodField()

    class Meta:
        model = BookedSeat
        fields = ['id', 'seat', 'seat_label', 'price_paid']

    def get_seat_label(self, obj):
        return f"{obj.seat.row}{obj.seat.number}"


class BookingSerializer(serializers.ModelSerializer):
    booked_seats = BookedSeatSerializer(many=True, read_only=True)
    show_info = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = ['id', 'booking_ref', 'show', 'show_info', 'user', 'customer_name',
                  'customer_phone', 'customer_email', 'source', 'status', 'total_amount',
                  'convenience_fee', 'discount', 'bms_booking_id', 'booked_seats',
                  'created_at', 'cancelled_at', 'notes']
        read_only_fields = ['id', 'booking_ref', 'created_at', 'cancelled_at']

    def get_show_info(self, obj):
        return {
            'movie': obj.show.movie.title,
            'screen': obj.show.screen.name,
            'date': obj.show.show_date,
            'time': obj.show.start_time,
        }


class CreateBookingSerializer(serializers.Serializer):
    show_id = serializers.IntegerField()
    seat_ids = serializers.ListField(child=serializers.IntegerField(), min_length=1)
    source = serializers.ChoiceField(choices=Booking.Source.choices, default='APP')
    customer_name = serializers.CharField(required=False, default='')
    customer_phone = serializers.CharField(required=False, default='')
    customer_email = serializers.EmailField(required=False, default='')


class BMSSyncLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = BMSSyncLog
        fields = '__all__'


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.select_related('show__movie', 'show__screen').order_by('-created_at')
    serializer_class = BookingSerializer
    filterset_fields = ['status', 'source', 'show']
    search_fields = ['booking_ref', 'customer_name', 'customer_phone']

    def get_permissions(self):
        if self.action in ['create']:
            return [AllowAny()]
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsMDOrAdmin()]

    def create(self, request, *args, **kwargs):
        s = CreateBookingSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            booking = BookingService.create_booking(
                show_id=s.validated_data['show_id'],
                seat_ids=s.validated_data['seat_ids'],
                source=s.validated_data['source'],
                user=request.user if request.user.is_authenticated else None,
                customer_name=s.validated_data.get('customer_name', ''),
                customer_phone=s.validated_data.get('customer_phone', ''),
                customer_email=s.validated_data.get('customer_email', ''),
            )
            return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        try:
            booking = BookingService.cancel_booking(pk)
            return Response(BookingSerializer(booking).data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='bms-sync-logs')
    def bms_sync_logs(self, request):
        logs = BMSSyncLog.objects.order_by('-sync_timestamp')[:20]
        return Response(BMSSyncLogSerializer(logs, many=True).data)

    @action(detail=False, methods=['post'], url_path='trigger-bms-sync', permission_classes=[IsMDOrAdmin])
    def trigger_bms_sync(self, request):
        from apps.bookings.tasks import sync_bms_bookings_task
        sync_bms_bookings_task.delay()
        return Response({'message': 'BMS sync triggered.'})


# ─── REFUNDS, CANCELLATIONS & ADJUSTMENTS ──────────────────────────────────────

from .models import BookingCorrection
from apps.tenants.mixins import TenantSafeMixin
from apps.accounts.permissions import IsStaffOrAbove

class BookingCorrectionSerializer(serializers.ModelSerializer):
    booking_ref         = serializers.CharField(source='booking.booking_ref', read_only=True)
    customer_name       = serializers.CharField(source='booking.customer_name', read_only=True)
    customer_email      = serializers.CharField(source='booking.customer_email', read_only=True)
    show_info           = serializers.SerializerMethodField(read_only=True)
    seats               = serializers.SerializerMethodField(read_only=True)
    approved_by_username = serializers.CharField(source='approved_by.username', read_only=True)
    correction_type_display = serializers.CharField(source='get_correction_type_display', read_only=True)
    status_display      = serializers.CharField(source='get_status_display', read_only=True)
    refund_mode_display = serializers.CharField(source='get_refund_mode_display', read_only=True)

    class Meta:
        model = BookingCorrection
        fields = '__all__'
        read_only_fields = ['audit_ref', 'original_amount', 'status', 'approved_by', 'created_at', 'updated_at']

    def get_show_info(self, obj):
        if obj.booking and obj.booking.show:
            return {
                'movie': obj.booking.show.movie.title,
                'screen': obj.booking.show.screen.name,
                'date': str(obj.booking.show.show_date),
                'time': str(obj.booking.show.start_time),
            }
        return None

    def get_seats(self, obj):
        if obj.booking:
            return [f"{s.seat.row}{s.seat.number}" for s in obj.booking.booked_seats.all()]
        return []


class BookingCorrectionViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = BookingCorrection.objects.select_related(
        'booking__show__movie', 'booking__show__screen', 'approved_by'
    ).prefetch_related('booking__booked_seats__seat').order_by('-created_at')
    serializer_class = BookingCorrectionSerializer
    filterset_fields = ['status', 'correction_type', 'booking']
    permission_classes = [IsStaffOrAbove]

    def perform_create(self, serializer):
        # By default, corrections require approval. MD/Admin can post approved corrections directly.
        status = BookingCorrection.Status.PENDING
        approved_by = None
        if self.request.user.role in ['MD', 'ADMIN']:
            status = BookingCorrection.Status.APPROVED
            approved_by = self.request.user

        booking_id = self.request.data.get('booking')
        booking = Booking.objects.get(pk=booking_id)

        serializer.save(
            tenant=self.request.tenant,
            status=status,
            approved_by=approved_by,
            original_amount=booking.total_amount
        )

        # If auto-approved (posted by MD/Admin), apply effects immediately
        if status == BookingCorrection.Status.APPROVED:
            correction = serializer.instance
            self._apply_correction_effects(correction, self.request.user)

    # ── Action: Select Booking (Get Info) ─────────────────────────────────────
    @action(detail=False, methods=['get'], url_path='select-booking')
    def select_booking(self, request):
        booking_ref = request.query_params.get('booking_ref')
        if not booking_ref:
            return Response({'error': 'booking_ref param is required'}, status=400)
        try:
            booking = Booking.objects.get(booking_ref=booking_ref)
            seats = [f"{s.seat.row}{s.seat.number}" for s in booking.booked_seats.all()]
            return Response({
                'booking_id': booking.id,
                'booking_ref': booking.booking_ref,
                'customer_name': booking.customer_name,
                'customer_email': booking.customer_email,
                'status': booking.status,
                'original_amount': str(booking.total_amount),
                'show': {
                    'movie': booking.show.movie.title,
                    'screen': booking.show.screen.name,
                    'date': str(booking.show.show_date),
                    'time': str(booking.show.start_time),
                },
                'seats': seats
            })
        except Booking.DoesNotExist:
            return Response({'error': 'Booking not found'}, status=404)

    # ── Action: Request Refund ────────────────────────────────────────────────
    @action(detail=False, methods=['post'], url_path='request-refund')
    def request_refund(self, request):
        booking_id = request.data.get('booking')
        amount = request.data.get('refund_amount')
        mode = request.data.get('refund_mode', BookingCorrection.RefundMode.UPI)
        reason = request.data.get('reason', '')

        if not booking_id or not amount:
            return Response({'error': 'booking and refund_amount are required'}, status=400)

        booking = Booking.objects.get(pk=booking_id)
        is_auto = request.user.role in ['MD', 'ADMIN']
        status_val = BookingCorrection.Status.APPROVED if is_auto else BookingCorrection.Status.PENDING

        corr = BookingCorrection.objects.create(
            tenant=request.tenant,
            booking=booking,
            correction_type=BookingCorrection.CorrectionType.REFUND,
            original_amount=booking.total_amount,
            refund_amount=amount,
            refund_mode=mode,
            reason=reason,
            status=status_val,
            approved_by=request.user if is_auto else None
        )

        if is_auto:
            self._apply_correction_effects(corr, request.user)

        return Response(BookingCorrectionSerializer(corr).data)

    # ── Action: Request Cancellation ──────────────────────────────────────────
    @action(detail=False, methods=['post'], url_path='request-cancellation')
    def request_cancellation(self, request):
        booking_id = request.data.get('booking')
        reason = request.data.get('reason', '')

        if not booking_id:
            return Response({'error': 'booking is required'}, status=400)

        booking = Booking.objects.get(pk=booking_id)
        is_auto = request.user.role in ['MD', 'ADMIN']
        status_val = BookingCorrection.Status.APPROVED if is_auto else BookingCorrection.Status.PENDING

        corr = BookingCorrection.objects.create(
            tenant=request.tenant,
            booking=booking,
            correction_type=BookingCorrection.CorrectionType.CANCELLATION,
            original_amount=booking.total_amount,
            reason=reason,
            status=status_val,
            approved_by=request.user if is_auto else None
        )

        if is_auto:
            self._apply_correction_effects(corr, request.user)

        return Response(BookingCorrectionSerializer(corr).data)

    # ── Action: Mark Complimentary ────────────────────────────────────────────
    @action(detail=False, methods=['post'], url_path='mark-complimentary')
    def mark_complimentary(self, request):
        booking_id = request.data.get('booking')
        reason = request.data.get('reason', '')

        if not booking_id:
            return Response({'error': 'booking is required'}, status=400)

        booking = Booking.objects.get(pk=booking_id)
        is_auto = request.user.role in ['MD', 'ADMIN']
        status_val = BookingCorrection.Status.APPROVED if is_auto else BookingCorrection.Status.PENDING

        corr = BookingCorrection.objects.create(
            tenant=request.tenant,
            booking=booking,
            correction_type=BookingCorrection.CorrectionType.COMPLIMENTARY,
            original_amount=booking.total_amount,
            reason=reason,
            status=status_val,
            approved_by=request.user if is_auto else None
        )

        if is_auto:
            self._apply_correction_effects(corr, request.user)

        return Response(BookingCorrectionSerializer(corr).data)

    # ── Action: Adjust Manually ───────────────────────────────────────────────
    @action(detail=False, methods=['post'], url_path='adjust-manually')
    def adjust_manually(self, request):
        booking_id = request.data.get('booking')
        after_val = request.data.get('after_value')
        logic = request.data.get('adjustment_logic', '')
        reason = request.data.get('reason', '')

        if not booking_id or after_val is None:
            return Response({'error': 'booking and after_value are required'}, status=400)

        booking = Booking.objects.get(pk=booking_id)
        is_auto = request.user.role in ['MD', 'ADMIN']
        status_val = BookingCorrection.Status.APPROVED if is_auto else BookingCorrection.Status.PENDING

        corr = BookingCorrection.objects.create(
            tenant=request.tenant,
            booking=booking,
            correction_type=BookingCorrection.CorrectionType.ADJUSTMENT,
            original_amount=booking.total_amount,
            before_value=booking.total_amount,
            after_value=after_val,
            adjustment_logic=logic,
            reason=reason,
            status=status_val,
            approved_by=request.user if is_auto else None
        )

        if is_auto:
            self._apply_correction_effects(corr, request.user)

        return Response(BookingCorrectionSerializer(corr).data)

    # ── Action: Approve/Reject ────────────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        correction = self.get_object()
        if correction.status != BookingCorrection.Status.PENDING:
            return Response({'error': 'Correction is already processed'}, status=400)

        correction.status = BookingCorrection.Status.APPROVED
        correction.approved_by = request.user
        correction.save()

        # Apply actual adjustments/revenue updates
        self._apply_correction_effects(correction, request.user)

        return Response({'status': 'Approved', 'audit_ref': correction.audit_ref})

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        correction = self.get_object()
        if correction.status != BookingCorrection.Status.PENDING:
            return Response({'error': 'Correction is already processed'}, status=400)

        correction.status = BookingCorrection.Status.REJECTED
        correction.approved_by = request.user
        correction.save(update_fields=['status', 'approved_by', 'updated_at'])
        return Response({'status': 'Rejected', 'audit_ref': correction.audit_ref})

    # ── Action: Export Logs ───────────────────────────────────────────────────
    @action(detail=False, methods=['get'], url_path='export')
    def export(self, request):
        import csv
        from django.http import HttpResponse
        qs = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="booking_corrections_log.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'Audit Ref', 'Booking Ref', 'Type', 'Original Amount', 'Refund Amt',
            'Before Value', 'After Value', 'Reason', 'Status', 'Approved By', 'Timestamp'
        ])
        for c in qs:
            writer.writerow([
                c.audit_ref, c.booking.booking_ref, c.get_correction_type_display(),
                c.original_amount, c.refund_amount, c.before_value, c.after_value,
                c.reason, c.get_status_display(),
                c.approved_by.username if c.approved_by else '',
                c.created_at
            ])
        return response

    # ── Helper to execute correction rules ────────────────────────────────────
    def _apply_correction_effects(self, corr, user):
        from django.utils import timezone
        booking = corr.booking

        if corr.correction_type == BookingCorrection.CorrectionType.CANCELLATION:
            # Shift booking status, release seats
            booking.status = Booking.Status.CANCELLED
            booking.cancelled_at = timezone.now()
            booking.save(update_fields=['status', 'cancelled_at'])

            # Free seats
            seat_ids = booking.booked_seats.values_list('seat_id', flat=True)
            ShowSeatStatus.objects.filter(
                show=booking.show, seat_id__in=seat_ids
            ).update(state='AVAILABLE')

        elif corr.correction_type == BookingCorrection.CorrectionType.REFUND:
            # Shift booking to REFUNDED, record changes
            booking.status = Booking.Status.REFUNDED
            booking.notes = f"{booking.notes}\n[Refunded ₹{corr.refund_amount} via {corr.get_refund_mode_display()} due to: {corr.reason}]".strip()
            booking.save(update_fields=['status', 'notes'])

            # Free seats (most refunds involve cancellation or seat release)
            seat_ids = booking.booked_seats.values_list('seat_id', flat=True)
            ShowSeatStatus.objects.filter(
                show=booking.show, seat_id__in=seat_ids
            ).update(state='AVAILABLE')

        elif corr.correction_type == BookingCorrection.CorrectionType.COMPLIMENTARY:
            # Set booking amount to 0, tag as complimentary
            booking.total_amount = 0
            booking.notes = f"{booking.notes}\n[Marked Complimentary: {corr.reason}]".strip()
            booking.save(update_fields=['total_amount', 'notes'])

        elif corr.correction_type == BookingCorrection.CorrectionType.ADJUSTMENT:
            # Apply adjusted total amount
            booking.total_amount = corr.after_value
            booking.notes = f"{booking.notes}\n[Adjusted from ₹{corr.before_value} to ₹{corr.after_value} - Logic: {corr.adjustment_logic}]".strip()
            booking.save(update_fields=['total_amount', 'notes'])

        # Write to Audit Shield ChangeLog
        from apps.audit.models import ChangeLog
        ChangeLog.objects.create(
            tenant=corr.tenant,
            table_name='BookingCorrection',
            record_id=corr.id,
            action=ChangeLog.ACTION_UPDATE,
            changed_by=user,
            changes={
                'audit_ref': corr.audit_ref,
                'booking_ref': booking.booking_ref,
                'correction_type': corr.correction_type,
                'status': 'APPROVED',
                'original_amount': str(corr.original_amount),
                'refund_amount': str(corr.refund_amount),
                'after_value': str(corr.after_value),
            }
        )
