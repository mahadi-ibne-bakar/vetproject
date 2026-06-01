"""
Django settings for vetproject.

Environment variables are loaded from .env via python-decouple.
Never put secrets directly in this file.
"""

from pathlib import Path
from decouple import config, Csv

# ─── Paths ────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent


# ─── Security ─────────────────────────────────────────────────────────────────

SECRET_KEY = config('SECRET_KEY')

REMINDER_SECRET = config('REMINDER_SECRET', default='')

DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv(), default='localhost,127.0.0.1')


# ─── Applications ─────────────────────────────────────────────────────────────

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'django.contrib.sites',
    'storages',

    # Third-party
    'tailwind',
    'crispy_forms',
    'crispy_tailwind',
    'theme',

    # Our apps (we will add these as we create them)
    'accounts',
    'core',
    'consultations',
    # 'prescriptions',
    'blog',
]

TAILWIND_APP_NAME = 'theme'

CRISPY_ALLOWED_TEMPLATE_PACKS = 'tailwind'
CRISPY_TEMPLATE_PACK = 'tailwind'


# ─── Middleware ───────────────────────────────────────────────────────────────

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Custom middleware — must come after AuthenticationMiddleware
    'accounts.middleware.BannedUserMiddleware',
    'accounts.middleware.RoleRedirectMiddleware',
]


# ─── URLs and WSGI ────────────────────────────────────────────────────────────

ROOT_URLCONF = 'vetproject.urls'

WSGI_APPLICATION = 'vetproject.wsgi.application'


# ─── Templates ────────────────────────────────────────────────────────────────

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Global templates folder
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.site_settings',
            ],
        },
    },
]


# ─── Database ─────────────────────────────────────────────────────────────────
# Reads DATABASE_URL from .env
# Local:      sqlite:///db.sqlite3
# Production: postgresql://... (Supabase URL, set in Chunk 5)

from decouple import config
import dj_database_url  # We will add this package next

DATABASES = {
    'default': dj_database_url.parse(
        config('DATABASE_URL')
    )
}


# ─── Authentication ───────────────────────────────────────────────────────────

AUTH_USER_MODEL = 'accounts.User'  # Our custom user model (created in Day 2)

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'


# ─── Internationalisation ─────────────────────────────────────────────────────

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Dhaka'
USE_I18N = True
USE_TZ = True


# ─── Static and Media Files ───────────────────────────────────────────────────

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ─── Storage (Supabase S3-compatible) ─────────────────────────────────────────
SUPABASE_URL            = config('SUPABASE_URL', default='')
SUPABASE_BUCKET         = config('SUPABASE_BUCKET', default='vetproject-media')
SUPABASE_S3_ACCESS_KEY  = config('SUPABASE_S3_ACCESS_KEY', default='')
SUPABASE_S3_SECRET_KEY  = config('SUPABASE_S3_SECRET_KEY', default='')

import re as _re
_match = _re.search(r'https://([^.]+)\.supabase\.co', SUPABASE_URL)
SUPABASE_PROJECT_ID = _match.group(1) if _match else ''

if SUPABASE_URL and SUPABASE_S3_ACCESS_KEY and SUPABASE_S3_SECRET_KEY:
    STORAGES = {
        'default': {
            'BACKEND': 'storages.backends.s3.S3Storage',
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
        },
    }

    AWS_ACCESS_KEY_ID       = SUPABASE_S3_ACCESS_KEY
    AWS_SECRET_ACCESS_KEY   = SUPABASE_S3_SECRET_KEY
    AWS_STORAGE_BUCKET_NAME = SUPABASE_BUCKET
    AWS_S3_ENDPOINT_URL     = (
        f'https://{SUPABASE_PROJECT_ID}.supabase.co/storage/v1/s3'
    )
    AWS_DEFAULT_ACL         = None
    AWS_QUERYSTRING_AUTH    = False
    AWS_S3_FILE_OVERWRITE   = False
    AWS_S3_ADDRESSING_STYLE = 'path'

    # Force public CDN URL for all media files
    AWS_S3_CUSTOM_DOMAIN = (
        f'{SUPABASE_PROJECT_ID}.supabase.co'
        f'/storage/v1/object/public/{SUPABASE_BUCKET}'
    )

    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/'
    MEDIA_ROOT = BASE_DIR / 'media'

else:
    STORAGES = {
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
        },
    }
    MEDIA_URL  = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'


# ─── Email ────────────────────────────────────────────────────────────────────

EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST          = 'smtp.gmail.com'
EMAIL_PORT          = 587
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL  = config('DEFAULT_FROM_EMAIL', default=EMAIL_HOST_USER)
EMAIL_TIMEOUT       = 10


# ─── Default Primary Key ──────────────────────────────────────────────────────

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ─── Security Headers (active in production only) ─────────────────────────────

if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 3600
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# ─── Production Static Files ──────────────────────────────────────────────────
# Whitenoise serves static files directly — no separate static file server needed
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True

# ── Logging ────────────────────────────────────────────────────────────────────
LOGGING = {
    'version':                  1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {message}',
            'style':  '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style':  '{',
        },
    },
    'handlers': {
        'console': {
            'class':     'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level':    'WARNING',
    },
    'loggers': {
        'django': {
            'handlers':  ['console'],
            'level':     config('DJANGO_LOG_LEVEL', default='WARNING'),
            'propagate': False,
        },
        'django.request': {
            'handlers':  ['console'],
            'level':     'ERROR',
            'propagate': False,
        },
        'consultations': {
            'handlers':  ['console'],
            'level':     'INFO',
            'propagate': False,
        },
        'core': {
            'handlers':  ['console'],
            'level':     'INFO',
            'propagate': False,
        },
    },
}

# ── Production security ────────────────────────────────────────────────────────
if not DEBUG:
    # Force HTTPS
    SECURE_SSL_REDIRECT                  = True
    SECURE_PROXY_SSL_HEADER              = ('HTTP_X_FORWARDED_PROTO', 'https')

    # HSTS — tell browsers to only use HTTPS for 1 year
    SECURE_HSTS_SECONDS                  = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS       = True
    SECURE_HSTS_PRELOAD                  = True

    # Cookies only sent over HTTPS
    SESSION_COOKIE_SECURE                = True
    CSRF_COOKIE_SECURE                   = True

    # Prevent clickjacking
    X_FRAME_OPTIONS                      = 'DENY'

    # Prevent browsers from MIME-sniffing
    SECURE_CONTENT_TYPE_NOSNIFF          = True

    # XSS protection header
    SECURE_BROWSER_XSS_FILTER           = True

    # Referrer policy
    SECURE_REFERRER_POLICY               = 'strict-origin-when-cross-origin'

# ── Cache (database-backed, shared across workers) ────────────────────────────
CACHES = {
    'default': {
        'BACKEND':  'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'django_cache',
        'TIMEOUT':  300,  # 5 minutes default
        'OPTIONS':  {
            'MAX_ENTRIES': 10000,
        }
    }
}


SITE_ID = 1