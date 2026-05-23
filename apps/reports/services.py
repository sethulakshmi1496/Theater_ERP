"""AEC Cinemas – P&L Report Engine & MD Intelligence"""

from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal


class PLReportEngine:
    """Central P&L aggregation for Daily and Monthly reports."""

    @staticmethod
    def get_daily_report(report_date: date, tenant=None) -> dict:
        from apps.bookings.models import Booking
        from apps.revenue.models import CanteenSale, AdvertisingSlot
        from apps.operations.models import UtilityReading, GeneratorLog
        from apps.finance.models import DistributorShare
        from apps.payroll.models import PayrollEntry
        from apps.expenses.models import Expense

        # ── INCOME ────────────────────────────────────────────────────
        booking_qs = Booking.objects.filter(
            show__show_date=report_date,
            status__in=['CONFIRMED', 'CHECKED_IN']
        )
        if tenant: booking_qs = booking_qs.filter(tenant=tenant)
        ticket_revenue = booking_qs.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

        canteen_qs = CanteenSale.objects.filter(date=report_date)
        if tenant: canteen_qs = canteen_qs.filter(tenant=tenant)
        canteen_gross = canteen_qs.aggregate(total=Sum('total'))['total'] or Decimal('0')

        from apps.revenue.models import CafeExpense
        cafe_exp_qs = CafeExpense.objects.filter(date=report_date)
        if tenant: cafe_exp_qs = cafe_exp_qs.filter(tenant=tenant)
        cafe_expense = cafe_exp_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')

        canteen_revenue = canteen_gross - cafe_expense

        ad_qs = AdvertisingSlot.objects.filter(show__show_date=report_date)
        if tenant: ad_qs = ad_qs.filter(tenant=tenant)
        ad_revenue = ad_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')

        total_income = ticket_revenue + canteen_revenue + ad_revenue

        # ── EXPENSES ───────────────────────────────────────────────────
        elec_qs = UtilityReading.objects.filter(reading_date=report_date, meter__meter_type='ELECTRICITY')
        if tenant: elec_qs = elec_qs.filter(tenant=tenant)
        elec_charges = elec_qs.aggregate(total=Sum('total_cost'))['total'] or Decimal('0')

        gen_qs = GeneratorLog.objects.filter(date=report_date)
        if tenant: gen_qs = gen_qs.filter(tenant=tenant)
        diesel_cost = gen_qs.aggregate(total=Sum('diesel_cost'))['total'] or Decimal('0')

        dist_qs = DistributorShare.objects.filter(show__show_date=report_date)
        if tenant: dist_qs = dist_qs.filter(tenant=tenant)
        distributor_cost = dist_qs.aggregate(total=Sum('share_amount'))['total'] or Decimal('0')

        # Payroll: prorate monthly salary to day (÷ working days in month)
        days_in_month = 26  # standard working days
        pay_qs = PayrollEntry.objects.filter(month=report_date.month, year=report_date.year, status='PAID')
        if tenant: pay_qs = pay_qs.filter(tenant=tenant)
        payroll = pay_qs.aggregate(total=Sum('net_salary'))['total'] or Decimal('0')
        daily_payroll = payroll / Decimal(str(days_in_month))

        # petty and general approved/posted expenses from Expense model
        expense_qs = Expense.objects.filter(date=report_date, approval_status='APPROVED')
        if tenant: expense_qs = expense_qs.filter(tenant=tenant)
        general_expenses_total = expense_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')

        general_exp_breakdown = {}
        for item in expense_qs.values('expense_type').annotate(total=Sum('amount')):
            t_name = item['expense_type']
            general_exp_breakdown[t_name] = float(item['total'])

        total_expenses = elec_charges + diesel_cost + distributor_cost + daily_payroll + cafe_expense + general_expenses_total

        net = total_income - total_expenses

        # ── ALERTS ────────────────────────────────────────────────────
        alerts = []
        if ticket_revenue > 0 and elec_charges > ticket_revenue:
            alerts.append({
                'type': 'LOSS_SHOW',
                'message': f"Electricity cost (₹{elec_charges:,.2f}) exceeds ticket revenue (₹{ticket_revenue:,.2f}). Loss-making day!",
                'severity': 'critical',
            })

        # Lamp alerts
        from apps.screens.models import Screen
        screen_qs = Screen.objects.filter(is_active=True)
        if tenant: screen_qs = screen_qs.filter(tenant=tenant)
        for screen in screen_qs:
            if screen.lamp_alert:
                alerts.append({
                    'type': 'LAMP_ALERT',
                    'message': f"{screen.name} projection lamp: Only {screen.lamp_balance:.1f} hours remaining!",
                    'severity': 'critical',
                })

        bookings_count = booking_qs.count()
        tickets_sold = booking_qs.aggregate(seats=Count('booked_seats'))['seats'] or 0

        # Roll up by cafe_unit
        cafe_units_breakdown = {}
        for sale in canteen_qs.values('cafe_unit__name').annotate(total=Sum('total')):
            unit_name = sale['cafe_unit__name'] or 'Main Counter'
            if unit_name not in cafe_units_breakdown: cafe_units_breakdown[unit_name] = {'revenue': Decimal('0'), 'expenses': Decimal('0')}
            cafe_units_breakdown[unit_name]['revenue'] += sale['total']

        for exp in cafe_exp_qs.values('cafe_unit__name').annotate(total=Sum('amount')):
            unit_name = exp['cafe_unit__name'] or 'Main Counter'
            if unit_name not in cafe_units_breakdown: cafe_units_breakdown[unit_name] = {'revenue': Decimal('0'), 'expenses': Decimal('0')}
            cafe_units_breakdown[unit_name]['expenses'] += exp['total']

        cafe_units_summary = [
            {'name': name, 'revenue': float(data['revenue']), 'expenses': float(data['expenses']), 'net': float(data['revenue'] - data['expenses'])}
            for name, data in cafe_units_breakdown.items()
        ]

        return {
            'date': str(report_date),
            'income': {
                'ticket_revenue': float(ticket_revenue),
                'canteen_revenue': float(canteen_gross),
                'ad_revenue': float(ad_revenue),
                'total': float(total_income),
            },
            'expenses': {
                'electricity': float(elec_charges),
                'diesel': float(diesel_cost),
                'distributor_share': float(distributor_cost),
                'daily_payroll': float(daily_payroll),
                'cafe_expenses': float(cafe_expense),
                'general_expenses': float(general_expenses_total),
                'general_expenses_breakdown': general_exp_breakdown,
                'total': float(total_expenses),
            },
            'net_profit': float(net),
            'is_profitable': net >= 0,
            'bookings_count': bookings_count,
            'tickets_sold': tickets_sold,
            'alerts': alerts,
            'cafe_units_breakdown': cafe_units_summary,
            'drill_down_paths': {
                'expense_register': f"/api/expenses/expenses/?date={report_date}",
                'utility_readings': f"/api/operations/utility-readings/?date={report_date}",
                'film_finance': f"/api/finance/distributor-shares/?date={report_date}",
                'bookings_corrections': f"/api/bookings/bookings/?date={report_date}",
                'cafe_wastage': f"/api/revenue/cafe-expenses/?date={report_date}"
            }
        }

    @staticmethod
    def get_monthly_report(month: int, year: int, tenant=None) -> dict:
        from apps.bookings.models import Booking
        from apps.revenue.models import CanteenSale, AdvertisingSlot
        from apps.operations.models import UtilityReading, GeneratorLog
        from apps.finance.models import DistributorShare, FilmAdvance
        from apps.payroll.models import PayrollEntry
        from apps.expenses.models import Expense

        # Date range
        from calendar import monthrange
        _, days = monthrange(year, month)
        start = date(year, month, 1)
        end = date(year, month, days)

        booking_qs = Booking.objects.filter(
            show__show_date__range=[start, end],
            status__in=['CONFIRMED', 'CHECKED_IN']
        )
        if tenant: booking_qs = booking_qs.filter(tenant=tenant)
        ticket_revenue = booking_qs.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

        canteen_qs = CanteenSale.objects.filter(date__range=[start, end])
        if tenant: canteen_qs = canteen_qs.filter(tenant=tenant)
        canteen_gross = canteen_qs.aggregate(total=Sum('total'))['total'] or Decimal('0')

        from apps.revenue.models import CafeExpense
        cafe_exp_qs = CafeExpense.objects.filter(date__range=[start, end])
        if tenant: cafe_exp_qs = cafe_exp_qs.filter(tenant=tenant)
        cafe_expense = cafe_exp_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')

        canteen_revenue = canteen_gross - cafe_expense

        ad_qs = AdvertisingSlot.objects.filter(show__show_date__range=[start, end])
        if tenant: ad_qs = ad_qs.filter(tenant=tenant)
        ad_revenue = ad_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')

        total_income = ticket_revenue + canteen_revenue + ad_revenue

        elec_qs = UtilityReading.objects.filter(reading_date__range=[start, end], meter__meter_type='ELECTRICITY')
        if tenant: elec_qs = elec_qs.filter(tenant=tenant)
        elec_charges = elec_qs.aggregate(total=Sum('total_cost'))['total'] or Decimal('0')

        gen_qs = GeneratorLog.objects.filter(date__range=[start, end])
        if tenant: gen_qs = gen_qs.filter(tenant=tenant)
        diesel_cost = gen_qs.aggregate(total=Sum('diesel_cost'))['total'] or Decimal('0')

        dist_qs = DistributorShare.objects.filter(show__show_date__range=[start, end])
        if tenant: dist_qs = dist_qs.filter(tenant=tenant)
        distributor_cost = dist_qs.aggregate(total=Sum('share_amount'))['total'] or Decimal('0')

        film_advances_qs = FilmAdvance.objects.filter(release_date__range=[start, end])
        if tenant: film_advances_qs = film_advances_qs.filter(tenant=tenant)
        film_advances = film_advances_qs.aggregate(total=Sum('advance_amount'))['total'] or Decimal('0')

        pay_qs = PayrollEntry.objects.filter(month=month, year=year)
        if tenant: pay_qs = pay_qs.filter(tenant=tenant)
        payroll = pay_qs.aggregate(total=Sum('net_salary'))['total'] or Decimal('0')

        expense_qs = Expense.objects.filter(date__range=[start, end], approval_status='APPROVED')
        if tenant: expense_qs = expense_qs.filter(tenant=tenant)
        general_expenses_total = expense_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')

        general_exp_breakdown = {}
        for item in expense_qs.values('expense_type').annotate(total=Sum('amount')):
            t_name = item['expense_type']
            general_exp_breakdown[t_name] = float(item['total'])

        total_expenses = elec_charges + diesel_cost + distributor_cost + film_advances + payroll + cafe_expense + general_expenses_total
        net = total_income - total_expenses

        # Day-by-day breakdown
        daily = []
        for d in range(1, days + 1):
            day_date = date(year, month, d)
            day_report = PLReportEngine.get_daily_report(day_date, tenant=tenant)
            daily.append({
                'date': str(day_date),
                'income': day_report['income']['total'],
                'expenses': day_report['expenses']['total'],
                'net': day_report['net_profit'],
            })

        # Roll up by cafe_unit
        cafe_units_breakdown = {}
        for sale in canteen_qs.values('cafe_unit__name').annotate(total=Sum('total')):
            unit_name = sale['cafe_unit__name'] or 'Main Counter'
            if unit_name not in cafe_units_breakdown: cafe_units_breakdown[unit_name] = {'revenue': Decimal('0'), 'expenses': Decimal('0')}
            cafe_units_breakdown[unit_name]['revenue'] += sale['total']

        for exp in cafe_exp_qs.values('cafe_unit__name').annotate(total=Sum('amount')):
            unit_name = exp['cafe_unit__name'] or 'Main Counter'
            if unit_name not in cafe_units_breakdown: cafe_units_breakdown[unit_name] = {'revenue': Decimal('0'), 'expenses': Decimal('0')}
            cafe_units_breakdown[unit_name]['expenses'] += exp['total']

        cafe_units_summary = [
            {'name': name, 'revenue': float(data['revenue']), 'expenses': float(data['expenses']), 'net': float(data['revenue'] - data['expenses'])}
            for name, data in cafe_units_breakdown.items()
        ]

        return {
            'month': month, 'year': year,
            'income': {
                'ticket_revenue': float(ticket_revenue),
                'canteen_revenue': float(canteen_gross),
                'ad_revenue': float(ad_revenue),
                'total': float(total_income),
            },
            'expenses': {
                'electricity': float(elec_charges),
                'diesel': float(diesel_cost),
                'distributor_share': float(distributor_cost),
                'film_advances': float(film_advances),
                'payroll': float(payroll),
                'cafe_expenses': float(cafe_expense),
                'general_expenses': float(general_expenses_total),
                'general_expenses_breakdown': general_exp_breakdown,
                'total': float(total_expenses),
            },
            'net_profit': float(net),
            'is_profitable': net >= 0,
            'daily_breakdown': daily,
            'cafe_units_breakdown': cafe_units_summary,
            'drill_down_paths': {
                'expense_register': f"/api/expenses/expenses/?month={month}&year={year}",
                'utility_readings': f"/api/operations/utility-readings/?month={month}&year={year}",
                'film_finance': f"/api/finance/distributor-shares/?month={month}&year={year}",
                'bookings_corrections': f"/api/bookings/bookings/?month={month}&year={year}",
                'cafe_wastage': f"/api/revenue/cafe-expenses/?month={month}&year={year}"
            }
        }

    @staticmethod
    def compare_periods(p1_date: date, p2_date: date, tenant=None) -> dict:
        """Compare daily performance between two dates and compute absolute and percentage variances."""
        rep1 = PLReportEngine.get_daily_report(p1_date, tenant=tenant)
        rep2 = PLReportEngine.get_daily_report(p2_date, tenant=tenant)

        comparisons = {}
        
        # income compare
        comparisons['ticket_revenue'] = PLReportEngine._diff(rep1['income']['ticket_revenue'], rep2['income']['ticket_revenue'])
        comparisons['canteen_revenue'] = PLReportEngine._diff(rep1['income']['canteen_revenue'], rep2['income']['canteen_revenue'])
        comparisons['ad_revenue'] = PLReportEngine._diff(rep1['income']['ad_revenue'], rep2['income']['ad_revenue'])
        comparisons['total_income'] = PLReportEngine._diff(rep1['income']['total'], rep2['income']['total'])

        # expenses compare
        comparisons['electricity'] = PLReportEngine._diff(rep1['expenses']['electricity'], rep2['expenses']['electricity'])
        comparisons['diesel'] = PLReportEngine._diff(rep1['expenses']['diesel'], rep2['expenses']['diesel'])
        comparisons['distributor_share'] = PLReportEngine._diff(rep1['expenses']['distributor_share'], rep2['expenses']['distributor_share'])
        comparisons['daily_payroll'] = PLReportEngine._diff(rep1['expenses']['daily_payroll'], rep2['expenses']['daily_payroll'])
        comparisons['cafe_expenses'] = PLReportEngine._diff(rep1['expenses']['cafe_expenses'], rep2['expenses']['cafe_expenses'])
        comparisons['general_expenses'] = PLReportEngine._diff(rep1['expenses']['general_expenses'], rep2['expenses']['general_expenses'])
        comparisons['total_expenses'] = PLReportEngine._diff(rep1['expenses']['total'], rep2['expenses']['total'])

        # profit compare
        comparisons['net_profit'] = PLReportEngine._diff(rep1['net_profit'], rep2['net_profit'])

        return {
            'period_1': str(p1_date),
            'period_2': str(p2_date),
            'comparisons': comparisons,
            'summary': {
                'revenue_drift': comparisons['total_income']['percent_change'],
                'expense_drift': comparisons['total_expenses']['percent_change'],
                'profitability_drift': comparisons['net_profit']['percent_change']
            }
        }

    @staticmethod
    def _diff(val1: float, val2: float) -> dict:
        diff_abs = val2 - val1
        if val1 == 0:
            diff_pct = 100.0 if diff_abs > 0 else (0.0 if diff_abs == 0 else -100.0)
        else:
            diff_pct = (diff_abs / val1) * 100.0
        return {
            'period_1_value': val1,
            'period_2_value': val2,
            'absolute_variance': diff_abs,
            'percent_change': round(diff_pct, 2)
        }

    @staticmethod
    def get_variance_drivers(target_date: date, tenant=None) -> dict:
        """Evaluates daily report against the running 30-day average baseline."""
        current = PLReportEngine.get_daily_report(target_date, tenant=tenant)
        
        # Calculate running 30-day baseline average
        start_date = target_date - timedelta(days=30)
        end_date = target_date - timedelta(days=1)
        
        from apps.bookings.models import Booking
        from apps.revenue.models import CanteenSale, AdvertisingSlot
        from apps.operations.models import UtilityReading, GeneratorLog
        from apps.expenses.models import Expense

        # Bookings 30-day
        booking_qs = Booking.objects.filter(show__show_date__range=[start_date, end_date], status__in=['CONFIRMED', 'CHECKED_IN'])
        if tenant: booking_qs = booking_qs.filter(tenant=tenant)
        booking_30 = (booking_qs.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')) / Decimal('30.0')

        # Canteen 30-day
        canteen_qs = CanteenSale.objects.filter(date__range=[start_date, end_date])
        if tenant: canteen_qs = canteen_qs.filter(tenant=tenant)
        canteen_30 = (canteen_qs.aggregate(total=Sum('total'))['total'] or Decimal('0')) / Decimal('30.0')

        # Electricity 30-day
        elec_qs = UtilityReading.objects.filter(reading_date__range=[start_date, end_date], meter__meter_type='ELECTRICITY')
        if tenant: elec_qs = elec_qs.filter(tenant=tenant)
        elec_30 = (elec_qs.aggregate(total=Sum('total_cost'))['total'] or Decimal('0')) / Decimal('30.0')

        # Diesel 30-day
        gen_qs = GeneratorLog.objects.filter(date__range=[start_date, end_date])
        if tenant: gen_qs = gen_qs.filter(tenant=tenant)
        diesel_30 = (gen_qs.aggregate(total=Sum('diesel_cost'))['total'] or Decimal('0')) / Decimal('30.0')

        # General expenses 30-day
        expense_qs = Expense.objects.filter(date__range=[start_date, end_date], approval_status='APPROVED')
        if tenant: expense_qs = expense_qs.filter(tenant=tenant)
        general_exp_30 = (expense_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')) / Decimal('30.0')

        drivers = []
        
        # Check income variances
        t_rev = Decimal(str(current['income']['ticket_revenue']))
        if booking_30 > 0:
            t_var = ((t_rev - booking_30) / booking_30) * Decimal('100.0')
            if abs(t_var) >= 15:
                drivers.append({
                    'metric': 'Ticket Revenue',
                    'current': float(t_rev),
                    'baseline': float(booking_30),
                    'variance_percent': float(round(t_var, 2)),
                    'impact': 'POSITIVE' if t_var > 0 else 'NEGATIVE',
                    'description': f"Ticket sales drift by {round(t_var, 2)}% vs 30-day baseline."
                })

        c_rev = Decimal(str(current['income']['canteen_revenue']))
        if canteen_30 > 0:
            c_var = ((c_rev - canteen_30) / canteen_30) * Decimal('100.0')
            if abs(c_var) >= 15:
                drivers.append({
                    'metric': 'Canteen Sales',
                    'current': float(c_rev),
                    'baseline': float(canteen_30),
                    'variance_percent': float(round(c_var, 2)),
                    'impact': 'POSITIVE' if c_var > 0 else 'NEGATIVE',
                    'description': f"Cafe purchases drift by {round(c_var, 2)}% vs 30-day baseline."
                })

        # Check expense spikes
        e_exp = Decimal(str(current['expenses']['electricity']))
        if elec_30 > 0:
            e_var = ((e_exp - elec_30) / elec_30) * Decimal('100.0')
            if e_var >= 20:
                drivers.append({
                    'metric': 'Electricity utility cost',
                    'current': float(e_exp),
                    'baseline': float(elec_30),
                    'variance_percent': float(round(e_var, 2)),
                    'impact': 'CRITICAL_SPIKE',
                    'description': f"Utility usage surged by {round(e_var, 2)}% above historical average! Review meter log anomalies."
                })

        d_exp = Decimal(str(current['expenses']['diesel']))
        if diesel_30 > 0:
            d_var = ((d_exp - diesel_30) / diesel_30) * Decimal('100.0')
            if d_var >= 25:
                drivers.append({
                    'metric': 'Generator Diesel cost',
                    'current': float(d_exp),
                    'baseline': float(diesel_30),
                    'variance_percent': float(round(d_var, 2)),
                    'impact': 'CRITICAL_SPIKE',
                    'description': f"Generator fuel usage surged by {round(d_var, 2)}% vs baseline average."
                })

        return {
            'target_date': str(target_date),
            'drivers_count': len(drivers),
            'variance_drivers': drivers,
            'variance_baseline': '30-Day Running Average Baseline'
        }

    @staticmethod
    def drill_down_source(period_start: date, period_end: date, source_module: str, category: str = None, tenant=None) -> list:
        """Fetch exact transaction items backing a specific P&L item for trace verification."""
        results = []

        if source_module == 'BOOKINGS':
            from apps.bookings.models import Booking
            qs = Booking.objects.filter(show__show_date__range=[period_start, period_end], status__in=['CONFIRMED', 'CHECKED_IN'])
            if tenant: qs = qs.filter(tenant=tenant)
            for item in qs.select_related('show__movie', 'customer')[:100]:
                results.append({
                    'source': 'Bookings',
                    'record_id': item.id,
                    'date': str(item.show.show_date),
                    'reference': item.booking_reference,
                    'details': f"Movie: {item.show.movie.title} | Customer: {item.customer.email if item.customer else 'Guest'}",
                    'amount': float(item.total_amount),
                    'status': item.status
                })

        elif source_module == 'UTILITY_READINGS':
            from apps.operations.models import UtilityReading
            qs = UtilityReading.objects.filter(reading_date__range=[period_start, period_end])
            if tenant: qs = qs.filter(tenant=tenant)
            for item in qs.select_related('meter')[:100]:
                results.append({
                    'source': 'Utility Readings',
                    'record_id': item.id,
                    'date': str(item.reading_date),
                    'reference': f"Meter: {item.meter.meter_number}",
                    'details': f"Type: {item.meter.meter_type} | Consumption: {item.consumption} units",
                    'amount': float(item.total_cost),
                    'status': item.posting_status
                })

        elif source_module == 'FILM_FINANCE':
            from apps.finance.models import DistributorShare
            qs = DistributorShare.objects.filter(show__show_date__range=[period_start, period_end])
            if tenant: qs = qs.filter(tenant=tenant)
            for item in qs.select_related('show__movie', 'distributor')[:100]:
                results.append({
                    'source': 'Distributor Finance',
                    'record_id': item.id,
                    'date': str(item.show.show_date),
                    'reference': item.distributor.name,
                    'details': f"Movie: {item.show.movie.title} | Net share split",
                    'amount': float(item.share_amount),
                    'status': 'POSTED'
                })

        elif source_module == 'EXPENSES':
            from apps.expenses.models import Expense
            qs = Expense.objects.filter(date__range=[period_start, period_end], approval_status='APPROVED')
            if tenant: qs = qs.filter(tenant=tenant)
            if category:
                qs = qs.filter(expense_type=category)
            for item in qs[:100]:
                results.append({
                    'source': 'Expense Register',
                    'record_id': item.id,
                    'date': str(item.date),
                    'reference': item.paid_to,
                    'details': f"Type: {item.get_expense_type_display()} | Notes: {item.notes}",
                    'amount': float(item.amount),
                    'status': item.get_approval_status_display()
                })

        elif source_module == 'CAFE_WASTAGE':
            from apps.revenue.models import CafeExpense
            qs = CafeExpense.objects.filter(date__range=[period_start, period_end])
            if tenant: qs = qs.filter(tenant=tenant)
            for item in qs.select_related('cafe_unit')[:100]:
                results.append({
                    'source': 'Cafe Wastage / Stock Expense',
                    'record_id': item.id,
                    'date': str(item.date),
                    'reference': item.cafe_unit.name if item.cafe_unit else 'Main Counter',
                    'details': f"Item: {item.notes}",
                    'amount': float(item.amount),
                    'status': 'APPROVED'
                })

        return results
