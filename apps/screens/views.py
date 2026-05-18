"""AEC Cinemas – Screens, Shows, Seat Map API"""

from rest_framework import serializers, generics, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Screen, Seat, SeatCategory, Movie, Show, ShowSchedule
from apps.accounts.permissions import IsMDOrAdmin
from apps.tenants.mixins import TenantSafeMixin


class SeatCategorySerializer(serializers.ModelSerializer):
    seat_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = SeatCategory
        fields = ['id', 'screen', 'name', 'price', 'color_code', 'seat_count']
        read_only_fields = ['tenant', 'seat_count']


class SeatSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_price = serializers.DecimalField(source='category.price', max_digits=8, decimal_places=2, read_only=True)
    category_color = serializers.CharField(source='category.color_code', read_only=True)

    class Meta:
        model = Seat
        fields = ['id', 'row', 'number', 'category', 'category_name', 'category_price', 'category_color', 'is_active']


class ScreenSerializer(serializers.ModelSerializer):
    lamp_percentage = serializers.SerializerMethodField()
    lamp_alert = serializers.SerializerMethodField()
    categories = SeatCategorySerializer(many=True, read_only=True)
    sellable_seat_count = serializers.SerializerMethodField()

    class Meta:
        model = Screen
        fields = ['id', 'name', 'screen_type', 'total_seats', 'sellable_seat_count',
                  'lamp_balance', 'lamp_max_hours', 'lamp_alert_threshold',
                  'lamp_percentage', 'lamp_alert', 'is_active', 'categories']
        read_only_fields = ['tenant', 'total_seats']

    def get_lamp_percentage(self, obj):
        return obj.lamp_percentage

    def get_lamp_alert(self, obj):
        return obj.lamp_alert

    def get_sellable_seat_count(self, obj):
        # Use cached total_seats for performance; recalculate only via explicit action
        return obj.total_seats


class MovieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = '__all__'


class ShowSerializer(serializers.ModelSerializer):
    movie_title = serializers.CharField(source='movie.title', read_only=True)
    movie_language = serializers.CharField(source='movie.language', read_only=True)
    movie_duration = serializers.IntegerField(source='movie.duration_minutes', read_only=True)
    movie_poster = serializers.ImageField(source='movie.poster', read_only=True)
    movie_certificate = serializers.CharField(source='movie.certificate', read_only=True)
    screen_name = serializers.CharField(source='screen.name', read_only=True)
    occupancy_percentage = serializers.SerializerMethodField()
    available_seats = serializers.SerializerMethodField()

    class Meta:
        model = Show
        fields = ['id', 'screen', 'screen_name', 'movie', 'movie_title', 'movie_language',
                  'movie_duration', 'movie_poster', 'movie_certificate', 'show_date',
                  'start_time', 'end_time', 'duration_hours', 'status', 'base_price',
                  'is_housefull', 'occupancy_percentage', 'available_seats', 'created_at']

    def get_occupancy_percentage(self, obj):
        return obj.occupancy_percentage

    def get_available_seats(self, obj):
        booked = obj.seat_statuses.filter(state='BOOKED').count()
        return obj.total_seats - booked


class ScreenViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = Screen.objects.all()
    serializer_class = ScreenSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'seats']:
            return [AllowAny()]
        return [IsMDOrAdmin()]

    @action(detail=True, methods=['get'])
    def seats(self, request, pk=None):
        screen = self.get_object()
        seats = screen.seats.filter(is_active=True).select_related('category')
        return Response(SeatSerializer(seats, many=True).data)

    @action(detail=True, methods=['post'], url_path='configure-seats')
    def configure_seats(self, request, pk=None):
        screen = self.get_object()
        categories_data = request.data.get('categories', [])
        from apps.tenants.mixins import get_tenant_from_request
        tenant = get_tenant_from_request(request)

        try:
            screen.seats.all().delete()
            screen.categories.all().delete()
        except Exception:
            return Response({'error': 'Cannot reconfigure layout. Existing bookings depend on current seats.'}, status=400)

        seats_to_create = []
        total_seats = 0
        current_row_ord = ord('A')

        for cat_data in categories_data:
            cat = SeatCategory.objects.create(
                screen=screen,
                tenant=tenant,
                name=cat_data['name'],
                price=cat_data.get('price', 100),
                color_code=cat_data.get('color', '#FFFFFF')
            )
            count = int(cat_data.get('seat_count', 0))
            if count <= 0:
                continue

            rows = count // 20
            rem = count % 20

            for _ in range(rows):
                for i in range(1, 21):
                    seats_to_create.append(Seat(screen=screen, category=cat, row=chr(current_row_ord), number=i))
                current_row_ord += 1
            if rem > 0:
                for i in range(1, rem + 1):
                    seats_to_create.append(Seat(screen=screen, category=cat, row=chr(current_row_ord), number=i))
                current_row_ord += 1
            total_seats += count

        Seat.objects.bulk_create(seats_to_create)
        # Recalculate from real seat rows
        screen.total_seats = total_seats
        screen.save(update_fields=['total_seats'])
        # Backfill seat_count on each category
        for cat in screen.categories.all():
            cat.seat_count = cat.seats.filter(is_active=True).count()
            SeatCategory.objects.filter(pk=cat.pk).update(seat_count=cat.seat_count)
        return Response({'status': 'success', 'total_seats': total_seats})

    @action(detail=True, methods=['post'], url_path='recalculate-seats')
    def recalculate_seats(self, request, pk=None):
        """Force-recalculate total_seats from actual Seat rows."""
        screen = self.get_object()
        count = screen.recalculate_total_seats()
        return Response({'status': 'recalculated', 'total_seats': count})


class SeatCategoryViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = SeatCategory.objects.all()
    serializer_class = SeatCategorySerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsMDOrAdmin()]


class MovieViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = Movie.objects.filter(is_active=True).order_by('-release_date')
    serializer_class = MovieSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'seat_map']:
            return [AllowAny()]
        return [IsMDOrAdmin()]


class ShowViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = Show.objects.select_related('screen', 'movie').order_by('show_date', 'start_time')
    serializer_class = ShowSerializer
    filterset_fields = ['show_date', 'screen', 'movie', 'status']
    search_fields = ['movie__title']

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'seat_map']:
            return [AllowAny()]
        return [IsMDOrAdmin()]

    def perform_destroy(self, instance):
        if instance.seat_statuses.filter(state='BOOKED').exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Cannot delete a show that has confirmed bookings.")
        super().perform_destroy(instance)

    @action(detail=True, methods=['get'], url_path='seat-map')
    def seat_map(self, request, pk=None):
        """Return seats with their live booking state for SVG rendering."""
        show = self.get_object()
        seats = show.screen.seats.filter(is_active=True).select_related('category')
        
        from apps.bookings.models import BookedSeat
        booked_seats = {
            bs.seat_id: bs.booking.source
            for bs in BookedSeat.objects.filter(booking__show=show).select_related('booking')
        }
        
        statuses = {
            ss.seat_id: ss.state
            for ss in show.seat_statuses.select_related('seat')
        }
        
        result = []
        for seat in seats:
            state = statuses.get(seat.id, 'AVAILABLE')
            source = booked_seats.get(seat.id, None)
            
            result.append({
                'id': seat.id,
                'row': seat.row,
                'number': seat.number,
                'category': seat.category.name if seat.category else 'Standard',
                'price': float(seat.category.price) if seat.category else 0,
                'color': seat.category.color_code if seat.category else '#4F46E5',
                'state': state,
                'source': source,
            })
            
        stats = {
            'total_seats': len(seats),
            'online_bookings': sum(1 for s in result if s['state'] == 'BOOKED' and s['source'] in ['APP', 'BMS']),
            'offline_bookings': sum(1 for s in result if s['state'] == 'BOOKED' and s['source'] == 'COUNTER'),
            'total_bookings': sum(1 for s in result if s['state'] == 'BOOKED')
        }
        
        return Response({'show_id': show.id, 'show': str(show), 'seats': result, 'stats': stats})


