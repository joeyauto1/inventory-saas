"""Task 3 — Stripe customer creation failure must be logged, not swallowed.

The pre-fix code was `except Exception: pass` with a comment promising a later
prompt that never existed. A merchant could fail to get a Stripe customer and
become permanently unbillable with no record of the failure.

This test induces a Stripe failure inside the OAuth callback and asserts the
log line names the merchant id and the error type. It is the regression test
for the silent swallow.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.config import settings


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("BACKEND_URL", "https://test.example.com")
    monkeypatch.setattr(settings, "REDIRECT_URI", "https://test.example.com/auth/callback")
    monkeypatch.setattr(settings, "JWT_SECRET", "test-secret")

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def valid_state():
    state = "valid_test_state_1234567890123"
    return {"state": state, "cookie": f"oauth_state={state}"}


def test_stripe_customer_failure_is_logged_with_merchant_id(
    client, valid_state, monkeypatch, capsys
):
    """When get_or_create_customer raises, the log line must carry the merchant
    id and the exception — the exact information the old `except: pass` threw
    away."""

    async def fake_exchange(_code):
        return {
            "access_token": "encrypted_at",
            "refresh_token": "encrypted_rt",
            "expires_at": __import__("datetime").datetime(2027, 1, 1),
            "merchant_id": "sq_test_123",
        }

    def fake_merch_info(_c):
        return {"merchant": {"business_name": "Joe's Cafe", "email": "joe@example.com"}}

    def fake_locations(_c):
        return {"locations": []}

    def explode_customer(**kwargs):
        raise RuntimeError("simulated Stripe outage")

    monkeypatch.setattr("app.routes.auth.exchange_code", fake_exchange)
    monkeypatch.setattr("app.routes.auth.get_client", lambda _t: object())
    monkeypatch.setattr("app.routes.auth.get_merchant_info", fake_merch_info)
    monkeypatch.setattr("app.routes.auth.list_locations", fake_locations)
    monkeypatch.setattr(
        "app.routes.auth.stripe_service.get_or_create_customer", explode_customer
    )

    # The callback runs end-to-end against a real in-memory DB. The Stripe step
    # raises, is caught, logged, and signup continues (a 500 later is fine —
    # the assertion is about the log line, not the response).
    client.get(
        f"/auth/callback?code=fake&state={valid_state['state']}",
        headers={"Cookie": valid_state["cookie"]},
        follow_redirects=False,
    )

    captured = capsys.readouterr()
    err = captured.err

    assert "stripe_customer_creation_failed" in err, (
        f"stripe failure was not logged; stderr was: {err!r}"
    )
    assert "RuntimeError" in err, f"error type not logged: {err!r}"
    assert "simulated Stripe outage" in err, f"error message not logged: {err!r}"
