"""AEC Cinemas – Custom User Model with RBAC"""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.MD)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        STAFF = 'STAFF', 'Staff'
        ADMIN = 'ADMIN', 'Admin / Accountant'
        MD = 'MD', 'Managing Director'

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STAFF)
    phone = models.CharField(max_length=15, blank=True)
    # ── Tenant Foundation ──────────────────────────────────────────────────
    # nullable=True for backwards-compat; backfilled by migration 0003.
    # Will be made non-nullable in a later migration after all rows are filled.
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='users',
        help_text='Owning tenant. Null only during initial migration backfill.'
    )
    # ── End Tenant Foundation ──────────────────────────────────────────────
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    class Meta:
        app_label = 'accounts'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.full_name} ({self.role})"

    @property
    def is_md(self):
        return self.role == self.Role.MD

    @property
    def is_admin(self):
        return self.role in [self.Role.ADMIN, self.Role.MD]
