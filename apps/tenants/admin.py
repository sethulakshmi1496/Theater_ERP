from django.contrib import admin
from .models import Tenant, TenantModule


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'plan', 'is_active', 'created_at']
    list_filter = ['plan', 'is_active']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'slug']


@admin.register(TenantModule)
class TenantModuleAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'module_key', 'is_enabled']
    list_filter = ['is_enabled', 'module_key']
    list_editable = ['is_enabled']
