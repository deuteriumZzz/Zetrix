"""Provision a disposable local-only account, never a production identity."""
import json
import os
import secrets
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = 'Create a local developer account and a private credentials file.'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='zetrix-local')
        parser.add_argument('--credentials-file', required=True)

    def handle(self, *args, **options):
        if not getattr(settings, 'ZETRIX_LOCAL_DEVELOPMENT', False):
            raise CommandError('This command requires config.settings.workspace_local.')
        username = options['username']
        if not username or len(username) > 150:
            raise CommandError('Username must contain 1–150 characters.')
        path = Path(options['credentials_file']).resolve()
        if get_user_model().objects.filter(username=username).exists():
            raise CommandError('Account already exists; credentials were not changed.')
        path.parent.mkdir(parents=True, exist_ok=True)
        password = secrets.token_urlsafe(24)
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as exc:
            raise CommandError('Credentials file already exists; refusing to overwrite it.') from exc
        try:
            with os.fdopen(descriptor, 'w') as output:
                json.dump({'username': username, 'password': password,
                           'scope': 'Local Zetrix development only'}, output, indent=2)
                output.write('\n')
            with transaction.atomic():
                get_user_model().objects.create_user(username=username, password=password, is_staff=True)
        except Exception:
            path.unlink(missing_ok=True)
            raise
        self.stdout.write(f'Local account created. Credentials saved privately: {path}')
