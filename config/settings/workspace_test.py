"""Isolated, disposable SQLite configuration for the scenario workspace tests."""
SECRET_KEY = 'test-only-not-a-production-secret'
DEBUG = False
ALLOWED_HOSTS = ['testserver', 'localhost']
INSTALLED_APPS = ['django.contrib.auth', 'django.contrib.contenttypes',
                  'django.contrib.sessions', 'apps.workspaces', 'apps.evidence', 'apps.decisions']
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
MIDDLEWARE = ['django.contrib.sessions.middleware.SessionMiddleware',
              'django.middleware.csrf.CsrfViewMiddleware',
              'django.contrib.auth.middleware.AuthenticationMiddleware']
ROOT_URLCONF = 'config.workspace_urls'
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
REST_FRAMEWORK = {'UNAUTHENTICATED_USER': 'django.contrib.auth.models.AnonymousUser'}
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
