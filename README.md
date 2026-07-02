# BrandFlow AI

BrandFlow AI is a multilingual AI Content Operations Platform: **your brand’s AI content manager**. It plans, generates, approves, publishes, analyzes, and learns across English, Persian/Farsi RTL, and German.

## Architecture

- `apps/api`: FastAPI, SQLAlchemy 2.x models, JWT auth, RBAC, AI agents, connector architecture, approval workflow, analytics/report endpoints.
- `apps/web`: Next.js App Router, TypeScript, Tailwind, dark SaaS UI, locale routes for `en`, `de`, and `fa` with true RTL via `dir="rtl"`.
- `infra`: reserved for production deployment assets.
- PostgreSQL + pgvector image, Redis, worker placeholder, scheduler placeholder in Docker Compose.

## Run locally

```bash
cp .env.example .env
make up
```

Open:

- Web: http://localhost:3000/en
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

Without Docker:

```bash
cd apps/api && pip install -r requirements.txt && uvicorn app.main:app --reload
cd apps/web && npm install && npm run dev
```

## Seed data

```bash
make seed
```

Demo accounts use password `password123`:

| Email | Role |
|---|---|
| `admin@brandflow.ai` | super_admin |
| `owner@demo.com` | org_owner |
| `client@demo.com` | client_approver |

Seed includes a German aesthetic clinic, Iranian ecommerce shop with Telegram/Bale/WooCommerce, German IT services brand, and agency organization.

## Main routes

- `/en`, `/de`, `/fa`: landing pages.
- `/{locale}/auth/login`: login UI placeholder.
- `/{locale}/app/dashboard`: brand operating cockpit.
- `/{locale}/app/admin`: Super Admin command center.
- `/{locale}/public/approval/{token}`: mobile-first public approval preview.

## API highlights

Auth, organizations, brands, onboarding, Brand DNA, memory, calendar generation, draft generation/edit/revise/translate, approvals, public approval token actions, scheduling, publishing, assisted kit, analytics snapshots, weekly reports, assets, campaigns, connector webhooks, Bale, Bale Safir, and Super Admin endpoints are implemented in FastAPI.

## Real vs mocked

| Area | Status |
|---|---|
| Database models | Real SQLAlchemy foundation with required core models |
| Auth | Real JWT + bcrypt password hashing |
| RBAC | Permission matrix foundation |
| AI | Provider abstraction + deterministic mock agents; OpenAI/Anthropic/Gemini placeholders |
| Publishing | Real connector interfaces + mock end-to-end publishing |
| External APIs | Safe skeletons/placeholders only unless simple bot-style calls are configured later |
| Worker/scheduler | Runnable placeholders with documented job names |
| Storage | S3/MinIO environment placeholders; asset API mock |

## Connector status

| Connector | Direct | Assisted | Analytics | Approval bot | Notes |
|---|---:|---:|---:|---:|---|
| Mock | yes | yes | yes | yes | Demo default |
| Telegram | bot skeleton | yes | limited | yes | Bot token/chat_id placeholder |
| Bale Bot | bot skeleton | yes | manual/limited | yes | Defaults to `https://tapi.bale.ai/bot<token>/METHOD_NAME` pattern |
| Bale Safir | no | notifications | no | reminders | Opt-in phone messaging only |
| Instagram/Facebook | permission-gated placeholder | yes | placeholder | no | Meta review required |
| TikTok | permission-gated placeholder | yes | placeholder | no | App review required |
| LinkedIn | OAuth placeholder | yes | placeholder | no | Official API required |
| Google Business | API placeholder | yes | placeholder | no | Official API required |
| YouTube | upload placeholder | yes | placeholder | no | Quota-aware TODO |
| WooCommerce | REST placeholder | n/a | orders/products | no | Credentials required |
| GA4 | Data API placeholder | n/a | yes | no | Credentials required |
| Eitaa/Soroush/Aparat | disabled skeleton | yes | no | no | No unsafe automation |

## Telegram

The Telegram connector exposes capabilities for publishing text/photo/video/document/media groups, webhooks, polling, and approval bot buttons. Production requires official Bot API token, channel/group setup, admin permission verification, rate limit handling, and webhook hardening.

## Bale Bot

The Bale connector is first-class with provider key `bale`, configurable base URL, mock `send_message`, webhook/poll endpoints, approval button workflow placeholder, error mapping, and assisted publishing fallback.

## Bale Safir

The Bale Safir connector is separate (`bale_safir`) for direct notification/message use cases. It normalizes Iranian phones (`0912...`, `+98912...`, `98912...`), maps known Safir errors, stores message IDs in mock responses, and requires explicit consent before sending.

## Security notes

- No hardcoded production secrets; use `.env`.
- Public approval tokens are hashed in the database.
- Passwords use bcrypt.
- Connectors avoid scraping, browser automation, fake sessions, and policy-violating behavior.
- Bale Safir is opt-in only and should not be used for unsolicited bulk messaging.

## Production next steps

1. Replace SQLite/dev DB defaults with managed Postgres + pgvector migrations.
2. Add full Alembic autogeneration and migration lifecycle.
3. Implement encrypted token storage with KMS.
4. Add API-level rate limiting and CSRF/session hardening if cookie auth is used.
5. Complete real OAuth flows and official app reviews per platform.
6. Add Celery task implementations and Super Admin retry/cancel operations.
7. Add comprehensive frontend forms wired to API.
8. Expand tests with TestClient database fixtures and Playwright UI smoke tests.

## Known limitations

This MVP+ foundation works end-to-end using mock AI and mock connectors. Direct publishing to social networks requires official credentials, permissions, and app review where applicable.
