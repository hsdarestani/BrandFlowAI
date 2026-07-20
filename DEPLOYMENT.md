# Smarbiz deployment

The repository deploys to `91.107.157.75` through `.github/workflows/ci-deploy.yml` after a successful push to `main`.

## Required GitHub secret

- `PASS`: the current `root` SSH password for the server.

Password-based SSH is supported for the first deployment. Replace it with a dedicated deploy user and SSH key after the service is stable.

## Required DNS

Create these records at the DNS provider:

| Type | Name | Value |
|---|---|---|
| A | `@` | `91.107.157.75` |
| A | `www` | `91.107.157.75` |

Caddy obtains and renews HTTPS certificates automatically after DNS resolves and ports `80` and `443` reach the server.

## Server layout

- Current release: `/opt/smarbiz/current`
- Immutable releases: `/opt/smarbiz/releases/<git-sha>`
- Persistent secrets: `/opt/smarbiz/shared/.env.production`
- Persistent data: Docker volumes named under the `smarbiz` Compose project

The deploy workflow creates `.env.production` once with random PostgreSQL, JWT, and connector secrets. Later deploys preserve it, so sessions and database access remain stable.

## Runtime mode

The initial public deployment uses:

- `APP_ENV=staging`
- `DEMO_MODE=false`
- PostgreSQL + Redis
- real authentication and persistent workspaces
- deterministic `AI_PROVIDER=mock`
- mock external connectors disabled

This makes the core workspace usable without pretending that third-party publishing or a paid AI provider is connected. To move to strict production, edit `/opt/smarbiz/shared/.env.production`, add a real AI key/provider, set `APP_ENV=production`, and redeploy.

## Useful server commands

```bash
cd /opt/smarbiz/current

docker compose --env-file .env.production -f docker-compose.prod.yml ps
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f --tail=200
docker compose --env-file .env.production -f docker-compose.prod.yml restart api web caddy
```

Health endpoints:

- Public proxy: `https://smarbiz.sbs/healthz`
- API: `https://smarbiz.sbs/api/health`
