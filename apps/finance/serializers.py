from rest_framework import serializers
from .models import Distributor, FilmContract, FilmAdvance, DistributorShare, Settlement, DistributorStatement

class DistributorSerializer(serializers.ModelSerializer):
    movies_linked = serializers.SerializerMethodField()

    class Meta:
        model = Distributor
        fields = '__all__'
        read_only_fields = ['tenant', 'created_at']

    def get_movies_linked(self, obj):
        # returns distinct movie titles linked via contracts
        return list(obj.contracts.values_list('movie__title', flat=True).distinct())

class FilmContractSerializer(serializers.ModelSerializer):
    movie_title = serializers.CharField(source='movie.title', read_only=True)
    distributor_name = serializers.CharField(source='distributor.name', read_only=True)
    advance_paid_amount = serializers.SerializerMethodField()

    class Meta:
        model = FilmContract
        fields = '__all__'
        read_only_fields = ['tenant', 'created_at', 'entered_by']

    def get_advance_paid_amount(self, obj):
        from django.db.models import Sum
        return obj.advances.aggregate(t=Sum('advance_amount'))['t'] or 0

    def validate(self, data):
        if self.instance and self.instance.approval_status == FilmContract.ApprovalStatus.APPROVED:
            raise serializers.ValidationError("Cannot edit an approved contract.")
        return data

class FilmAdvanceSerializer(serializers.ModelSerializer):
    movie_title = serializers.CharField(source='movie.title', read_only=True)
    
    class Meta:
        model = FilmAdvance
        fields = '__all__'
        read_only_fields = ['tenant', 'created_at', 'entered_by']

class DistributorShareSerializer(serializers.ModelSerializer):
    class Meta:
        model = DistributorShare
        fields = '__all__'
        read_only_fields = ['tenant', 'created_at', 'entered_by', 'share_amount']

class SettlementSerializer(serializers.ModelSerializer):
    contract_info = serializers.CharField(source='contract.__str__', read_only=True)
    
    class Meta:
        model = Settlement
        fields = '__all__'
        read_only_fields = ['tenant', 'created_at', 'generated_by', 'approved_by']

class DistributorStatementSerializer(serializers.ModelSerializer):
    distributor_name = serializers.CharField(source='distributor.name', read_only=True)
    
    class Meta:
        model = DistributorStatement
        fields = '__all__'
        read_only_fields = ['tenant', 'generated_at', 'generated_by']
