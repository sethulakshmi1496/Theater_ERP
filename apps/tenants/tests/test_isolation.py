"""
AEC Cinemas Platform – Tenant Isolation Tests
=============================================
Module 2: Verifies that:
  1. Tenant A users cannot list Tenant B records
  2. Tenant A users get 404 on Tenant B detail/update/delete
  3. Create always stamps the correct tenant from request context
  4. All key endpoints are tenant-scoped

Run:  python manage.py test apps.tenants.tests.test_isolation -v 2
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.tenants.models import Tenant, TenantModule
from apps.accounts.models import User
from apps.screens.models import Screen, Movie
from apps.revenue.models import CanteenSale
from apps.operations.models import ElectricityReading, GeneratorLog
from apps.finance.models import FilmAdvance


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def create_tenant(name, slug, plan='pro'):
    t = Tenant.objects.create(name=name, slug=slug, plan=plan, is_active=True)
    for module in ['OPERATIONS', 'CAFE', 'FINANCE', 'SCREEN_BUILDER']:
        TenantModule.objects.create(tenant=t, module_key=module, is_enabled=True)
    return t


def create_user(email, tenant, role=User.Role.ADMIN):
    u = User.objects.create_user(
        email=email,
        password='testpass123!',
        full_name='Test User',
        role=role,
    )
    u.tenant = tenant
    u.save()
    return u


def get_ids_from_response(response_data):
    """Extract IDs from either paginated {results: [...]} or flat [...] response."""
    if isinstance(response_data, dict):
        items = response_data.get('results', [])
    else:
        items = response_data
    return [item['id'] for item in items]


def auth_client(user) -> APIClient:
    client = APIClient()
    response = client.post('/api/auth/login/', {
        'email': user.email,
        'password': 'testpass123!',
    }, format='json')
    token = response.data.get('access')
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    return client


# ─── Base Test Case ───────────────────────────────────────────────────────────

class TenantIsolationTestCase(TestCase):
    """
    Base class: creates two isolated tenants (Alpha and Beta) with one
    user per tenant. Subclasses test specific endpoint isolation.
    """

    @classmethod
    def setUpTestData(cls):
        cls.tenant_a = create_tenant('Alpha Cinema', 'alpha-cinema')
        cls.tenant_b = create_tenant('Beta Cinema', 'beta-cinema')

        cls.user_a = create_user('admin@alpha.com', cls.tenant_a, role=User.Role.MD)
        cls.user_b = create_user('admin@beta.com', cls.tenant_b, role=User.Role.MD)

    def setUp(self):
        self.client_a = auth_client(self.user_a)
        self.client_b = auth_client(self.user_b)


# ─── Screen Isolation Tests ────────────────────────────────────────────────────

class ScreenTenantIsolationTest(TenantIsolationTestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.screen_a = Screen.objects.create(
            tenant=cls.tenant_a, name='Alpha Screen 1', total_seats=200
        )
        cls.screen_b = Screen.objects.create(
            tenant=cls.tenant_b, name='Beta Screen 1', total_seats=150
        )

    def test_list_returns_only_own_tenant_screens(self):
        """Tenant A user sees only Tenant A screens."""
        r = self.client_a.get('/api/screens/screens/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        ids = get_ids_from_response(r.data)
        self.assertIn(self.screen_a.id, ids)
        self.assertNotIn(self.screen_b.id, ids)

    def test_list_tenant_b_sees_only_own_screens(self):
        """Tenant B user sees only Tenant B screens."""
        r = self.client_b.get('/api/screens/screens/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        ids = get_ids_from_response(r.data)
        self.assertIn(self.screen_b.id, ids)
        self.assertNotIn(self.screen_a.id, ids)

    def test_detail_cross_tenant_returns_404(self):
        """Tenant A user gets 404 when accessing Tenant B's screen."""
        r = self.client_a.get(f'/api/screens/screens/{self.screen_b.id}/')
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_cross_tenant_returns_404(self):
        """Tenant A user cannot update Tenant B's screen."""
        r = self.client_a.patch(
            f'/api/screens/screens/{self.screen_b.id}/',
            {'name': 'Hacked Screen'},
            format='json'
        )
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)
        # Verify the name was NOT changed
        self.screen_b.refresh_from_db()
        self.assertEqual(self.screen_b.name, 'Beta Screen 1')

    def test_create_stamps_correct_tenant(self):
        """Creating a screen via API stamps Tenant A's tenant, not whatever is in the body."""
        r = self.client_a.post('/api/screens/screens/', {
            'name': 'Alpha Screen 2',
            'total_seats': 100,
            'tenant': self.tenant_b.id,   # Attempt to forge tenant
        }, format='json')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        new_screen = Screen.objects.get(id=r.data['id'])
        # Must be stamped with tenant_a, not tenant_b
        self.assertEqual(new_screen.tenant_id, self.tenant_a.id)


