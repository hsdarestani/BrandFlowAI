# Smarbiz functional release

This release completes the connected product workflows, fixes the root-domain 404 by redirecting `/` to `/fa`, and runs the API, web app, Celery worker, Celery scheduler, PostgreSQL, Redis, and persistent asset storage as one production stack.

Validation covers API tests, a single Alembic head, TypeScript, the Next.js production build, Compose validation, and production image builds.
