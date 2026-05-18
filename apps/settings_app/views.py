"""AEC Cinemas – Tenant Settings Views"""

from rest_framework import serializers, viewsets, status, mixins
from rest_framework.response import Response
from rest_framework.decorators import action
from apps.settings_app.models import TenantSetting
from apps.tenants.models import Tenant, TenantModule
from apps.accounts.permissions import IsMDOrAdmin, IsMD
from apps.tenants.middleware import TenantQuerysetMixin
from apps.audit.models import ChangeLog


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ['id', 'name', 'slug', 'timezone', 'currency', 'working_days_per_month', 'plan']
        read_only_fields = ['id', 'slug', 'plan']


class TenantModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantModule
        fields = ['id', 'module_key', 'is_enabled', 'config_json']
        read_only_fields = ['id', 'module_key']


class TenantSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantSetting
        fields = '__all__'
        read_only_fields = ['updated_at', 'tenant']


class TenantProfileViewSet(mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """Allows MD to update their own tenant's profile (name, currency, timezone, etc)."""
    serializer_class = TenantSerializer
    permission_classes = [IsMD]

    def get_object(self):
        return self.request.user.tenant

    def perform_update(self, serializer):
        obj = self.get_object()
        old_data = {'name': obj.name, 'timezone': obj.timezone, 'currency': obj.currency}
        updated_obj = serializer.save()
        ChangeLog.objects.create(
            table_name='Tenant',
            record_id=updated_obj.id,
            action=ChangeLog.ACTION_UPDATE,
            changed_by=self.request.user,
            changes={'old': old_data, 'new': {'name': updated_obj.name, 'timezone': updated_obj.timezone, 'currency': updated_obj.currency}}
        )


class TenantModuleViewSet(TenantQuerysetMixin, viewsets.ModelViewSet):
    """Allows MD to toggle features."""
    queryset = TenantModule.objects.all().order_by('module_key')
    serializer_class = TenantModuleSerializer
    permission_classes = [IsMD]

    def perform_update(self, serializer):
        obj = self.get_object()
        old_val = obj.is_enabled
        updated_obj = serializer.save()
        ChangeLog.objects.create(
            table_name='TenantModule',
            record_id=updated_obj.id,
            action=ChangeLog.ACTION_UPDATE,
            changed_by=self.request.user,
            changes={'module_key': updated_obj.module_key, 'old_enabled': old_val, 'new_enabled': updated_obj.is_enabled}
        )


class TenantSettingViewSet(TenantQuerysetMixin, viewsets.ModelViewSet):
    queryset = TenantSetting.objects.all().order_by('key')
    serializer_class = TenantSettingSerializer
    permission_classes = [IsMDOrAdmin]

    def perform_create(self, serializer):
        obj = serializer.save(tenant=self.request.user.tenant)
        ChangeLog.objects.create(
            table_name='TenantSetting',
            record_id=obj.id,
            action=ChangeLog.ACTION_CREATE,
            changed_by=self.request.user,
            changes={'key': obj.key, 'value': obj.value}
        )

    def perform_update(self, serializer):
        obj = self.get_object()
        old_val = obj.value
        updated_obj = serializer.save()
        ChangeLog.objects.create(
            table_name='TenantSetting',
            record_id=updated_obj.id,
            action=ChangeLog.ACTION_UPDATE,
            changed_by=self.request.user,
            changes={'key': updated_obj.key, 'old_value': old_val, 'new_value': updated_obj.value}
        )


# ─── VENDOR MASTER ────────────────────────────────────────────────────────────

from apps.settings_app.models import Vendor
from apps.accounts.permissions import IsStaffOrAbove

class VendorSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Vendor
        fields = '__all__'
        read_only_fields = ['tenant', 'created_at', 'updated_at']


class VendorViewSet(TenantQuerysetMixin, viewsets.ModelViewSet):
    queryset = Vendor.objects.all().order_by('name')
    serializer_class = VendorSerializer
    filterset_fields = ['category', 'is_active']
    search_fields = ['name', 'contact_person', 'phone', 'email']
    permission_classes = [IsStaffOrAbove]

    def perform_create(self, serializer):
        obj = serializer.save(tenant=self.request.user.tenant)
        ChangeLog.objects.create(
            tenant=self.request.user.tenant,
            table_name='Vendor',
            record_id=obj.id,
            action=ChangeLog.ACTION_CREATE,
            changed_by=self.request.user,
            changes={'name': obj.name, 'category': obj.category}
        )

    def perform_update(self, serializer):
        obj = self.get_object()
        old_name = obj.name
        updated_obj = serializer.save()
        ChangeLog.objects.create(
            tenant=self.request.user.tenant,
            table_name='Vendor',
            record_id=updated_obj.id,
            action=ChangeLog.ACTION_UPDATE,
            changed_by=self.request.user,
            changes={'name': updated_obj.name, 'old_name': old_name}
        )

    @action(detail=True, methods=['post'], url_path='deactivate')
    def deactivate(self, request, pk=None):
        vendor = self.get_object()
        vendor.is_active = False
        vendor.save(update_fields=['is_active', 'updated_at'])
        ChangeLog.objects.create(
            tenant=self.request.user.tenant,
            table_name='Vendor',
            record_id=vendor.id,
            action=ChangeLog.ACTION_UPDATE,
            changed_by=request.user,
            changes={'is_active': False, 'name': vendor.name}
        )
        return Response({'status': 'Vendor deactivated', 'name': vendor.name})

    @action(detail=False, methods=['get'], url_path='export')
    def export(self, request):
        import csv
        from django.http import HttpResponse
        qs = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="vendor_list.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'Vendor Name', 'Category', 'Contact Person', 'Phone', 'Email',
            'GST Number', 'Address', 'Default Payment Terms', 'Bank Details Reference', 'Status'
        ])
        for v in qs:
            writer.writerow([
                v.name, v.get_category_display(), v.contact_person, v.phone, v.email,
                v.gst_number, v.address, v.default_payment_terms, v.bank_details_ref,
                'Active' if v.is_active else 'Inactive'
            ])
        return response


