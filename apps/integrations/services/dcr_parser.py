import pdfplumber
import pandas as pd
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

class DistrictDCRParser:
    """Service to parse District DCR PDFs using pdfplumber and regex fallback."""
    
    VERSION = '1.0'

    @staticmethod
    def clean_decimal(val):
        """Helper to safely convert string to Decimal."""
        if not val:
            return Decimal('0')
        if isinstance(val, (int, float, Decimal)):
            return Decimal(str(val))
        clean_str = re.sub(r'[^\d.]', '', str(val))
        try:
            return Decimal(clean_str) if clean_str else Decimal('0')
        except InvalidOperation:
            return Decimal('0')

    @classmethod
    def parse_pdf(cls, file_path):
        """
        Parses the DCR PDF and extracts all relevant fields.
        Returns a dictionary with raw data and confidence score.
        """
        parsed_data = {
            'report_date': None,
            'movie_title': 'Unknown Movie',
            'screen_name': 'Unknown Screen',
            'show_time': None,
            'ticket_classes': [],
            'gross_revenue': Decimal('0'),
            'parsed_occupancy': Decimal('0'),
            'gst': Decimal('0'),
            'etax': Decimal('0'),
            'cess': Decimal('0'),
            'nett_revenue': Decimal('0'),
            'distributor_share': Decimal('0'),
            'exhibitor_share': Decimal('0'),
            'raw_text': '',
            'confidence_score': 1.0
        }

        try:
            with pdfplumber.open(file_path) as pdf:
                full_text = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text.append(text)
                    
                    # Optional: extract tables via pdfplumber
                    tables = page.extract_tables()
                    for table in tables:
                        # Attempt to interpret tables
                        df = pd.DataFrame(table[1:], columns=table[0]) if len(table) > 1 else pd.DataFrame()
                        # We could use pandas logic here if the structure is known
                        # For now, regex fallback on raw text is robust for unstructured DCRs

                raw_text = "\n".join(full_text)
                parsed_data['raw_text'] = raw_text

                # ── REGEX EXTRACTION FALLBACK ────────────────────────────────────
                
                # Date (e.g., Date: 2024-05-15 or 15/05/2024)
                date_match = re.search(r'(?i)Date[\s:]+([\d\-\/]+)', raw_text)
                if date_match:
                    try:
                        # Try parsing common formats
                        dt_str = date_match.group(1).strip()
                        if '/' in dt_str:
                            parsed_data['report_date'] = datetime.strptime(dt_str, '%d/%m/%Y').date()
                        else:
                            parsed_data['report_date'] = datetime.strptime(dt_str, '%Y-%m-%d').date()
                    except Exception:
                        pass
                
                if not parsed_data['report_date']:
                    parsed_data['report_date'] = datetime.now().date() # Fallback

                # Movie Title
                movie_match = re.search(r'(?i)Movie[\s:]+(.+)', raw_text)
                if movie_match:
                    parsed_data['movie_title'] = movie_match.group(1).strip()

                # Screen
                screen_match = re.search(r'(?i)Screen[\s:]+(.+)', raw_text)
                if screen_match:
                    parsed_data['screen_name'] = screen_match.group(1).strip()

                # Show Time
                time_match = re.search(r'(?i)Time[\s:]+([\d:]+\s*[AM|PM|am|pm]*)', raw_text)
                if time_match:
                    try:
                        parsed_data['show_time'] = datetime.strptime(time_match.group(1).strip(), '%I:%M %p').time()
                    except:
                        pass

                # Ticket Classes (Looking for lines like: Platinum 100 250.00 25000.00)
                # This is a generic heuristic.
                ticket_classes = ['Platinum', 'Gold', 'Silver', 'Balcony', 'First Class']
                for tclass in ticket_classes:
                    # Match class name, followed by count, rate, total
                    pattern = rf'(?i){tclass}\s+(\d+)\s+([\d\.]+)\s+([\d\.]+)'
                    match = re.search(pattern, raw_text)
                    if match:
                        count = int(match.group(1))
                        rate = cls.clean_decimal(match.group(2))
                        total = cls.clean_decimal(match.group(3))
                        parsed_data['ticket_classes'].append({
                            'ticket_class_name': tclass,
                            'ticket_count': count,
                            'ticket_rate': rate,
                            'parsed_total': total
                        })

                # Financials Extraction
                gross_match = re.search(r'(?i)Gross\s*(?:Revenue)?[\s:]+([\d\.]+)', raw_text)
                if gross_match: parsed_data['gross_revenue'] = cls.clean_decimal(gross_match.group(1))

                occ_match = re.search(r'(?i)Occupancy[\s:]+([\d\.]+)(?:\s*%)?', raw_text)
                if occ_match:
                    parsed_data['parsed_occupancy'] = cls.clean_decimal(occ_match.group(1))
                else:
                    # heuristic fallback: if we have ticket classes, compute average occupancy or default
                    parsed_data['parsed_occupancy'] = Decimal('45.00')

                gst_match = re.search(r'(?i)GST[\s:]+([\d\.]+)', raw_text)
                if gst_match: parsed_data['gst'] = cls.clean_decimal(gst_match.group(1))

                etax_match = re.search(r'(?i)Entertainment\s*Tax[\s:]+([\d\.]+)', raw_text)
                if etax_match: parsed_data['etax'] = cls.clean_decimal(etax_match.group(1))

                cess_match = re.search(r'(?i)Cess[\s:]+([\d\.]+)', raw_text)
                if cess_match: parsed_data['cess'] = cls.clean_decimal(cess_match.group(1))

                nett_match = re.search(r'(?i)Nett\s*(?:Revenue)?[\s:]+([\d\.]+)', raw_text)
                if nett_match: parsed_data['nett_revenue'] = cls.clean_decimal(nett_match.group(1))

                dist_match = re.search(r'(?i)Distributor\s*Share[\s:]+([\d\.]+)', raw_text)
                if dist_match: parsed_data['distributor_share'] = cls.clean_decimal(dist_match.group(1))

                exhib_match = re.search(r'(?i)Exhibitor\s*Share[\s:]+([\d\.]+)', raw_text)
                if exhib_match: parsed_data['exhibitor_share'] = cls.clean_decimal(exhib_match.group(1))

        except Exception as e:
            parsed_data['confidence_score'] = 0.0
            print(f"Error parsing PDF: {e}")

        return parsed_data
