"""Authorization tests — the auth hole is closed.

These pin the two behaviours the brief demands:

1. Unauthenticated requests to every tenant-scoped router return 401.
2. A valid session for merchant A cannot read merchant B's data — the route
   returns 404 (not 403), so existence is not confirmed.

The cross-merchant test below would FAIL against the pre-fix code, where every
route accepted a client-supplied ``merchant_id`` query param with no session at
all. There is no path, query, or body parameter left that carries merchant_id.
"""

import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.merchant import Merchant
from app.models.recipe import Recipe
from app.config import settings
from app.routes.auth import _create_jwt


@pytest.fixture
def db_engine():
    """In-memory SQLite shared across the TestClient's threads."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def client(db_engine, monkeypatch):
    monkeypatch.setattr(settings, "JWT_SECRET", "test-secret")

    TestingSession = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)

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


def _make_merchant(db_engine, merchant_id: int, square_id: str) -> Merchant:
    Session = sessionmaker(bind=db_engine)
    db = Session()
    now = datetime.now(timezone.utc)
    merchant = Merchant(
        id=merchant_id,
        square_merchant_id=square_id,
        access_token="encrypted-a",
        refresh_token="encrypted-r",
        token_expires_at=now + timedelta(days=30),
        business_name=f"Merchant {merchant_id}",
        email=f"m{merchant_id}@example.com",
        trial_ends_at=now + timedelta(days=14),
        subscription_status="trialing",
    )
    db.add(merchant)
    db.commit()
    db.close()
    return merchant


def _cookie_for(merchant_id: int) -> dict:
    token = _create_jwt(merchant_id)
    return {"session_token": token}


# --- 401: no credentials ------------------------------------------------------


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/api/inventory"),
        ("GET", "/api/inventory/V1/history"),
        ("POST", "/api/inventory/sync"),
        ("GET", "/api/billing/portal"),
        ("GET", "/api/billing/status"),
        ("POST", "/api/billing/checkout"),
        ("GET", "/api/waste"),
        ("POST", "/api/waste"),
        ("GET", "/api/waste/summary"),
        ("DELETE", "/api/waste/1"),
        ("GET", "/api/recipes"),
        ("POST", "/api/recipes"),
        ("GET", "/api/recipes/1"),
        ("POST", "/api/recipes/1/ingredients"),
        ("DELETE", "/api/recipes/1/ingredients/1"),
        ("GET", "/api/reports/waste"),
        ("GET", "/api/reports/cogs"),
        ("GET", "/api/reports/inventory-valuation"),
    ],
)
def test_unauthenticated_requests_return_401(client, method, path):
    """Every tenant-scoped route must reject a request with no session cookie.

    POSTs without a body still reach the auth dependency first, so they must
    return 401 (not 422) — the auth check runs before body validation.
    """
    resp = client.request(method, path)
    assert resp.status_code == 401, f"{method} {path} returned {resp.status_code}"


def test_invalid_session_token_returns_401(client):
    resp = client.get("/api/inventory", cookies={"session_token": "not-a-jwt"})
    assert resp.status_code == 401


# --- 404: cross-merchant access ---------------------------------------------


def test_merchant_a_cannot_read_merchant_b_recipe(client, db_engine):
    """A valid session for merchant 1 must get 404 for merchant 2's recipe."""
    _make_merchant(db_engine, 1, "sq-A")
    _make_merchant(db_engine, 2, "sq-B")

    Session = sessionmaker(bind=db_engine)
    db = Session()
    recipe_b = Recipe(merchant_id=2, name="Merchant B's secret recipe", portions=1)
    db.add(recipe_b)
    db.commit()
    db.refresh(recipe_b)
    recipe_b_id = recipe_b.id
    db.close()

    resp = client.get(f"/api/recipes/{recipe_b_id}", cookies=_cookie_for(1))

    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_merchant_a_cannot_delete_merchant_b_waste(client, db_engine):
    """Cross-tenant DELETE must 404, not 403 — existence is not confirmed."""
    _make_merchant(db_engine, 1, "sq-A")
    _make_merchant(db_engine, 2, "sq-B")

    from app.models.waste import WasteEvent

    Session = sessionmaker(bind=db_engine)
    db = Session()
    event = WasteEvent(
        merchant_id=2,
        location_id=1,
        square_catalog_object_id="V1",
        item_name="Beef Mince",
        quantity=1,
        reason="spoilage",
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    event_id = event.id
    db.close()

    resp = client.delete(f"/api/waste/{event_id}", cookies=_cookie_for(1))

    assert resp.status_code == 404


def test_merchant_can_read_own_data(client, db_engine):
    """The same cookie that 404s on merchant B's data works for merchant 1's."""
    _make_merchant(db_engine, 1, "sq-A")

    resp = client.get("/api/recipes", cookies=_cookie_for(1))

    assert resp.status_code == 200
    assert resp.json()["count"] == 0


# --- a validated client-supplied id is still client-supplied -----------------


def test_merchant_id_query_param_is_ignored_not_trusted(client, db_engine):
    """Even if a client sends ?merchant_id=2, the identity comes from the cookie.

    With a cookie for merchant 1, a request asking for merchant 2's data must
    still be scoped to merchant 1 (empty list), not return merchant 2's rows.
    """
    _make_merchant(db_engine, 1, "sq-A")
    _make_merchant(db_engine, 2, "sq-B")

    resp = client.get("/api/recipes?merchant_id=2", cookies=_cookie_for(1))

    assert resp.status_code == 200
    assert resp.json()["count"] == 0
