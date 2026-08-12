"""Square's token-exchange error body must survive into the logs.

A real 401 from `POST /oauth2/token` was diagnosed from Render's logs as only:

    type=HTTPStatusError message=Client error '401 Unauthorized' for url '...'

That is unactionable, because Square returns HTTP 401 for at least three
distinct causes and distinguishes them *only in the response body*:

    wrong client_secret  -> {"message": "Not Authorized",
                             "type": "service.not_authorized"}
    bad/expired code     -> {"errors": [{"category": "AUTHENTICATION_ERROR",
                                         "code": "UNAUTHORIZED",
                                         "detail": "Authorization code not found
                                                    for app sandbox-sq0idb-..."}]}
    mismatched redirect  -> (indistinguishable from the bad-code body)

`httpx.Response.raise_for_status()` puts only the status line in the exception
message, so the one piece of information that identifies the cause was being
discarded at the exact layer that had it. These tests pin the body into the
error path.

The secret must never appear in the log line — the body is Square's, not ours.
"""

import asyncio

import httpx
import pytest

from app.services.square_auth import exchange_code


def _mock_transport(status_code: int, payload):
    """An httpx transport that always answers the token endpoint with `payload`."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=payload)

    return httpx.MockTransport(handler)


@pytest.fixture(autouse=True)
def _configured(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "REDIRECT_URI", "https://test.example.com/auth/callback")
    monkeypatch.setattr(settings, "SQUARE_SANDBOX", True)
    monkeypatch.setattr(settings, "SQUARE_APP_ID", "sandbox-sq0idb-testapp")
    monkeypatch.setattr(settings, "SQUARE_APP_SECRET", "sandbox-sq0csb-supersecret")


@pytest.fixture
def patched_client(monkeypatch):
    """Route exchange_code's httpx.AsyncClient through a mock transport."""

    def _install(status_code, payload):
        real_init = httpx.AsyncClient.__init__

        def init(self, *args, **kwargs):
            kwargs["transport"] = _mock_transport(status_code, payload)
            real_init(self, *args, **kwargs)

        monkeypatch.setattr(httpx.AsyncClient, "__init__", init)

    return _install


def test_wrong_secret_body_is_in_the_error(patched_client):
    """The wrong-secret shape is Square's flattest error — no `errors` array,
    just a bare message. It must still reach the log."""
    patched_client(401, {"message": "Not Authorized", "type": "service.not_authorized"})

    with pytest.raises(Exception) as excinfo:
        asyncio.run(exchange_code("some-code"))

    message = str(excinfo.value)
    assert "service.not_authorized" in message, (
        f"Square's error body was discarded; got only: {message!r}"
    )


def test_bad_code_detail_is_in_the_error(patched_client):
    """The bad-code shape carries its explanation in errors[0].detail."""
    patched_client(
        401,
        {
            "errors": [
                {
                    "category": "AUTHENTICATION_ERROR",
                    "code": "UNAUTHORIZED",
                    "detail": "Authorization code not found for app sandbox-sq0idb-testapp",
                }
            ]
        },
    )

    with pytest.raises(Exception) as excinfo:
        asyncio.run(exchange_code("expired-code"))

    message = str(excinfo.value)
    assert "Authorization code not found" in message, (
        f"Square's error detail was discarded; got only: {message!r}"
    )


def test_status_code_is_preserved_in_the_error(patched_client):
    """Losing the status while gaining the body would be a bad trade."""
    patched_client(401, {"message": "Not Authorized", "type": "service.not_authorized"})

    with pytest.raises(Exception) as excinfo:
        asyncio.run(exchange_code("some-code"))

    assert "401" in str(excinfo.value)


def test_client_secret_is_never_logged(patched_client):
    """The error text is written to logs Render retains. Square's body is safe
    to echo; our credentials are not, and must not be interpolated in."""
    patched_client(401, {"message": "Not Authorized", "type": "service.not_authorized"})

    with pytest.raises(Exception) as excinfo:
        asyncio.run(exchange_code("some-code"))

    assert "supersecret" not in str(excinfo.value)


def test_non_json_body_does_not_mask_the_original_failure(patched_client):
    """Square (or a proxy in front of it) can answer with HTML on a bad day.
    Trying to parse that must not replace the useful error with a JSONDecodeError."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="<html>Bad Gateway</html>")

    real_init = httpx.AsyncClient.__init__

    def init(self, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        real_init(self, *args, **kwargs)

    import unittest.mock

    with unittest.mock.patch.object(httpx.AsyncClient, "__init__", init):
        with pytest.raises(Exception) as excinfo:
            asyncio.run(exchange_code("some-code"))

    message = str(excinfo.value)
    assert "502" in message
    assert "JSONDecodeError" not in type(excinfo.value).__name__