# ─── ALERT RULES & SYSTEM GOVERNANCE ──────────────────────────────────────────

from apps.settings_app.models import AlertRule

class AlertRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertRule
        fields = '__all__'
        read_only_fields = ['tenant', 'created_at']


class AlertRuleViewSet(TenantQuerysetMixin, viewsets.ModelViewSet):
    queryset = AlertRule.objects.all().order_by('module', 'rule_name')
    serializer_class = AlertRuleSerializer
    permission_classes = [IsMDOrAdmin]
    filterset_fields = ['module', 'is_enabled']

    def perform_create(self, serializer):
        rule = serializer.save(tenant=self.request.user.tenant)
        ChangeLog.objects.create(
            tenant=self.request.user.tenant,
            table_name='AlertRule',
            record_id=rule.id,
            action=ChangeLog.ACTION_CREATE,
            changed_by=self.request.user,
            changes={'rule_name': rule.rule_name, 'threshold': float(rule.threshold_value)}
        )

    def perform_update(self, serializer):
        rule = self.get_object()
        old_val = rule.threshold_value
        updated_rule = serializer.save()
        ChangeLog.objects.create(
            tenant=self.request.user.tenant,
            table_name='AlertRule',
            record_id=updated_rule.id,
            action=ChangeLog.ACTION_UPDATE,
            changed_by=self.request.user,
            changes={'rule_name': updated_rule.rule_name, 'old_threshold': float(old_val), 'new_threshold': float(updated_rule.threshold_value)}
        )


