"""The workspace tests on a disposable PostgreSQL (Django creates and drops test_<name>).

Connection comes from the environment; HOST may be a unix-socket directory.
Never point this at a database whose data matters: the runner creates its own
test database, but the account needs CREATEDB.
"""
import os

from .workspace_test import *  # noqa: F401,F403

DATABASES = {'default': {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': os.environ.get('ZETRIX_PG_NAME', 'zetrix'),
    'USER': os.environ.get('ZETRIX_PG_USER', 'postgres'),
    'PASSWORD': os.environ.get('ZETRIX_PG_PASSWORD', ''),
    'HOST': os.environ.get('ZETRIX_PG_HOST', '127.0.0.1'),
    'PORT': os.environ.get('ZETRIX_PG_PORT', ''),
}}
