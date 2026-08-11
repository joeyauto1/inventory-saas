"""OAuth CSRF state parameter — the security boundary on the Square connect flow.

Without a state parameter, /auth/callback will bind whatever Square account an
attacker authorises to whoever opens the crafted callback URL. These tests pin
the three behaviours that close that hole.
"""

import re

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.routes.auth import OAUTH_STATE_COOKIE


@pytest.fixture
def client():
    """TestClient with the DB dependency stubbed out.

    The state check must reject before anything touches the database, so a
    null session is sufficient — and if a rejection path ever starts hitting
    the DB, these tests will fail loudly rather than silently connecting.
    """
    app.dependency_overrides[get_db] = lambda: None
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _state_from_login(response):
    """Pull the state value out of the login redirect's Location header."""
    match = re.search(r"[?&]state=([^&]+)", response.headers["location"])
    assert match, f"no state in redirect URL: {response.headers['location']}"
    return match.group(1)


def test_login_includes_state_in_authorize_url(client):
    resp = client.get("/auth/login", follow_redirects=False)

    assert resp.status_code == 307
    state = _state_from_login(resp)
    assert len(state) >= 32, "state must be long enough to be unguessable"


def test_login_sets_state_cookie_matching_the_url(client):
    resp = client.get("/auth/login", follow_redirects=False)

    url_state = _state_from_login(resp)
    set_cookie = resp.headers["set-cookie"]

    assert OAUTH_STATE_COOKIE in set_cookie
    assert url_state in set_cookie, "cookie state must match the URL state"
    assert "HttpOnly" in set_cookie, "state cookie must not be readable by JS"


def test_login_generates_a_fresh_state_each_time(client):
    first = _state_from_login(client.get("/auth/login", follow_redirects=False))
    second = _state_from_login(client.get("/auth/login", follow_redirects=False))

    assert first != second, "reusing state across logins defeats the protection"


def test_callback_rejects_missing_state(client):
    resp = client.get("/auth/callback?code=fake_auth_code", follow_redirects=False)

    assert resp.status_code == 400


def test_callback_rejects_mismatched_state(client):
    resp = client.get(
        "/auth/callback?code=fake_auth_code&state=attacker_supplied",
        headers={"Cookie": f"{OAUTH_STATE_COOKIE}=the_real_state"},
        follow_redirects=False,
    )

    assert resp.status_code == 400


def test_callback_rejects_state_param_with_no_cookie(client):
    """A crafted link carries a state param but the victim has no matching cookie."""
    resp = client.get(
        "/auth/callback?code=fake_auth_code&state=attacker_supplied",
        follow_redirects=False,
    )

    assert resp.status_code == 400
