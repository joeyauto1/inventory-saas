"""Square webhook must fail closed.

Round-1 review finding F2: the handler skipped signature verification entirely
when ``SQUARE_WEBHOOK_SIGNATURE_KEY`` was unset — a missing key waved every
request through unverified. These tests pin the fail-closed behaviour: a missing
key, a missing signature header, and a wrong signature must all be refused, and
a correctly-signed event must still be accepted.

The ``test_missing_key_is_refused`` case is the regression guard: under the old
``if settings.SQUARE_WEBHOOK_SIGNATURE_KEY:`` shape, an unset key skipped
verification and returned 200, so this test fails if the guard is ever reverted.
"""

import hashlib
import hmac

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app


def _sign(key: str, body: bytes) -> str:
    return hmac.new(key.encode(), body, hashlib.sha256).hexdigest()


def _client(monkeypatch):
    monkeypatch.setattr(settings, "SQUARE_WEBHOOK_SIGNATURE_KEY", "")
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
    client = TestClient(app)
    return client


def test_missing_key_is_refused(monkeypatch):
    """A missing signature key must refuse, never skip verification.

    This is the exact bug from review F2 — reverting to ``if <key>:`` makes this
    test fail, because the request would be waved through with a 200.
    """
    client = _client(monkeypatch)
    try:
        resp = client.post(
            "/webhooks/square",
            json={"type": "inventory.count.updated"},
        )
        assert resp.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_missing_signature_is_refused(monkeypatch):
    client = _client(monkeypatch)
    try:
        monkeypatch.setattr(settings, "SQUARE_WEBHOOK_SIGNATURE_KEY", "test-key")
        resp = client.post(
            "/webhooks/square",
            content=b'{"type": "inventory.count.updated"}',
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_wrong_signature_is_refused(monkeypatch):
    client = _client(monkeypatch)
    try:
        monkeypatch.setattr(settings, "SQUARE_WEBHOOK_SIGNATURE_KEY", "test-key")
        body = b'{"type": "inventory.count.updated"}'
        resp = client.post(
            "/webhooks/square",
            content=body,
            headers={
                "Content-Type": "application/json",
                "x-square-signature": "totally-invalid",
            },
        )
        assert resp.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_correct_signature_is_accepted(monkeypatch):
    """The 'still works' half: a correctly-signed event must still be processed.

    Fail-closed must not mean fail-always — a valid Square signature returns 200.
    """
    client = _client(monkeypatch)
    try:
        key = "test-key"
        monkeypatch.setattr(settings, "SQUARE_WEBHOOK_SIGNATURE_KEY", key)
        body = b'{"type": "inventory.count.updated"}'
        resp = client.post(
            "/webhooks/square",
            content=body,
            headers={
                "Content-Type": "application/json",
                "x-square-signature": _sign(key, body),
            },
        )
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
    finally:
        app.dependency_overrides.clear()
