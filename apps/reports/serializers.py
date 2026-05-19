from rest_framework import serializers
from .models import ManagementSnapshot, AIInsightReport, AIActionItem

class ManagementSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManagementSnapshot
        fields = '__all__'
        read_only_fields = ('tenant', 'saved_by', 'created_at')

class AIActionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIActionItem
        fields = '__all__'

class AIInsightReportSerializer(serializers.ModelSerializer):
    action_items = AIActionItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = AIInsightReport
        fields = '__all__'
