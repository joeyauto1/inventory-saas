"""The debug endpoint must be off unless explicitly switched on.

/api/debug/env reports which secrets are configured, the frontend URL and the
Square app-ID prefix. That is fine as a deliberate diagnostic and not fine as a
publicly reachable route.
"""

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def test_debug_endpoint_defaults_to_disabled():
    """No DEBUG_ENDPOINT_ENABLED in the environment means the route is absent."""
    assert settings.DEBUG_ENDPOINT_ENABLED is False

    with TestClient(app) as client:
        assert client.get("/api/debug/env").status_code == 404


def test_health_endpoint_still_reachable():
    """The gate must not take the unrelated health check down with it."""
    with TestClient(app) as client:
        resp = client.get("/api/health")

    assert resp.status_code == 200
    # "ok" or "degraded" depending on whether a database is reachable — the
    # point of this test is that the route answers at all. Health deliberately
    # returns 200 even when degraded so a failing deploy stays diagnosable
    # rather than being rolled back to stale code by Render's health check.
    assert resp.json()["status"] in ("ok", "degraded")
    assert resp.json()["version"] == "0.1.0"
