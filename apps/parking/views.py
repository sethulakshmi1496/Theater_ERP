"""AEC Cinemas – Parking Analytics Views
Count entry, auto-calculation, heatmap, analytics widgets, and anomaly alerts.
"""

from rest_framework import serializers, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Avg, Max, Count, Q
from django.utils import timezone
from apps.accounts.permissions import IsStaffOrAbove, IsMDOrAdmin
from apps.tenants.mixins import TenantSafeMixin
from .models import ParkingZone, ParkingSlotEntry


# ─── SERIALIZERS ──────────────────────────────────────────────────────────────

class ParkingZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParkingZone
        fields = '__all__'
        read_only_fields = ['created_at'] if hasattr(ParkingZone, 'created_at') else []


class ParkingSlotEntrySerializer(serializers.ModelSerializer):
    zone_name           = serializers.CharField(source='zone.name', read_only=True)
    zone_code           = serializers.CharField(source='zone.zone_code', read_only=True)
    show_slot_display   = serializers.CharField(source='get_show_slot_display', read_only=True)
    special_day_display = serializers.CharField(source='get_special_day_tag_display', read_only=True)
    tw_occupancy_pct    = serializers.FloatField(read_only=True)
    fw_occupancy_pct    = serializers.FloatField(read_only=True)
    tw_fw_ratio         = serializers.FloatField(read_only=True)
    is_high_occupancy   = serializers.BooleanField(read_only=True)

    class Meta:
        model = ParkingSlotEntry
        fields = '__all__'
        read_only_fields = ['tw_closing', 'fw_closing', 'created_at', 'updated_at']


# ─── VIEWSETS ─────────────────────────────────────────────────────────────────

class ParkingZoneViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = ParkingZone.objects.all().order_by('zone_code')
    serializer_class = ParkingZoneSerializer
    filterset_fields = ['is_active', 'is_overflow']
    permission_classes = [IsStaffOrAbove]

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)


