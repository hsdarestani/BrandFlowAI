# Smarbiz deployment

The repository deploys to `91.107.157.75` through `.github/workflows/ci-deploy.yml` after a successful push to `main`.

## Required GitHub secret

- `PASS`: the current `root` SSH password for the server.

Password-based SSH is supported for the first deployment. Replace it with a dedicated deploy user and SSH key after the service is stable.

## DNS and HTTPS

The public records may remain proxied through Cloudflare:

| Type | Name | Origin |
|---|---|---|
| A | `@` | `91.107.157.75` |
| A | `www` | `91.107.157.75` |

The host already uses Nginx and Certbot on ports `80` and `443`. The deploy workflow preserves that topology, installs the repository-managed Smarbiz Nginx site, validates it before reload, and keeps a copy of the previous site in `/opt/smarbiz/shared` for recovery.

Only Nginx is public. Docker publishes the application on loopback-only ports:

- Web: `127.0.0.1:13000`
- API: `127.0.0.1:18000`
- PostgreSQL and Redis: Docker network only

## Server layout

- Current release: `/opt/smarbiz/current`
- Immutable releases: `/opt/smarbiz/releases/<git-sha>`
- Persistent secrets: `/opt/smarbiz/shared/.env.production`
- Nginx backups: `/opt/smarbiz/shared/nginx-smarbiz-before-<git-sha>.conf`
- Persistent data: Docker volumes under the `smarbiz` Compose project

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
docker compose --env-file .env.production -f docker-compose.prod.yml restart api web
nginx -t && systemctl reload nginx
ufw status verbose
```

Health endpoints:

- Public proxy: `https://smarbiz.sbs/healthz`
- API: `https://smarbiz.sbs/api/health`
- Landing page: `https://smarbiz.sbs/en`
