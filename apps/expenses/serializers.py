from rest_framework import serializers
from .models import Expense, ExpenseSubcategory

class ExpenseSubcategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseSubcategory
        fields = '__all__'
        read_only_fields = ['tenant']

class ExpenseSerializer(serializers.ModelSerializer):
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)
    entered_by_name = serializers.CharField(source='entered_by.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)

    class Meta:
        model = Expense
        fields = '__all__'
        read_only_fields = [
            'tenant', 'entered_by', 'approved_by', 
            'approval_timestamp', 'posting_status', 
            'created_at', 'updated_at'
        ]

    def validate(self, data):
        # Allow editing only if not approved/posted
        if self.instance:
            if self.instance.approval_status == Expense.ApprovalStatus.APPROVED:
                raise serializers.ValidationError("Cannot edit an approved expense.")
            if self.instance.posting_status == Expense.PostingStatus.POSTED:
                raise serializers.ValidationError("Cannot edit a posted expense.")
        return data