# ─── Canteen Sale Isolation Tests ─────────────────────────────────────────────

class CanteenSaleTenantIsolationTest(TenantIsolationTestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        from datetime import date
        cls.sale_a = CanteenSale.objects.create(
            tenant=cls.tenant_a,
            date=date.today(),
            item_name='Popcorn',
            quantity=5,
            unit_price=100,
            total=500,
        )
        cls.sale_b = CanteenSale.objects.create(
            tenant=cls.tenant_b,
            date=date.today(),
            item_name='Cold Drink',
            quantity=3,
            unit_price=80,
            total=240,
        )

    def test_list_returns_only_own_sales(self):
        r = self.client_a.get('/api/revenue/canteen/sales/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        ids = get_ids_from_response(r.data)
        self.assertIn(self.sale_a.id, ids)
        self.assertNotIn(self.sale_b.id, ids)

    def test_cross_tenant_detail_404(self):
        r = self.client_a.get(f'/api/revenue/canteen/sales/{self.sale_b.id}/')
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_stamps_tenant(self):
        from datetime import date
        r = self.client_a.post('/api/revenue/canteen/sales/', {
            'date': str(date.today()),
            'item_name': 'Nachos',
            'quantity': 2,
            'unit_price': 150,
            'total': 300,
        }, format='json')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        new_sale = CanteenSale.objects.get(id=r.data['id'])
        self.assertEqual(new_sale.tenant_id, self.tenant_a.id)


# ─── Utility Reading Isolation Tests ───────────────────────────────────────────

class UtilityReadingIsolationTest(TenantIsolationTestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        from datetime import date, timedelta
        from apps.operations.models import UtilityMeter, UtilityReading

        # Create meters
        cls.meter_a = UtilityMeter.objects.create(
            tenant=cls.tenant_a, name='Main Meter Alpha', meter_type='ELECTRICITY'
        )
        cls.meter_b = UtilityMeter.objects.create(
            tenant=cls.tenant_b, name='Main Meter Beta', meter_type='ELECTRICITY'
        )

        cls.reading_a = UtilityReading.objects.create(
            meter=cls.meter_a,
            reading_date=date.today() - timedelta(days=2),
            initial_reading=1000,
            final_reading=1050,
        )
        cls.reading_b = UtilityReading.objects.create(
            meter=cls.meter_b,
            reading_date=date.today() - timedelta(days=3),
            initial_reading=2000,
            final_reading=2060,
        )

    def test_list_isolation(self):
        r = self.client_a.get('/api/operations/utility-readings/')
        ids = get_ids_from_response(r.data)
        self.assertIn(self.reading_a.id, ids)
        self.assertNotIn(self.reading_b.id, ids)

    def test_cross_tenant_detail_404(self):
        r = self.client_a.get(f'/api/operations/utility-readings/{self.reading_b.id}/')
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)


# ─── User Context Tests ────────────────────────────────────────────────────────

class MeEndpointTenantTest(TenantIsolationTestCase):

    def test_me_returns_tenant_for_user_a(self):
        r = self.client_a.get('/api/accounts/me/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn('tenant', r.data)
        self.assertEqual(r.data['tenant']['slug'], 'alpha-cinema')

    def test_me_returns_tenant_for_user_b(self):
        r = self.client_b.get('/api/accounts/me/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['tenant']['slug'], 'beta-cinema')

    def test_me_returns_active_modules(self):
        """active_modules reflects the modules enabled for the user's tenant."""
        r = self.client_a.get('/api/accounts/me/')
        self.assertIn('active_modules', r.data)
        self.assertIsInstance(r.data['active_modules'], list)
        # 'CAFE' was explicitly seeded in create_tenant() fixture
        self.assertIn('CAFE', r.data['active_modules'])


# ─── Tenant Boundary — No Orphan Access ──────────────────────────────────────

class NoOrphanTenantTest(TestCase):
    """
    A user with no tenant assigned should get a clear error.
    """

    def setUp(self):
        self.orphan = User.objects.create_user(
            email='orphan@test.com',
            password='testpass123!',
            full_name='Orphan User',
            role=User.Role.ADMIN,
            # No tenant assigned
        )
        self.client = APIClient()
        r = self.client.post('/api/auth/login/', {
            'email': 'orphan@test.com',
            'password': 'testpass123!',
        }, format='json')
        token = r.data.get('access', '')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_orphan_user_gets_empty_list_not_all_data(self):
        """
        An orphaned user (no tenant) should get an empty list from tenant-scoped
        endpoints, never all-tenants data.
        """
        r = self.client.get('/api/screens/screens/')
        if r.status_code == status.HTTP_200_OK:
            results = get_ids_from_response(r.data)
            self.assertEqual(len(results), 0, 'Orphan user must never see any tenant data')
        else:
            self.assertIn(r.status_code, [
                status.HTTP_403_FORBIDDEN,
                status.HTTP_401_UNAUTHORIZED,
            ])


# ─── TenantAsset Isolation Tests ──────────────────────────────────────────────

class TenantAssetIsolationTest(TenantIsolationTestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        from apps.operations.models import AssetCategory, AssetTemplate, TenantAsset

        cls.cat = AssetCategory.objects.create(
            key='LAMP_TEST', label='Test Lamp', tracks_hours=True
        )
        cls.template = AssetTemplate.objects.create(
            category=cls.cat,
            manufacturer='Christie',
            model_number='X-Test-3000',
            rated_life_hours=3000,
        )
        cls.asset_a = TenantAsset.objects.create(
            tenant=cls.tenant_a,
            template=cls.template,
            serial_number='SN-ALPHA-001',
            current_hours=100,
            alert_threshold_hours=200,
            is_active=True,
        )
        cls.asset_b = TenantAsset.objects.create(
            tenant=cls.tenant_b,
            template=cls.template,
            serial_number='SN-BETA-001',
            current_hours=50,
            alert_threshold_hours=200,
            is_active=True,
        )

    def test_list_returns_only_own_tenant_assets(self):
        """Tenant A only sees their own assets."""
        r = self.client_a.get('/api/operations/tenant-assets/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        ids = get_ids_from_response(r.data)
        self.assertIn(self.asset_a.id, ids)
        self.assertNotIn(self.asset_b.id, ids)

    def test_cross_tenant_asset_detail_returns_404(self):
        """Tenant A cannot access Tenant B's asset detail."""
        r = self.client_a.get(f'/api/operations/tenant-assets/{self.asset_b.id}/')
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_alerts_endpoint_scoped_to_tenant(self):
        """Alerts endpoint only returns assets from the requesting tenant."""
        r = self.client_a.get('/api/operations/tenant-assets/alerts/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        ids = [a['id'] for a in r.data.get('results', [])]
        for aid in ids:
            self.assertNotEqual(aid, self.asset_b.id)

    def test_create_asset_stamps_correct_tenant(self):
        """Creating an asset via API stamps Tenant A's tenant."""
        r = self.client_a.post('/api/operations/tenant-assets/', {
            'template': self.template.id,
            'serial_number': 'SN-NEW-999',
            'is_active': True,
        }, format='json')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        from apps.operations.models import TenantAsset
        new = TenantAsset.objects.get(id=r.data['id'])
        self.assertEqual(new.tenant_id, self.tenant_a.id)
