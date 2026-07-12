"""
Test settings — overrides production settings for fast, isolated testing.
Uses SQLite instead of Supabase so tests run without credentials.
Disables external services (email, storage) so tests are fully offline.
"""

from vetproject.settings import *

# Use SQLite for speed
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME':   BASE_DIR / 'test_db.sqlite3',
    }
}

# Use in-memory cache for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Use local file storage for tests
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}

# Suppress emails during tests
EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'

# Fast password hashing for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable debug toolbar
INSTALLED_APPS = [
    app for app in INSTALLED_APPS
    if app != 'debug_toolbar'
]

# Disable security redirects for tests
SECURE_SSL_REDIRECT = False