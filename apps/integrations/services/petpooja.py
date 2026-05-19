import requests
import json
import logging
from datetime import datetime
from django.utils import timezone
from apps.integrations.models import IntegrationConnector, PetpoojaItemMap, PetpoojaSalesBill, PetpoojaSalesLineItem, PetpoojaSyncJob, PetpoojaFailedSync
from apps.revenue.models import CanteenSale, CanteenItem, CafeDailyConsumption
from apps.audit.models import ChangeLog

logger = logging.getLogger(__name__)

class PetpoojaService:
    @classmethod
    def get_credentials(cls, tenant):
        try:
            connector = IntegrationConnector.objects.get(
                tenant=tenant,
                connector_name=IntegrationConnector.ConnectorName.PETPOOJA,
                is_active=True
            )
            return connector.credentials_json
        except IntegrationConnector.DoesNotExist:
            return None

    @classmethod
    def sync_items(cls, tenant):
        creds = cls.get_credentials(tenant)
        if not creds:
            logger.error("Petpooja credentials missing or inactive.")
            return None
        
        job = PetpoojaSyncJob.objects.create(tenant=tenant, sync_type=PetpoojaSyncJob.SyncType.ITEM_SYNC)
        
        # Simulate Petpooja API call to get items
        # Usually: requests.get(f"{creds.get('base_url')}/items", headers={'Authorization': ...})
        mock_items = [
            {"itemid": "PP101", "itemname": "Butter Popcorn Tub", "itemcode": "P-01", "category": "POPCORN", "price": 240, "tax": "GST5"},
            {"itemid": "PP102", "itemname": "Pepsi Fountain", "itemcode": "B-01", "category": "BEVERAGE", "price": 180, "tax": "GST5"}
        ]
        
        processed = 0
        failed = 0
        
        for item in mock_items:
            try:
                # Update or create the item mapping
                petpooja_item, created = PetpoojaItemMap.objects.update_or_create(
                    tenant=tenant,
                    external_item_id=item['itemid'],
                    defaults={
                        'item_name': item['itemname'],
                        'sku': item['itemcode'],
                        'category': item.get('category', ''),
                        'selling_price': item.get('price', 0),
                        'tax_rule': item.get('tax', '')
                    }
                )
                
                # Auto-map if exact name match exists
                if not petpooja_item.is_mapped:
                    matched_aec_item = CanteenItem.objects.filter(tenant=tenant, name__iexact=item['itemname']).first()
                    if matched_aec_item:
                        petpooja_item.aec_item = matched_aec_item
                        petpooja_item.is_mapped = True
                        petpooja_item.save()
                        
                processed += 1
            except Exception as e:
                failed += 1
                PetpoojaFailedSync.objects.create(
                    tenant=tenant,
                    job=job,
                    external_id=item['itemid'],
                    record_type='ITEM',
                    payload=item,
                    error_reason=str(e)
                )

        job.records_processed = processed
        job.records_failed = failed
        job.status = PetpoojaSyncJob.Status.SUCCESS if failed == 0 else PetpoojaSyncJob.Status.PARTIAL
        job.completed_at = timezone.now()
        job.save()
        return job

    @classmethod
    def sync_sales(cls, tenant, from_date=None, to_date=None):
        creds = cls.get_credentials(tenant)
        if not creds:
            logger.error("Petpooja credentials missing or inactive.")
            return None
            
        job = PetpoojaSyncJob.objects.create(tenant=tenant, sync_type=PetpoojaSyncJob.SyncType.SALES_SYNC)
        
        # Simulate Petpooja API call to get bills
        mock_bills = [
            {
                "orderid": "ORD-5001",
                "billno": "B-201",
                "date": str(timezone.now().date()),
                "datetime": timezone.now().isoformat(),
                "gross": 420.00,
                "discount": 0.00,
                "tax": 21.00,
                "net": 441.00,
                "payment": "UPI",
                "items": [
                    {"itemid": "PP101", "name": "Butter Popcorn Tub", "qty": 1, "price": 240, "total": 240},
                    {"itemid": "PP102", "name": "Pepsi Fountain", "qty": 1, "price": 180, "total": 180}
                ]
            }
        ]
        
        processed = 0
        failed = 0
        
        for bill_data in mock_bills:
            try:
                # Idempotent bill creation
                bill, created = PetpoojaSalesBill.objects.get_or_create(
                    tenant=tenant,
                    external_order_id=bill_data['orderid'],
                    defaults={
                        'business_date': bill_data['date'],
                        'bill_datetime': bill_data['datetime'],
                        'bill_number': bill_data['billno'],
                        'gross_amount': bill_data['gross'],
                        'discount_amount': bill_data['discount'],
                        'tax_amount': bill_data['tax'],
                        'net_amount': bill_data['net'],
                        'payment_mode': bill_data.get('payment', '')
                    }
                )
                
                if created:
                    for l_item in bill_data.get('items', []):
                        PetpoojaSalesLineItem.objects.create(
                            bill=bill,
                            external_item_id=l_item['itemid'],
                            item_name=l_item['name'],
                            quantity=l_item['qty'],
                            unit_price=l_item['price'],
                            net_amount=l_item['total']
                        )
                        
                        # Find mapping to deduct inventory
                        mapping = PetpoojaItemMap.objects.filter(tenant=tenant, external_item_id=l_item['itemid']).first()
                        if mapping and mapping.is_mapped and mapping.aec_item:
                            aec_item = mapping.aec_item
                            
                            # Create CanteenSale to populate reports automatically
                            CanteenSale.objects.create(
                                tenant=tenant,
                                date=bill.business_date,
                                item=aec_item,
                                item_name=aec_item.name,
                                quantity=l_item['qty'],
                                unit_price=l_item['price'],
                                notes=f"Petpooja Sync: {bill.bill_number}"
                            )
                            
                            # Deduct from actual stock logic
                            if aec_item.is_track_stock:
                                aec_item.current_stock -= l_item['qty']
                                aec_item.save()
                                
                    bill.is_imported_to_aec = True
                    bill.save()
                    
                processed += 1
            except Exception as e:
                failed += 1
                PetpoojaFailedSync.objects.create(
                    tenant=tenant,
                    job=job,
                    external_id=bill_data['orderid'],
                    record_type='BILL',
                    payload=bill_data,
                    error_reason=str(e)
                )

        job.records_processed = processed
        job.records_failed = failed
        job.status = PetpoojaSyncJob.Status.SUCCESS if failed == 0 else PetpoojaSyncJob.Status.PARTIAL
        job.completed_at = timezone.now()
        job.save()
        return job
