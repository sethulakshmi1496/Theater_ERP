from django.contrib import admin
from .models import Distributor, FilmContract, FilmAdvance, DistributorShare, Settlement, DistributorStatement

@admin.register(Distributor)
class DistributorAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'is_active', 'contact_person', 'phone')
    list_filter = ('tenant', 'is_active')

@admin.register(FilmContract)
class FilmContractAdmin(admin.ModelAdmin):
    list_display = ('movie', 'distributor', 'contract_type', 'status', 'start_date')
    list_filter = ('tenant', 'contract_type', 'status')

@admin.register(FilmAdvance)
class FilmAdvanceAdmin(admin.ModelAdmin):
    list_display = ('movie', 'contract', 'advance_amount', 'release_date', 'paid_date')
    list_filter = ('tenant',)

@admin.register(DistributorShare)
class DistributorShareAdmin(admin.ModelAdmin):
    list_display = ('show', 'contract', 'share_percentage', 'share_amount', 'is_settled')
    list_filter = ('tenant', 'is_settled', 'week_number')

@admin.register(Settlement)
class SettlementAdmin(admin.ModelAdmin):
    list_display = ('contract', 'start_date', 'end_date', 'net_payable', 'status')
    list_filter = ('tenant', 'status')

@admin.register(DistributorStatement)
class DistributorStatementAdmin(admin.ModelAdmin):
    list_display = ('distributor', 'period_start', 'period_end', 'generated_at')
    list_filter = ('tenant',)