class SystemGovernanceViewSet(viewsets.ViewSet):
    """
    Acts as the governance and master-data control layer for the entire AEC app.
    Consolidates subcategories, rules, role-level permissions, and module visibility.
    """
    permission_classes = [IsMDOrAdmin]

    # ── Action: Open Child Setup Pages ────────────────────────────────────────
    @action(detail=False, methods=['get'], url_path='setup-pages')
    def open_child_setup_pages(self, request):
        tenant = getattr(request.user, 'tenant', None)
        tenant_id = tenant.id if tenant else None
        
        return Response({
            'tenant_name': tenant.name if tenant else 'AEC Cinemas',
            'governance_child_areas': {
                'tenant_profile': {
                    'name': 'Tenant Profile',
                    'path': f"/api/settings/tenant-profile/",
                    'description': 'Configure tenant details, working days, plan, timezone and currency.'
                },
                'modules_features': {
                    'name': 'Modules & Features',
                    'path': "/api/settings/modules/",
                    'description': 'Toggle active operational features across theater operations.'
                },
                'utility_meters_alerts': {
                    'name': 'Utility Meters & Alerts',
                    'path': "/api/operations/meters/",
                    'description': 'Manage electricity and water baseline readings and warnings.'
                },
                'users_roles': {
                    'name': 'Users & Roles',
                    'path': "/api/accounts/users/",
                    'description': 'Administer team accounts, roles, access levels, and logs.'
                },
                'configuration_links': {
                    'name': 'Configuration Links',
                    'path': "/api/settings/tenant-settings/",
                    'description': 'Quick links to override base operational configuration values.'
                },
                'change_history': {
                    'name': 'Change History',
                    'path': "/api/audit/shield-logs/",
                    'description': 'Full compliance records and timeline trace of all system changes.'
                },
                'vendor_master': {
                    'name': 'Vendor Master',
                    'path': "/api/settings/vendors/",
                    'description': 'Manage supplier contacts, categories, and payment terms.'
                },
                'integration_hub': {
                    'name': 'Integration Hub',
                    'path': "/api/integrations/connectors/",
                    'description': 'Central registry connecting District, Petpooja, BMS, and Perplexity.'
                },
                'alert_rules': {
                    'name': 'Alert Rules',
                    'path': "/api/settings/alert-rules/",
                    'description': 'Define warning and error threshold triggers for automated alerts.'
                },
                'expense_masters': {
                    'name': 'Expense Masters',
                    'path': "/api/expenses/subcategories/",
                    'description': 'Configure budget limits and expense category sub-accounts.'
                },
                'parking_configuration': {
                    'name': 'Parking Configuration',
                    'path': "/api/parking/zones/",
                    'description': 'Setup vehicle parking capacity and tier rate cards.'
                }
            }
        })

    # ── Action: Manage Role Permissions ───────────────────────────────────────
    @action(detail=False, methods=['get'], url_path='role-permissions')
    def manage_role_permissions(self, request):
        # Returns roles and their mapped authorization scopes
        return Response({
            'roles': ['MD', 'ADMIN', 'STAFF', 'MANAGER'],
            'permissions_matrix': {
                'MD': {
                    'scope': 'ALL',
                    'unconditional_delete': True,
                    'approval_authority': True,
                    'p_and_l_view': True
                },
                'ADMIN': {
                    'scope': 'GLOBAL_TENANT',
                    'unconditional_delete': False,
                    'admin_2fa_delete': True,
                    'approval_authority': True
                },
                'STAFF': {
                    'scope': 'OPERATIONAL_ENTRY',
                    'unconditional_delete': False,
                    'view_directories': True
                }
            }
        })

    # ── Action: Configure Module Visibility ───────────────────────────────────
    @action(detail=False, methods=['post'], url_path='configure-visibility')
    def configure_module_visibility(self, request):
        tenant = getattr(request.user, 'tenant', None)
        module_key = request.data.get('module_key')
        is_enabled = request.data.get('is_enabled', True)

        if not module_key:
            return Response({'error': 'module_key parameter is required.'}, status=400)

        from apps.tenants.models import TenantModule
        module_obj, created = TenantModule.objects.update_or_create(
            tenant=tenant,
            module_key=module_key,
            defaults={'is_enabled': is_enabled}
        )

        ChangeLog.objects.create(
            tenant=tenant,
            table_name='TenantModule',
            record_id=module_obj.id,
            action=ChangeLog.ACTION_UPDATE,
            changed_by=request.user,
            changes={'module_key': module_key, 'is_enabled': is_enabled}
        )

        return Response({
            'module_key': module_key,
            'is_enabled': module_obj.is_enabled,
            'status': 'Module visibility updated successfully.'
        })

    # ── Action: Update Masters ────────────────────────────────────────────────
    @action(detail=False, methods=['post'], url_path='update-masters')
    def update_masters(self, request):
        tenant = getattr(request.user, 'tenant', None)
        configs = request.data.get('configurations', {})

        updated = []
        for key, val in configs.items():
            setting, created = TenantSetting.objects.update_or_create(
                tenant=tenant,
                key=key,
                defaults={'value': str(val)}
            )
            updated.append(key)
            ChangeLog.objects.create(
                tenant=tenant,
                table_name='TenantSetting',
                record_id=setting.id,
                action=ChangeLog.ACTION_UPDATE,
                changed_by=request.user,
                changes={'key': key, 'value': str(val)}
            )

        return Response({
            'status': 'Global configurations updated successfully.',
            'updated_keys': updated
        })



