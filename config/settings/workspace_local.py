"""Loopback-only development profile; separate SQLite DB, no legacy apps.

Set ZETRIX_LOCAL_DB to an explicit disposable database path for development.
A generated process key intentionally invalidates sessions on restart unless
DJANGO_SECRET_KEY is supplied by the developer's environment.
"""
import os
from pathlib import Path
from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY') or get_random_secret_key()
DEBUG = True
ZETRIX_LOCAL_DEVELOPMENT = True
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '[::1]']
INSTALLED_APPS = ['django.contrib.auth', 'django.contrib.contenttypes',
                  'django.contrib.sessions', 'rest_framework',
                  'apps.workspaces', 'apps.evidence', 'apps.decisions']
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3',
                         'NAME': os.environ.get('ZETRIX_LOCAL_DB', str(BASE_DIR / 'var' / 'zetrix-local.sqlite3'))}}
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware',
              'django.contrib.sessions.middleware.SessionMiddleware',
              'django.middleware.common.CommonMiddleware',
              'django.middleware.csrf.CsrfViewMiddleware',
              'django.contrib.auth.middleware.AuthenticationMiddleware',
              'django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF = 'config.workspace_urls'
USE_TZ = True
TIME_ZONE = 'UTC'
LANGUAGE_CODE = 'ru'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = False  # This profile is only served on loopback HTTP.
CSRF_COOKIE_SECURE = False
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
]
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
REST_FRAMEWORK = {'UNAUTHENTICATED_USER': 'django.contrib.auth.models.AnonymousUser'}
DATA_UPLOAD_MAX_MEMORY_SIZE = 3 * 1024 * 1024
CELERY_BEAT_SCHEDULE = {}
