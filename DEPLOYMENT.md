# Legacy deployment checklist

The Compose files below run the older application profile. They do not deploy
the isolated Zetrix v2 MVP (`config.settings.mvp`) or provide its separate
database, onboarding, PostgreSQL concurrency checks and staging gates. Do not
use these instructions as a v2 release procedure. See [docs/BACKEND.md](docs/BACKEND.md)
and [docs/MVP.md](docs/MVP.md) for the current local implementation and open
release gates.

The legacy Compose example is provider-agnostic and assumes a VM with a
host-level reverse proxy. Docker Compose 2.24.4+ is required because the
production override uses `!override` to remove development ports and bind
mounts.

## 1. Accounts/services you need to create yourself

None of these can be set up on your behalf — they all require your own
billing details and identity verification:

- A host that can run Docker Compose (VM or a platform with Docker support)
- A domain name, pointed at that host
- (Optional but recommended) [Sentry](https://sentry.io) project — `SENTRY_DSN`
- (Optional) SMTP provider for password-reset emails (SendGrid, Postmark, SES...)
- (Optional) Stripe account, once you're ready to charge — see `apps/billing/`

## 2. Required environment variables

Copy `.env.example` to `.env` and fill in, at minimum:

| Variable | Notes |
|---|---|
| `DJANGO_SECRET_KEY` | Generate with `python -c "import secrets; print(secrets.token_urlsafe(50))"` — has no default, app refuses to start without it |
| `DJANGO_DEBUG` | Must be `False` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated, including `zetrix.app` when the cabinet uses this host |
| `CORS_ALLOWED_ORIGINS` | Origins used by any legacy cross-origin frontend; the v2 cabinet uses same-origin requests |
| `CSRF_TRUSTED_ORIGINS` | Include `https://zetrix.app` |
| `DB_PASSWORD` | Don't ship with the `postgres`/`postgres` dev default |
| `FRONTEND_URL` | Used to build password-reset links |

Optional but you'll want them for full functionality:
`GROQ_API_KEY` (business-climate LLM), `TELEGRAM_BOT_TOKEN` (bot),
`SENTRY_DSN` (error tracking), `EMAIL_*` (password reset emails),
`STRIPE_*` (billing — see `apps/billing/`).

For the legacy profile behind the Caddy example below, set
`DJANGO_SECURE_SSL_REDIRECT=False`; Caddy terminates TLS and Django otherwise
redirects each proxied HTTP request back to HTTPS. The isolated v2 profile
instead has an explicit `DJANGO_TRUST_HTTPS_PROXY=true` option for a trusted
proxy that strips client-supplied forwarding headers.

## 3. Legacy stack only

```bash
git clone <your-repo> && cd Zetrix
cp .env.example .env   # fill in the table above
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py seed_geo
docker compose exec web python manage.py seed_plans
```

The `web` command runs `migrate` and `collectstatic` on every start/restart.
These commands do not complete the v2 MVP release gates above.

## 4. Reverse proxy / TLS

`docker-compose.prod.yml` removes the inherited Postgres, Redis and Airflow
host ports and binds `web` only to `127.0.0.1:8000`. It does not terminate TLS.
The following Caddy layout shows the same-origin routing required by a future
v2 deployment: the cabinet requests `/api/v2/` on its own origin, and direct
navigation to `/app/...` must load `app/index.html`. It is not sufficient to
deploy the v2 backend by itself:

```caddyfile
zetrix.app {
    root * /var/www/zetrix-frontend/dist
    redir /app /app/ 308
    handle /api/* {
        reverse_proxy localhost:8000
    }
    handle /app/* {
        try_files {path} /app/index.html
        file_server
    }
    handle {
        try_files {path} /index.html
        file_server
    }
}
```

Build the frontend with `cd frontend && npm run build` (outputs to
`frontend/dist/`). The cabinet uses relative `/api/v2/` requests; no
`VITE_API_URL` setting is used. Keep `app/index.html` and its assets in the
deployed `dist/` directory. Verify a direct refresh of `/app/org/...` and a
same-origin `/api/v2/auth/csrf/` request after deployment.

## 5. Backups

Nothing automated exists yet. Minimum viable backup for the Postgres volume:

```bash
docker compose exec -T db pg_dump -U postgres bali_market | gzip > backup-$(date +%F).sql.gz
```

Cron this, and store off the host (S3, Backblaze, etc.) — a snapshot living
on the same disk as the database it backs up isn't a real backup.

## 6. What's already wired, what isn't

**Handled for the legacy profile:**
- Error tracking — Sentry auto-initializes if `SENTRY_DSN` is set (`config/settings/production.py`)
- HTTPS hardening (HSTS, secure cookies) — `config/settings/production.py`, on by default
- CI — `.github/workflows/ci.yml` runs the full backend + frontend test suite on every push/PR
- Rate limiting — DRF throttle classes are configured, but the legacy
  production profile uses a per-worker local cache. Use a shared cache before
  relying on those limits across workers.

**Not handled — deliberately, needs a decision from you:**
- No CD (auto-deploy on merge) — added CI only, wire a deploy step once you've picked a host
- No automated DB backups (see §5)
- No staging environment — only dev (`docker-compose.yml`) and prod
- No CDN/static asset offload — Whitenoise serves static files directly from `web`, fine at small scale