class ParkingSlotEntryViewSet(TenantSafeMixin, viewsets.ModelViewSet):
    queryset = ParkingSlotEntry.objects.select_related('zone', 'entered_by', 'verified_by').order_by('-date', 'show_slot')
    serializer_class = ParkingSlotEntrySerializer
    filterset_fields  = ['date', 'zone', 'show_slot', 'special_day_tag', 'overflow_used']
    permission_classes = [IsStaffOrAbove]

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant, entered_by=self.request.user)

    # ── Action: Mark Overflow ─────────────────────────────────────────────────
    @action(detail=True, methods=['post'])
    def mark_overflow(self, request, pk=None):
        entry = self.get_object()
        entry.overflow_used = True
        entry.save(update_fields=['overflow_used', 'updated_at'])
        return Response({'status': 'Overflow marked', 'entry_id': entry.id})

    # ── Action: Tag Holiday / Special Day ─────────────────────────────────────
    @action(detail=True, methods=['post'])
    def tag_special_day(self, request, pk=None):
        entry = self.get_object()
        tag = request.data.get('special_day_tag', ParkingSlotEntry.SpecialDayTag.HOLIDAY)
        if tag not in ParkingSlotEntry.SpecialDayTag.values:
            return Response({'error': f'Invalid tag. Choose from {ParkingSlotEntry.SpecialDayTag.values}'}, status=400)
        entry.special_day_tag = tag
        entry.save(update_fields=['special_day_tag', 'updated_at'])
        return Response({'status': 'Tagged', 'special_day_tag': tag})

    # ── Action: Save Day Summary (bulk upsert for a full date) ─────────────────
    @action(detail=False, methods=['post'])
    def save_day_summary(self, request):
        """
        Accept a list of slot entries for a date and bulk upsert them.
        Body: { "date": "YYYY-MM-DD", "entries": [ { zone, show_slot, tw_*, fw_*, ... } ] }
        """
        date = request.data.get('date')
        entries_data = request.data.get('entries', [])
        if not date or not entries_data:
            return Response({'error': 'date and entries[] are required'}, status=400)

        created, updated = 0, 0
        for ed in entries_data:
            ed['date'] = date
            zone_id   = ed.pop('zone', None)
            show_slot = ed.pop('show_slot', None)
            if not zone_id or not show_slot:
                continue
            obj, is_new = ParkingSlotEntry.objects.update_or_create(
                tenant=request.tenant, zone_id=zone_id, date=date, show_slot=show_slot,
                defaults={**ed, 'entered_by': request.user}
            )
            if is_new:
                created += 1
            else:
                updated += 1
        return Response({'status': 'Day summary saved', 'created': created, 'updated': updated})

    # ── Action: Verify Entry ──────────────────────────────────────────────────
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        entry = self.get_object()
        entry.verified_by = request.user
        entry.save(update_fields=['verified_by', 'updated_at'])
        return Response({'status': 'Verified', 'verified_by': request.user.username})

    # ── Action: Daily Heatmap ─────────────────────────────────────────────────
    @action(detail=False, methods=['get'])
    def daily_heatmap(self, request):
        """
        Returns 2W and 4W occupancy % per zone per show_slot for a given date.
        Query param: ?date=YYYY-MM-DD
        """
        date = request.query_params.get('date', timezone.now().date())
        qs = self.get_queryset().filter(date=date)
        result = []
        for entry in qs:
            result.append({
                'zone': entry.zone.name,
                'zone_code': entry.zone.zone_code,
                'show_slot': entry.show_slot,
                'show_slot_display': entry.get_show_slot_display(),
                'tw_closing': entry.tw_closing,
                'fw_closing': entry.fw_closing,
                'tw_occupancy_pct': entry.tw_occupancy_pct,
                'fw_occupancy_pct': entry.fw_occupancy_pct,
                'overflow_used': entry.overflow_used,
                'is_high_occupancy': entry.is_high_occupancy,
            })
        return Response({'date': str(date), 'heatmap': result})

    # ── Action: Analytics Widgets ─────────────────────────────────────────────
    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """
        Aggregate analytics for dashboard widgets.
        Optional query params: ?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD&zone=<id>
        """
        from datetime import date, timedelta
        tenant = request.tenant
        today  = timezone.now().date()
        from_date = request.query_params.get('from_date', str(today - timedelta(days=30)))
        to_date   = request.query_params.get('to_date', str(today))
        zone_id   = request.query_params.get('zone')

        qs = self.get_queryset().filter(date__range=[from_date, to_date])
        if zone_id:
            qs = qs.filter(zone_id=zone_id)

        # Peak 2W / 4W
        agg = qs.aggregate(
            peak_2w=Max('tw_closing'),
            peak_4w=Max('fw_closing'),
            avg_2w=Avg('tw_closing'),
            avg_4w=Avg('fw_closing'),
            overflow_days=Count('id', filter=Q(overflow_used=True)),
            total_entries=Count('id'),
        )

        # 2W:4W ratio (avoid div/0)
        avg_2w = float(agg['avg_2w'] or 0)
        avg_4w = float(agg['avg_4w'] or 1)
        ratio  = round(avg_2w / avg_4w, 2) if avg_4w else None

        # Weekend trend
        weekend_qs = qs.filter(
            special_day_tag__in=[ParkingSlotEntry.SpecialDayTag.WEEKEND]
        ).aggregate(avg_2w_wknd=Avg('tw_closing'), avg_4w_wknd=Avg('fw_closing'))

        # Holiday trend
        holiday_qs = qs.filter(
            special_day_tag=ParkingSlotEntry.SpecialDayTag.HOLIDAY
        ).aggregate(avg_2w_hol=Avg('tw_closing'), avg_4w_hol=Avg('fw_closing'))

        # Show-slot pressure (which slot has the highest avg occupancy)
        slot_pressure = (
            qs.values('show_slot')
            .annotate(avg_tw=Avg('tw_closing'), avg_fw=Avg('fw_closing'), count=Count('id'))
            .order_by('-avg_fw')
        )

        # Zone occupancy summary
        zone_occ = (
            qs.values('zone', 'zone__name', 'zone__zone_code')
            .annotate(avg_tw=Avg('tw_closing'), avg_fw=Avg('fw_closing'), overflow_count=Count('id', filter=Q(overflow_used=True)))
            .order_by('-avg_fw')
        )

        return Response({
            'period': {'from': from_date, 'to': to_date},
            'peak_2w': agg['peak_2w'],
            'peak_4w': agg['peak_4w'],
            'avg_2w': round(avg_2w, 1),
            'avg_4w': round(avg_4w, 1),
            'tw_fw_ratio': ratio,
            'overflow_frequency': agg['overflow_days'],
            'total_slot_entries': agg['total_entries'],
            'weekend_trend': {
                'avg_2w': float(weekend_qs['avg_2w_wknd'] or 0),
                'avg_4w': float(weekend_qs['avg_4w_wknd'] or 0),
            },
            'holiday_trend': {
                'avg_2w': float(holiday_qs['avg_2w_hol'] or 0),
                'avg_4w': float(holiday_qs['avg_4w_hol'] or 0),
            },
            'show_slot_pressure': list(slot_pressure),
            'zone_occupancy': list(zone_occ),
        })

    # ── Action: Push Anomalies to Alert Center ────────────────────────────────
    @action(detail=False, methods=['post'])
    def push_anomaly_alerts(self, request):
        """
        Scan all entries for today and flag any zones at ≥90% occupancy or overflow.
        Writes alerts to the Audit Shield for surfacing in the Alert Center.
        """
        today = timezone.now().date()
        qs    = self.get_queryset().filter(date=today)
        alerts_pushed = 0

        from apps.audit.models import ChangeLog
        for entry in qs:
            if entry.is_high_occupancy or entry.overflow_used:
                ChangeLog.objects.create(
                    tenant=request.tenant,
                    table_name='ParkingSlotEntry',
                    record_id=entry.id,
                    action=ChangeLog.ACTION_CREATE,
                    changed_by=request.user,
                    changes={
                        'alert': 'PARKING_ANOMALY',
                        'zone': entry.zone.name,
                        'show_slot': entry.show_slot,
                        'tw_occupancy_pct': entry.tw_occupancy_pct,
                        'fw_occupancy_pct': entry.fw_occupancy_pct,
                        'overflow_used': entry.overflow_used,
                    }
                )
                alerts_pushed += 1

        return Response({'status': 'Done', 'alerts_pushed': alerts_pushed, 'date': str(today)})

    # ── Action: Export ────────────────────────────────────────────────────────
    @action(detail=False, methods=['get'])
    def export(self, request):
        import csv
        from django.http import HttpResponse
        qs = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="parking_analytics.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'Date', 'Zone', 'Show Slot', 'Special Day',
            '2W Opening', '2W Entered', '2W Exited', '2W Closing', '2W Occ%',
            '4W Opening', '4W Entered', '4W Exited', '4W Closing', '4W Occ%',
            '2W:4W Ratio', 'Overflow Used', 'Entered By', 'Verified By'
        ])
        for e in qs:
            writer.writerow([
                e.date, e.zone.name, e.get_show_slot_display(), e.get_special_day_tag_display(),
                e.tw_opening, e.tw_entered, e.tw_exited, e.tw_closing, e.tw_occupancy_pct,
                e.fw_opening, e.fw_entered, e.fw_exited, e.fw_closing, e.fw_occupancy_pct,
                e.tw_fw_ratio,
                'Yes' if e.overflow_used else 'No',
                e.entered_by.username if e.entered_by else '',
                e.verified_by.username if e.verified_by else '',
            ])
        return response