# ─── SHOW SCHEDULE & CONFLICT DETECTION ────────────────────────────────────────

class ShowScheduleSerializer(serializers.ModelSerializer):
    movie_title = serializers.CharField(source='movie.title', read_only=True)
    screen_name = serializers.CharField(source='screen.name', read_only=True)
    approved_by_username = serializers.CharField(source='approved_by.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ShowSchedule
        fields = '__all__'
        read_only_fields = ['tenant', 'conflict_flag', 'conflict_details', 'schedule_history', 'approved_by', 'created_at', 'updated_at']


class ShowScheduleViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = ShowSchedule.objects.select_related('movie', 'screen', 'approved_by').order_by('show_date', 'start_time')
    serializer_class = ShowScheduleSerializer
    filterset_fields = ['show_date', 'screen', 'movie', 'status', 'conflict_flag']
    search_fields = ['movie__title', 'show_slot', 'conflict_details']
    permission_classes = [IsMDOrAdmin]

    def perform_create(self, serializer):
        # Auto-detect conflict upon schedule draft creation
        from django.utils import timezone
        history_log = [{
            'timestamp': str(timezone.now()),
            'user': self.request.user.username,
            'action': 'CREATED',
            'details': 'Draft show schedule added'
        }]
        
        schedule = serializer.save(
            tenant=self.request.tenant,
            schedule_history=history_log
        )
        self._check_and_update_conflicts(schedule)

    def perform_update(self, serializer):
        from django.utils import timezone
        obj = self.get_object()
        history_log = obj.schedule_history or []
        history_log.append({
            'timestamp': str(timezone.now()),
            'user': self.request.user.username,
            'action': 'UPDATED',
            'details': f"Modified schedule timings or metadata. Date: {obj.show_date}"
        })
        
        schedule = serializer.save(schedule_history=history_log)
        self._check_and_update_conflicts(schedule)

    def _check_and_update_conflicts(self, schedule):
        # Overlap math: Same screen, same show_date, overlaps start/end time
        overlaps = ShowSchedule.objects.filter(
            tenant=schedule.tenant,
            screen=schedule.screen,
            show_date=schedule.show_date
        ).exclude(pk=schedule.id)

        conflicts = []
        s_start = schedule.start_time
        s_end = schedule.end_time

        for other in overlaps:
            # Range overlap formula: (start1 <= end2) and (end1 >= start2)
            if (s_start <= other.end_time and s_end >= other.start_time):
                conflicts.append(
                    f"Overlaps with '{other.movie.title}' (ID {other.id}) scheduled from {other.start_time} to {other.end_time}"
                )

        if conflicts:
            schedule.conflict_flag = True
            schedule.conflict_details = "; ".join(conflicts)
            
            # Auto-generate warning alert inside Alert Center
            from apps.operations.models import OperationalAlert
            OperationalAlert.objects.create(
                tenant=schedule.tenant,
                alert_type=OperationalAlert.AlertType.DCR_MISMATCH,  # Map schedule conflict to alert center
                source_module='Screens / Movie Scheduling',
                severity=OperationalAlert.Severity.WARNING,
                reference_record=f"ShowSchedule-{schedule.id}",
                status=OperationalAlert.Status.TRIGGERED,
                resolution_note=f"Schedule conflict details: {schedule.conflict_details}"
            )
        else:
            schedule.conflict_flag = False
            schedule.conflict_details = ""
        
        schedule.save(update_fields=['conflict_flag', 'conflict_details'])

    # ── Action: Detect Conflict ───────────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='detect-conflict')
    def detect_conflict(self, request, pk=None):
        schedule = self.get_object()
        self._check_and_update_conflicts(schedule)
        return Response({
            'conflict_flag': schedule.conflict_flag,
            'conflict_details': schedule.conflict_details
        })

    # ── Action: Approve Override ──────────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='approve-override')
    def approve_override(self, request, pk=None):
        schedule = self.get_object()
        if not schedule.conflict_flag:
            return Response({'message': 'No conflicts found on this schedule to override.'})

        schedule.holiday_override = True
        schedule.conflict_flag = False
        schedule.approved_by = request.user
        
        from django.utils import timezone
        schedule.schedule_history.append({
            'timestamp': str(timezone.now()),
            'user': request.user.username,
            'action': 'OVERRIDE_APPROVED',
            'details': 'Conflict overridden and authorized by Managing Director.'
        })
        schedule.save()

        # Audit Shield entry
        from apps.audit.models import ChangeLog
        ChangeLog.objects.create(
            tenant=schedule.tenant,
            table_name='ShowSchedule',
            record_id=schedule.id,
            action=ChangeLog.ACTION_UPDATE,
            changed_by=request.user,
            changes={'holiday_override': True, 'conflict_flag': False}
        )

        return Response(ShowScheduleSerializer(schedule).data)

    # ── Action: Pause Show ────────────────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='pause')
    def pause_show(self, request, pk=None):
        schedule = self.get_object()
        schedule.status = ShowSchedule.ScheduleStatus.PAUSED
        
        from django.utils import timezone
        schedule.schedule_history.append({
            'timestamp': str(timezone.now()),
            'user': request.user.username,
            'action': 'PAUSED',
            'details': 'Show execution suspended.'
        })
        schedule.save()

        # Cascade update to live Show records
        Show.objects.filter(
            screen=schedule.screen,
            movie=schedule.movie,
            show_date=schedule.show_date,
            start_time=schedule.start_time
        ).update(status=Show.Status.CANCELLED)

        return Response(ShowScheduleSerializer(schedule).data)

    # ── Action: Resume Show ───────────────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='resume')
    def resume_show(self, request, pk=None):
        schedule = self.get_object()
        schedule.status = ShowSchedule.ScheduleStatus.PUBLISHED
        
        from django.utils import timezone
        schedule.schedule_history.append({
            'timestamp': str(timezone.now()),
            'user': request.user.username,
            'action': 'RESUMED',
            'details': 'Show execution resumed.'
        })
        schedule.save()

        # Cascade update back to live Show records
        Show.objects.filter(
            screen=schedule.screen,
            movie=schedule.movie,
            show_date=schedule.show_date,
            start_time=schedule.start_time
        ).update(status=Show.Status.SCHEDULED)

        return Response(ShowScheduleSerializer(schedule).data)

    # ── Action: View History ──────────────────────────────────────────────────
    @action(detail=True, methods=['get'], url_path='history')
    def view_history(self, request, pk=None):
        schedule = self.get_object()
        return Response(schedule.schedule_history or [])

    # ── Action: Publish Schedule ──────────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='publish')
    def publish_schedule(self, request, pk=None):
        schedule = self.get_object()
        
        # Enforce validation: Must not have active conflict unless MD holiday override is approved
        if schedule.conflict_flag and not schedule.holiday_override:
            return Response({
                'error': 'Cannot publish schedule with active time conflicts. Approve a holiday override first.'
            }, status=400)

        schedule.status = ShowSchedule.ScheduleStatus.PUBLISHED
        from django.utils import timezone
        schedule.schedule_history.append({
            'timestamp': str(timezone.now()),
            'user': request.user.username,
            'action': 'PUBLISHED',
            'details': 'Schedule committed to live engine.'
        })
        schedule.save()

        # Atomically generate or update live Show record
        # Duration hours calculation: duration_minutes / 60
        dur = round(schedule.movie.duration_minutes / 60.0, 2)
        
        show_obj, created = Show.objects.update_or_create(
            screen=schedule.screen,
            movie=schedule.movie,
            show_date=schedule.show_date,
            start_time=schedule.start_time,
            defaults={
                'end_time': schedule.end_time,
                'duration_hours': dur,
                'status': Show.Status.SCHEDULED
            }
        )

        return Response({
            'status': 'Published successfully',
            'schedule_id': schedule.id,
            'show_id': show_obj.id,
            'created_new_show': created
        })

