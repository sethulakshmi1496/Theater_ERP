from celery import shared_task
from django.utils import timezone
import logging
from apps.tenants.models import Tenant
from apps.integrations.services.petpooja import PetpoojaService

logger = logging.getLogger(__name__)

@shared_task
def sync_petpooja_items_all_tenants():
    """Background job to sync items from Petpooja for all active integrations."""
    logger.info("Starting scheduled Petpooja ITEM sync for all tenants.")
    for tenant in Tenant.objects.filter(is_active=True):
        try:
            PetpoojaService.sync_items(tenant)
        except Exception as e:
            logger.error(f"Failed Petpooja item sync for tenant {tenant.name}: {str(e)}")

@shared_task
def sync_petpooja_sales_all_tenants():
    """Background job to sync bills from Petpooja for all active integrations."""
    logger.info("Starting scheduled Petpooja SALES sync for all tenants.")
    for tenant in Tenant.objects.filter(is_active=True):
        try:
            # Sync last 1 day by default
            PetpoojaService.sync_sales(tenant)
        except Exception as e:
            logger.error(f"Failed Petpooja sales sync for tenant {tenant.name}: {str(e)}")
