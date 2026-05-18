"""AEC Cinemas – Accounts Serializers & Views"""

from rest_framework import serializers, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import get_user_model

User = get_user_model()


class TenantSerializer(serializers.Serializer):
    """Lightweight tenant info exposed to the frontend."""
    id = serializers.IntegerField()
    name = serializers.CharField()
    slug = serializers.CharField()
    plan = serializers.CharField()
    timezone = serializers.CharField()
    currency = serializers.CharField()


class UserSerializer(serializers.ModelSerializer):
    tenant = TenantSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'role', 'phone', 'is_active', 'created_at', 'tenant']
        read_only_fields = ['id', 'created_at', 'tenant']

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['email', 'full_name', 'role', 'phone', 'password']

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        data = serializer.data

        # Prefer middleware-cached set, fall back to DB query (for tests / direct calls)
        active_modules = getattr(request, 'active_modules', None)
        if not active_modules and request.user.tenant_id:
            from apps.tenants.models import TenantModule
            active_modules = list(
                TenantModule.objects.filter(
                    tenant_id=request.user.tenant_id,
                    is_enabled=True
                ).values_list('module_key', flat=True)
            )
        data['active_modules'] = sorted(active_modules or [])
        return Response(data)


class UserListCreateView(generics.ListCreateAPIView):
    queryset = User.objects.all().order_by('full_name')
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UserCreateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            from apps.accounts.permissions import IsMDOrAdmin
            return [IsMDOrAdmin()]
        return [IsAuthenticated()]


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        from apps.accounts.permissions import IsMDOrAdmin
        return [IsMDOrAdmin()]
