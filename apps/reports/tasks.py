from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging
from apps.tenants.models import Tenant
from apps.reports.models import AIInsightReport
from apps.integrations.services.perplexity import PerplexityService

logger = logging.getLogger(__name__)

@shared_task
def generate_daily_reports():
    yesterday = timezone.now().date() - timedelta(days=1)
    for tenant in Tenant.objects.all():
        logger.info(f"Generating daily reports for tenant: {tenant.name}")
        context_data = {
            "date": str(yesterday),
            "notes": "Daily aggregated metrics"
        }
        PerplexityService.generate_report(
            tenant=tenant,
            report_type="Executive Daily Brief",
            period_type="DAILY",
            module="EXECUTIVE",
            start_date=yesterday,
            end_date=yesterday,
            context_data=context_data,
            prompt_template="Analyze yesterday's business performance, occupancy, anomalies, and suggest immediate improvements. Compare with relevant real-world context."
        )

        modules_to_report = [
            ("MOVIES", "Movies Daily Summary", "Analyze movie performance and occupancy alerts."),
            ("BOOKINGS", "Bookings Daily Summary", "Analyze booking trends, refund spikes, and ticketing exceptions."),
            ("CAFE", "Cafe Sales Daily Summary", "Analyze cafe sales, inventory alerts, and fast-moving items."),
            ("UTILITY", "Utility Daily Summary", "Analyze utility consumption, power tariffs, and generator usage."),
            ("MAINTENANCE", "Maintenance Daily Alert", "Analyze critical maintenance items and asset health."),
            ("FINANCE", "Distributor Finance Daily Risk Summary", "Provide daily mismatch or settlement risk notes."),
            ("EXPENSE", "Expense Daily Alert Summary", "Provide daily overspend alerts.")
        ]
        
        for mod_code, rep_type, prompt in modules_to_report:
            PerplexityService.generate_report(
                tenant=tenant,
                report_type=rep_type,
                period_type="DAILY",
                module=mod_code,
                start_date=yesterday,
                end_date=yesterday,
                context_data=context_data,
                prompt_template=prompt
            )

@shared_task
def generate_monthly_reports():
    today = timezone.now().date()
    last_day_of_prev_month = today.replace(day=1) - timedelta(days=1)
    first_day_of_prev_month = last_day_of_prev_month.replace(day=1)
    
    for tenant in Tenant.objects.all():
        logger.info(f"Generating monthly reports for tenant: {tenant.name}")
        context_data = {
            "month": first_day_of_prev_month.strftime("%Y-%m"),
            "notes": "Monthly aggregated metrics"
        }
        PerplexityService.generate_report(
            tenant=tenant,
            report_type="Executive Monthly Review",
            period_type="MONTHLY",
            module="EXECUTIVE",
            start_date=first_day_of_prev_month,
            end_date=last_day_of_prev_month,
            context_data=context_data,
            prompt_template="Analyze last month's overall business performance, margin analysis, and utilization patterns. Compare with previous month if applicable."
        )
        
        modules_to_report = [
            ("FINANCE", "Distributor Finance Monthly Settlement Review", "Analyze settlement health, distributor shares, and mismatches."),
            ("EXPENSE", "Expense Monthly Variance Review", "Analyze cost control, overspends, and vendor payments."),
            ("STAFF", "Staff Monthly Review", "Analyze attendance patterns, staffing efficiency, and HR logs."),
            ("UTILITY", "Utility Monthly Cost Review", "Analyze monthly cost and consumption pattern analysis."),
            ("BOOKINGS", "Booking Monthly Review", "Analyze monthly schedule-performance commentary.")
        ]
        
        for mod_code, rep_type, prompt in modules_to_report:
            PerplexityService.generate_report(
                tenant=tenant,
                report_type=rep_type,
                period_type="MONTHLY",
                module=mod_code,
                start_date=first_day_of_prev_month,
                end_date=last_day_of_prev_month,
                context_data=context_data,
                prompt_template=prompt
            )

@shared_task
def generate_yearly_reports():
    today = timezone.now().date()
    last_year = today.year - 1
    start_date = today.replace(year=last_year, month=1, day=1)
    end_date = today.replace(year=last_year, month=12, day=31)
    
    for tenant in Tenant.objects.all():
        logger.info(f"Generating yearly reports for tenant: {tenant.name}")
        context_data = {
            "year": str(last_year),
            "notes": "Yearly aggregated metrics"
        }
        PerplexityService.generate_report(
            tenant=tenant,
            report_type="Executive Yearly Business Review",
            period_type="YEARLY",
            module="EXECUTIVE",
            start_date=start_date,
            end_date=end_date,
            context_data=context_data,
            prompt_template="Provide a strategic review of the past year's business patterns, growth opportunities, and capex planning."
        )
        
        modules_to_report = [
            ("FINANCE", "Distributor Finance Yearly Distributor Review", "Provide yearly distributor and contract performance analysis."),
            ("EXPENSE", "Expense Yearly Cost-Discipline Review", "Provide yearly profitability, variance, and efficiency commentary."),
            ("UTILITY", "Utility Yearly Efficiency Review", "Provide yearly efficiency and savings recommendations."),
            ("BOOKINGS", "Booking Yearly Trend Review", "Provide yearly movie/release pattern analysis with improvement suggestions.")
        ]
        
        for mod_code, rep_type, prompt in modules_to_report:
            PerplexityService.generate_report(
                tenant=tenant,
                report_type=rep_type,
                period_type="YEARLY",
                module=mod_code,
                start_date=start_date,
                end_date=end_date,
                context_data=context_data,
                prompt_template=prompt
            )
