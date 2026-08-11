#!/usr/bin/env bash
#
# Container entry point.
#
# The previous start command was:
#
#     alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
#
# The '&&' meant any database problem — a wrong password, an unencoded '@',
# an unreachable host — stopped uvicorn from ever running. No port was bound,
# so Render failed the deploy and kept serving the previous instance. The
# service looked healthy while shipping stale code, and the actual error was
# only visible in a build log nobody was reading.
#
# This script decouples the two. Migrations still run first and their failure
# is still loud, but it no longer prevents the process from binding a port.
# A booted-but-degraded app can be interrogated over HTTP:
#
#     curl https://<service>/api/health
#
# reports the migration failure, the parsed database host, and the live
# connection error.
#
# Prefer Render's *Pre-Deploy Command* if you want migration failures to abort
# the deploy outright: put `alembic upgrade head` there and `./start.sh` in the
# Start Command. A failed pre-deploy aborts cleanly, names the error in Events,
# and leaves the old instance serving — which is the same protection '&&' was
# reaching for, without the silent-stale-code failure mode.

set -uo pipefail

MARKER="${MIGRATION_FAILURE_MARKER:-/tmp/inventory-saas-migrations-failed}"
rm -f "$MARKER"

echo "=== database configuration ==="
python -c "
from app.config import settings
from app.diagnostics import format_database_summary
print(format_database_summary(settings.DATABASE_URL))
" || echo "  (could not summarise DATABASE_URL — app.config failed to import)"

echo "=== alembic upgrade head ==="
migration_output="$(alembic upgrade head 2>&1)"
migration_status=$?
echo "$migration_output"

if [ $migration_status -ne 0 ]; then
    # Keep the tail only: enough to identify the failure, small enough that the
    # health endpoint stays readable.
    printf '%s\n' "$migration_output" | tail -n 20 > "$MARKER"
    echo "!!!"
    echo "!!! MIGRATIONS FAILED (exit $migration_status)."
    echo "!!! Starting the server anyway so the error is reachable at /api/health."
    echo "!!! Database-backed routes will fail until this is fixed."
    echo "!!!"
fi

echo "=== starting uvicorn on port ${PORT:-8000} ==="
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
