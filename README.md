# Smarbiz

Smarbiz is a multilingual AI-assisted content operations workspace for planning, creating, reviewing, scheduling, publishing, measuring, and improving brand content in English, Persian/Farsi RTL, and German.

## What works end to end

- Secure signup/login, tenant-scoped organizations and brands, and guided onboarding.
- Brand Pulse knowledge base with products, personas, rules, memory, JSON import/export, and real CRUD.
- Content Calendar → Content Studio → Approval → Schedule workflow.
- Public approval links with approve, request-changes, reject, reviewer identity, and history.
- Campaign planning with generated plan items and idempotent draft/calendar creation.
- Asset upload, review, metadata management, persistent storage, and authenticated download.
- Manual or connected analytics, recommendations, and Brand Memory learning.
- Weekly/custom reports with regenerate, edit, Markdown export, and Brevo email delivery when configured.
- Celery + Redis worker and beat scheduler for due scheduled posts, atomic claiming, bounded retries, and duplicate-publication protection.
- Production Docker/Caddy deployment and GitHub Actions CI/deploy.

## Architecture

- `apps/api`: FastAPI, SQLAlchemy 2.x, Alembic, JWT auth, tenant/RBAC guards, connectors, reports, assets, and Celery jobs.
- `apps/web`: Next.js App Router, TypeScript, Tailwind, locale routes (`en`, `de`, `fa`), responsive SaaS UI, and true Persian RTL.
- PostgreSQL + pgvector, Redis, API, worker, scheduler, web, and Caddy in Docker Compose.
- `apps/api/app/entrypoint.py` is the supported API entrypoint. It preserves the main API surface and installs production route replacements such as secure file streaming and real Brevo report delivery.

## Run locally with Docker

```bash
cp .env.example .env
make up
```

Open:

- Web: `http://localhost:3000/en`
- API docs: `http://localhost:8000/docs`
- API health: `http://localhost:8000/health`

Local Docker uses one shared PostgreSQL database, Redis broker, and persistent asset volume for the API, worker, and scheduler.

## Run without Docker

Start PostgreSQL and Redis first, then:

```bash
cd apps/api
pip install -r requirements.txt
alembic upgrade head
uvicorn app.entrypoint:app --reload
```

```bash
cd apps/api
python worker.py
```

```bash
cd apps/api
python scheduler.py
```

```bash
cd apps/web
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

## Tests and builds

```bash
make test
cd apps/web && npm run lint && npm run build
```

CI also validates the production Compose file and builds all production containers.

## Seed data

Seed data is intended only for local/demo environments:

```bash
make seed
```

Demo password: `password123`

| Email | Role |
|---|---|
| `admin@smarbiz.sbs` | super_admin |
| `owner@demo.com` | org_owner |
| `client@demo.com` | client_approver |

The production login screen shows these shortcuts only when the API explicitly reports Demo Mode.

## Environment modes

### Development/demo

- `APP_ENV=development`
- `DEMO_MODE=true`
- `AI_PROVIDER=mock`
- `ALLOW_MOCK_CONNECTORS=true`

### Public staging

- real auth, PostgreSQL, Redis, assets, approvals, reports, and background jobs
- `DEMO_MODE=false`
- mock external connectors disabled
- deterministic AI may remain enabled until a real provider key is configured

### Strict production

Production validation rejects SQLite, weak secrets, Demo Mode, mock AI, mock connectors, wildcard/localhost CORS, and missing connector encryption secret.

See [`DEPLOYMENT.md`](DEPLOYMENT.md) for the server layout, DNS, firewall, Cloudflare, Caddy, and GitHub secret requirements.

## Connector truthfulness

A connector is shown as connected only after saved configuration and a successful test. Integrations that require official OAuth/app review remain unavailable or assisted until those external requirements are completed.

Currently practical direct integrations include public approval links, configured bot-style Telegram/Bale flows, WooCommerce/GA4 data connections where credentials are supplied, and Brevo transactional report email. Instagram/Facebook, LinkedIn, TikTok, YouTube, and Google Business still require official provider apps, OAuth flows, permissions, quotas, and review before direct production publishing can be claimed.

## AI providers

The deterministic provider keeps development and public staging usable without sending brand data to a third party. Strict production requires a real provider configuration and API key. Do not place provider keys in the browser; manage them through server environment variables.

## Security notes

- No production secrets are committed.
- Passwords are bcrypt-hashed and JWT settings are environment-driven.
- Public approval tokens are stored hashed.
- Organization/brand routes are tenant guarded.
- Super Admin cannot be granted through public signup.
- Auth endpoints are rate-limited.
- Asset downloads require a valid tenant-scoped bearer token.
- Connector credentials are never returned to the browser after saving.
