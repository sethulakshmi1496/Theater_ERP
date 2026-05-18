from decimal import Decimal
from apps.integrations.models import DistrictDCRReport, DCRDiscrepancy, DCRTicketClass


class DCRValidator:
    """Service to validate math on parsed DCR data."""

    TOLERANCE = Decimal('1.00')

    @classmethod
    def validate_and_save(cls, tenant, parsed_data, pdf_file=None, uploader=None, share_percentage=Decimal('50.0')):
        """
        Takes raw parsed data dict, computes expected values, creates DB models, 
        and flags discrepancies.
        """
        report = DistrictDCRReport.objects.create(
            tenant=tenant,
            report_date=parsed_data['report_date'],
            movie_title=parsed_data['movie_title'],
            screen_name=parsed_data['screen_name'],
            show_time=parsed_data['show_time'],
            raw_pdf=pdf_file,
            parser_version='1.0',
            confidence_score=parsed_data['confidence_score'],
            raw_text_dump=parsed_data['raw_text'],
            parsed_gross_revenue=parsed_data['gross_revenue'],
            parsed_occupancy=parsed_data.get('parsed_occupancy', Decimal('0')),
            parsed_gst=parsed_data['gst'],
            parsed_etax=parsed_data['etax'],
            parsed_cess=parsed_data['cess'],
            parsed_nett_revenue=parsed_data['nett_revenue'],
            parsed_distributor_share=parsed_data['distributor_share'],
            parsed_exhibitor_share=parsed_data['exhibitor_share'],
            distributor_share_percentage=share_percentage,
            uploaded_by=uploader,
            status=DistrictDCRReport.Status.PARSED
        )

        computed_gross = Decimal('0')
        for tc_data in parsed_data.get('ticket_classes', []):
            tc = DCRTicketClass.objects.create(
                report=report,
                ticket_class_name=tc_data['ticket_class_name'],
                ticket_count=tc_data['ticket_count'],
                ticket_rate=tc_data['ticket_rate'],
                parsed_total=tc_data['parsed_total']
            )
            # Math: expected gross = sum(ticket_count * rate)
            expected_row_total = Decimal(str(tc.ticket_count)) * tc.ticket_rate
            computed_gross += expected_row_total

            # Class-level check
            if abs(expected_row_total - tc.parsed_total) > cls.TOLERANCE:
                DCRDiscrepancy.objects.create(
                    report=report,
                    discrepancy_type=DCRDiscrepancy.Type.GROSS_MISMATCH,
                    description=f"{tc.ticket_class_name} row math mismatch: expected {expected_row_total}, got {tc.parsed_total}",
                    variance_amount=abs(expected_row_total - tc.parsed_total)
                )

        report.computed_gross_revenue = computed_gross

        # Overall Gross Match
        if abs(computed_gross - report.parsed_gross_revenue) > cls.TOLERANCE:
            DCRDiscrepancy.objects.create(
                report=report,
                discrepancy_type=DCRDiscrepancy.Type.GROSS_MISMATCH,
                description=f"Total gross mismatch: computed {computed_gross}, parsed {report.parsed_gross_revenue}",
                variance_amount=abs(computed_gross - report.parsed_gross_revenue)
            )
        
        # Nett Match
        computed_nett = report.parsed_gross_revenue - report.parsed_gst - report.parsed_etax - report.parsed_cess
        report.computed_nett_revenue = computed_nett

        if abs(computed_nett - report.parsed_nett_revenue) > cls.TOLERANCE:
            DCRDiscrepancy.objects.create(
                report=report,
                discrepancy_type=DCRDiscrepancy.Type.NETT_MISMATCH,
                description=f"Nett math mismatch: expected (Gross-Taxes) {computed_nett}, parsed {report.parsed_nett_revenue}",
                variance_amount=abs(computed_nett - report.parsed_nett_revenue)
            )

        # Split Match
        ratio = share_percentage / Decimal('100.0')
        computed_dist = report.parsed_nett_revenue * ratio
        computed_exhib = report.parsed_nett_revenue - computed_dist
        
        report.computed_distributor_share = computed_dist
        report.computed_exhibitor_share = computed_exhib

        if abs(computed_dist - report.parsed_distributor_share) > cls.TOLERANCE:
            DCRDiscrepancy.objects.create(
                report=report,
                discrepancy_type=DCRDiscrepancy.Type.SPLIT_MISMATCH,
                description=f"Distributor share mismatch based on {share_percentage}%: expected {computed_dist}, parsed {report.parsed_distributor_share}",
                variance_amount=abs(computed_dist - report.parsed_distributor_share)
            )
        
        if abs(computed_exhib - report.parsed_exhibitor_share) > cls.TOLERANCE:
            DCRDiscrepancy.objects.create(
                report=report,
                discrepancy_type=DCRDiscrepancy.Type.SPLIT_MISMATCH,
                description=f"Exhibitor share mismatch: expected {computed_exhib}, parsed {report.parsed_exhibitor_share}",
                variance_amount=abs(computed_exhib - report.parsed_exhibitor_share)
            )

        # Check missing fields
        missing = []
        if report.parsed_gross_revenue == 0 and not parsed_data.get('ticket_classes'):
            missing.append("No gross revenue or ticket counts parsed.")
        if not report.movie_title or report.movie_title == 'Unknown Movie':
            missing.append("Movie title missing.")
        
        if missing:
            DCRDiscrepancy.objects.create(
                report=report,
                discrepancy_type=DCRDiscrepancy.Type.MISSING_FIELDS,
                description="; ".join(missing),
                variance_amount=Decimal('0')
            )

        # Determine Final Status
        if report.discrepancies.exists():
            report.status = DistrictDCRReport.Status.VARIANCE_FOUND
            report.mismatch_flag = True
        else:
            report.status = DistrictDCRReport.Status.VALIDATED
            report.mismatch_flag = False

        if report.raw_pdf:
            report.raw_archive_link = report.raw_pdf.url

        report.save()
        return report
