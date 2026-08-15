"""Square webhook must fail closed, and accept a signature from outside the implementation.

F6 (round 2): the handler's signature algorithm did not match Square's — it read
the wrong header (`x-square-signature`, the legacy SHA-1 header), signed the body
only instead of `notification_url + body`, and hex-encoded instead of base64. The
round-2 test computed its expected signature with the handler's own algorithm, so
it proved self-consistency and could not catch any of that.

This test is now the oracle:

- The fail-closed cases (missing key, missing notification URL, missing header,
  wrong signature) must all 401.
- The positive case computes its expected signature from Square's DOCUMENTED
  algorithm, reproduced independently with stdlib (hmac + hashlib + base64). The
  handler delegates to Square's SDK helper; this test never imports it, so the
  two cannot silently agree on a wrong algorithm.
"""

import base64
import hashlib
import hmac

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app

SIGNATURE_HEADER = "x-square-hmacsha256-signature"
NOTIFICATION_URL = "https://inventory-saas-4.onrender.com/webhooks/square"
KEY = "test-signature-key"


def _square_signature(key: str, notification_url: str, body: str) -> str:
    """Square's documented signature algorithm, reproduced independently.

    This is the oracle. It deliberately does NOT call the SDK helper the handler
    uses: payload = notification_url + body, HMAC-SHA256, base64. If the handler
    (or the SDK) ever deviates from this, the positive test fails.
    """
    payload = (notification_url + body).encode("utf-8")
    digest = hmac.new(key.encode("utf-8"), payload, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def _client(monkeypatch):
    monkeypatch.setattr(settings, "SQUARE_WEBHOOK_SIGNATURE_KEY", "")
    monkeypatch.setattr(settings, "SQUARE_NOTIFICATION_URL", "")
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
    return TestClient(app)


def test_missing_key_is_refused(monkeypatch):
    """A missing signature key must refuse, never skip verification.

    This is the exact bug from review F2 — reverting to ``if <key>:`` makes this
    test fail, because the request would be waved through with a 200.
    """
    client = _client(monkeypatch)
    try:
        resp = client.post("/webhooks/square", json={"type": "inventory.count.updated"})
        assert resp.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_missing_notification_url_is_refused(monkeypatch):
    """The notification URL is part of the signed payload; without it the request
    cannot be verified and must be refused, not waved through."""
    client = _client(monkeypatch)
    try:
        monkeypatch.setattr(settings, "SQUARE_WEBHOOK_SIGNATURE_KEY", KEY)
        resp = client.post("/webhooks/square", json={"type": "inventory.count.updated"})
        assert resp.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_missing_signature_is_refused(monkeypatch):
    client = _client(monkeypatch)
    try:
        monkeypatch.setattr(settings, "SQUARE_WEBHOOK_SIGNATURE_KEY", KEY)
        monkeypatch.setattr(settings, "SQUARE_NOTIFICATION_URL", NOTIFICATION_URL)
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
        monkeypatch.setattr(settings, "SQUARE_WEBHOOK_SIGNATURE_KEY", KEY)
        monkeypatch.setattr(settings, "SQUARE_NOTIFICATION_URL", NOTIFICATION_URL)
        body = b'{"type": "inventory.count.updated"}'
        resp = client.post(
            "/webhooks/square",
            content=body,
            headers={
                "Content-Type": "application/json",
                SIGNATURE_HEADER: "dG90YWxseS1pbnZhbGlk",
            },
        )
        assert resp.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_correct_signature_is_accepted(monkeypatch):
    """The 'still works' half, with an oracle outside the implementation.

    The expected signature is produced by ``_square_signature`` (stdlib), never
    by the SDK helper the handler calls — so the test cannot silently agree with
    a wrong algorithm in the code under test.
    """
    client = _client(monkeypatch)
    try:
        monkeypatch.setattr(settings, "SQUARE_WEBHOOK_SIGNATURE_KEY", KEY)
        monkeypatch.setattr(settings, "SQUARE_NOTIFICATION_URL", NOTIFICATION_URL)
        body = '{"type": "inventory.count.updated"}'
        signature = _square_signature(KEY, NOTIFICATION_URL, body)
        resp = client.post(
            "/webhooks/square",
            content=body.encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                SIGNATURE_HEADER: signature,
            },
        )
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
    finally:
        app.dependency_overrides.clear()
