#!/bin/sh
set -eu

python - <<'PY'
import os
import sys
import time
from sqlalchemy import create_engine, text

url = os.environ.get("DATABASE_URL", "")
if not url:
    sys.exit("DATABASE_URL is not configured")

last_error = None
for _ in range(60):
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text("select 1"))
        print("Database is ready")
        break
    except Exception as exc:
        last_error = exc
        time.sleep(2)
else:
    sys.exit(f"Database did not become ready: {last_error}")
PY

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    alembic upgrade head
fi

exec "$@"
