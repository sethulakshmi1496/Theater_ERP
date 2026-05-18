from rest_framework import serializers
from apps.integrations.models import DistrictDCRReport, DCRTicketClass, DCRDiscrepancy

class DCRTicketClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = DCRTicketClass
        fields = '__all__'

class DCRDiscrepancySerializer(serializers.ModelSerializer):
    class Meta:
        model = DCRDiscrepancy
        fields = '__all__'

class DistrictDCRReportSerializer(serializers.ModelSerializer):
    ticket_classes = DCRTicketClassSerializer(many=True, read_only=True)
    discrepancies = DCRDiscrepancySerializer(many=True, read_only=True)

    class Meta:
        model = DistrictDCRReport
        fields = '__all__'
        read_only_fields = ['status', 'tenant', 'uploaded_by', 'ticket_classes', 'discrepancies']
