from django.contrib import admin
from .models import Expense, ExpenseSubcategory

@admin.register(ExpenseSubcategory)
class ExpenseSubcategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'is_active')
    list_filter = ('tenant', 'is_active')
    search_fields = ('name',)

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('date', 'expense_type', 'amount', 'paid_to', 'approval_status', 'posting_status')
    list_filter = ('tenant', 'expense_type', 'approval_status', 'posting_status', 'date')
    search_fields = ('paid_to', 'reference_no', 'notes')
    readonly_fields = ('created_at', 'updated_at', 'approval_timestamp')
