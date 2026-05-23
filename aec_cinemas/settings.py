"""
AEC Cinemas ERP
Django Settings – Neon PostgreSQL Edition
"""

import os
from pathlib import Path
from datetime import timedelta

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'aec-cinemas-dev-secret-key-change-in-prod')

DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'django_celery_beat',

    # AEC Cinemas Apps
    'apps.tenants',        # Tenant Foundation — must be first
    'apps.accounts',
    'apps.screens',
    'apps.bookings',
    'apps.revenue',
    'apps.operations',
    'apps.finance',
    'apps.payroll',
    'apps.settings_app',
    'apps.reports',
    'apps.audit',
    'apps.expenses',
    'apps.integrations',
    'apps.parking',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.tenants.middleware.TenantMiddleware',    # Tenant context injection
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'aec_cinemas.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'aec_cinemas.wsgi.application'

# ─── DATABASE – Neon PostgreSQL (Cloud ACID) ──────────────────────────────────
# Priority: DATABASE_URL > individual DB_* vars > local defaults
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    import re
    # Parse DATABASE_URL: postgresql://user:pass@host:port/dbname
    match = re.match(
        r'postgresql://([^:]+):([^@]+)@([^:/]+):?(\d+)?/([^?]+)',
        DATABASE_URL
    )
    if match:
        _user, _pass, _host, _port, _name = match.groups()
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': _name,
                'USER': _user,
                'PASSWORD': _pass,
                'HOST': _host,
                'PORT': _port or '5432',
                'OPTIONS': {
                    'sslmode': 'require',
                    'options': '-c default_transaction_isolation=serializable',
                },
                'CONN_MAX_AGE': 60,          # Connection pooling for Neon
            }
        }
    else:
        raise ValueError(f"Could not parse DATABASE_URL: {DATABASE_URL}")
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'aec_cinemas_db'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', 'postgres'),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'OPTIONS': {
                'sslmode': os.environ.get('DB_SSLMODE', 'prefer'),
                'options': '-c default_transaction_isolation=serializable',
            },
            'CONN_MAX_AGE': 60,
        }
    }

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalisation – IST
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
    'EXCEPTION_HANDLER': 'apps.audit.utils.custom_exception_handler',
}

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# CORS – Allow React dev server and production frontend domain
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://localhost:3000',
    'http://127.0.0.1:5173',
]
_cors_origins = os.environ.get('CORS_ALLOWED_ORIGINS')
if _cors_origins:
    for _origin in _cors_origins.split(','):
        _o = _origin.strip()
        if _o:
            CORS_ALLOWED_ORIGINS.append(_o)

CORS_ALLOW_CREDENTIALS = True

# Celery
CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_TIMEZONE = 'Asia/Kolkata'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# WhiteNoise storage settings for Django 4.2+ / 5.x / 6.x
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# ─── BUSINESS CONSTANTS ──────────────────────────────────────────────────────
THEATER_TOTAL_SEATS = 434          # Total capacity for occupancy formula
THEATER_WORKING_DAYS = 26          # Standard working days for payroll proration
