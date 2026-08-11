"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine
from app.diagnostics import (
    check_database,
    migration_failure_detail,
    migrations_failed,
    public_database_report,
)
from app.routes import auth, webhooks, inventory, waste, recipes, reports, billing, debug

app = FastAPI(title="Inventory SaaS", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(auth.router)
app.include_router(webhooks.router)
app.include_router(inventory.router)
app.include_router(waste.router)
app.include_router(recipes.router)
app.include_router(reports.router)
app.include_router(billing.router)

# Diagnostics only — set DEBUG_ENDPOINT_ENABLED=true to expose, and unset it again
# afterwards. Leaving this on in production discloses configuration state publicly.
if settings.DEBUG_ENDPOINT_ENABLED:
    app.include_router(debug.router)


@app.get("/api/health")
async def health():
    """Liveness plus enough diagnosis to fix a broken deploy from a terminal.

    Always returns 200. The status field carries the verdict: a non-200 here
    would make Render's health check fail the deploy, which is precisely the
    silent-rollback-to-stale-code behaviour this endpoint exists to expose.

    No secrets are included — describe_database_url() reports the connection
    components with the password reduced to a boolean.
    """
    verbose = settings.DEBUG_ENDPOINT_ENABLED
    database = check_database(engine, verbose=verbose)
    migrations = {"status": "failed" if migrations_failed() else "ok"}
    if migrations["status"] == "failed" and verbose:
        migrations["detail"] = migration_failure_detail()

    degraded = database["status"] != "ok" or migrations["status"] != "ok"

    return {
        "status": "degraded" if degraded else "ok",
        "version": "0.1.0",
        "database": database,
        "database_url": public_database_report(settings.DATABASE_URL),
        "migrations": migrations,
    }
