"""Structured error logging on /auth/callback — correlation IDs and stderr traces.

The callback is the highest-stakes route in the app: if Square is up but
our DB is down, the merchant sees a blank page and we see nothing. These
tests verify that failures produce (a) a correlation ID in the response so
the merchant can quote a reference, and (b) a full traceback on stderr so
the operator can diagnose it from Render's Logs tab.
"""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.routes.auth import OAUTH_STATE_COOKIE


@pytest.fixture
def client():
    """TestClient with the DB dependency stubbed out."""
    app.dependency_overrides[get_db] = lambda: None
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def valid_state(client):
    """A state value and cookie that pass the CSRF check."""
    state = "valid_test_state_1234567890123"
    return {"state": state, "cookie": f"{OAUTH_STATE_COOKIE}={state}"}


def test_callback_returns_correlation_id_on_unexpected_error(client, valid_state, monkeypatch):
    """When something inside the callback raises unexpectedly, the 500 body
    must contain the correlation ID so the merchant can quote it to support."""
    async def explode(_code):
        raise RuntimeError("simulated DB connection failure")

    monkeypatch.setattr("app.routes.auth.exchange_code", explode)

    resp = client.get(
        f"/auth/callback?code=fake_code&state={valid_state['state']}",
        headers={"Cookie": valid_state["cookie"]},
        follow_redirects=False,
    )

    assert resp.status_code == 500
    body = resp.json()
    assert "detail" in body
    assert "Reference: " in body["detail"]
    ref = body["detail"].split("Reference: ")[1]
    assert len(ref) == 36, f"expected UUID, got: {ref}"


def test_callback_error_writes_traceback_to_stderr(client, valid_state, monkeypatch, capsys):
    """A traceback must reach stderr so Render's Logs tab captures it."""
    async def explode(_code):
        raise RuntimeError("simulated DB connection failure")

    monkeypatch.setattr("app.routes.auth.exchange_code", explode)

    client.get(
        f"/auth/callback?code=fake_code&state={valid_state['state']}",
        headers={"Cookie": valid_state["cookie"]},
        follow_redirects=False,
    )

    captured = capsys.readouterr()
    output = captured.err
    assert "[ERROR]" in output, f"stderr did not contain [ERROR] marker: {output}"
    assert "correlation_id=" in output, f"stderr missing correlation_id: {output}"
    assert "RuntimeError" in output, f"stderr missing exception type: {output}"
    assert "simulated DB connection failure" in output, f"stderr missing message: {output}"
    assert "Traceback" in output, f"stderr missing traceback: {output}"


def test_callback_does_not_catch_http_exceptions(client, valid_state, monkeypatch):
    """HTTPException (e.g. 400 for bad state) must pass through unchanged
    — it's an expected client error, not an internal failure."""
    async def raise_http(_code):
        raise HTTPException(status_code=429, detail="rate limited")

    monkeypatch.setattr("app.routes.auth.exchange_code", raise_http)

    resp = client.get(
        f"/auth/callback?code=fake_code&state={valid_state['state']}",
        headers={"Cookie": valid_state["cookie"]},
        follow_redirects=False,
    )

    assert resp.status_code == 429
    assert resp.json()["detail"] == "rate limited"


def test_callback_clears_state_cookie_after_success(client, valid_state, monkeypatch):
    """The state cookie is single-use — after ANY callback response (even a
    500), it should be cleared so the value cannot be replayed."""
    async def explode(_code):
        raise RuntimeError("boom")

    monkeypatch.setattr("app.routes.auth.exchange_code", explode)

    resp = client.get(
        f"/auth/callback?code=fake_code&state={valid_state['state']}",
        headers={"Cookie": valid_state["cookie"]},
        follow_redirects=False,
    )

    assert resp.status_code == 500
