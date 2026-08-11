"""Startup diagnostics for the database connection.

Every hour lost on this deploy traced back to an invisible error: the app
failed before it could tell anyone why. These helpers make the two failure
modes we actually hit visible from a plain `curl`, with no dashboard access:

1. A malformed DATABASE_URL. SQLAlchemy splits the URL on the *first* '@',
   so an unencoded '@' inside the password silently moves the rest of the
   password into the hostname:

       postgresql://user:pa@ss@real-host:5432/db
           -> host = "ss@real-host"   (never resolves)
           -> password = "pa"

   The resulting error is a DNS/network failure that reads like an outage
   rather than a typo. describe_database_url() reports the host SQLAlchemy
   will actually dial, so the mangling is obvious on sight.

2. Migrations that could not run. See start.sh — a failed migration no
   longer prevents the process from binding a port, so the reason is
   reachable at /api/health instead of only in a failed build log.
"""

import os
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine.url import make_url

# start.sh writes this marker when `alembic upgrade head` exits non-zero, so the
# running app can report the failure. /tmp is writable on Render and wiped
# between deploys, which is exactly the lifetime we want.
MIGRATION_FAILURE_MARKER = os.environ.get(
    "MIGRATION_FAILURE_MARKER", "/tmp/inventory-saas-migrations-failed"
)


# Each warning carries a stable code alongside its message. /api/health is
# unauthenticated, so it publishes only the codes — enough to identify the
# problem and look up the fix, without disclosing the host, the account name,
# or how far a guess got. The full messages go to the container log, which is
# already privileged.
WARNING_MESSAGES = {
    "empty": "DATABASE_URL is empty.",
    "psql_command_pasted": (
        "DATABASE_URL starts with 'psql ' — the Supabase Connect panel copies a "
        "whole shell command. Paste only the URL inside the quotes."
    ),
    "postgres_scheme_alias": (
        "Scheme is 'postgres://' — SQLAlchemy 2 dropped that alias. "
        "Use 'postgresql://'."
    ),
    "unparseable": "DATABASE_URL could not be parsed.",
    "unencoded_at_in_password": (
        "The host contains '@', so the password almost certainly has an "
        "unencoded one. SQLAlchemy splits on the FIRST '@' and the rest of the "
        "password becomes part of the hostname. Percent-encode it as '%40'."
    ),
    "no_password": "DATABASE_URL has no password.",
    "localhost_default": (
        "Host is localhost — DATABASE_URL is probably unset on this host and "
        "config.py's default is in use."
    ),
}


def describe_database_url(url: str) -> dict[str, Any]:
    """Summarise a database URL for logging. Never includes the password.

    Returns the components as SQLAlchemy itself parses them — the point is to
    show what the app will really connect to, not what the URL looks like.
    Warnings are returned as codes; look them up in WARNING_MESSAGES.
    """
    info: dict[str, Any] = {"warnings": []}

    if not url:
        info["warnings"].append("empty")
        return info

    if url.startswith("psql "):
        info["warnings"].append("psql_command_pasted")
    if url.startswith("postgres://"):
        info["warnings"].append("postgres_scheme_alias")

    try:
        parsed = make_url(url)
    except Exception as exc:  # malformed beyond parsing
        info["warnings"].append("unparseable")
        info["parse_error"] = f"{type(exc).__name__}: {exc}"
        return info

    info.update(
        {
            "driver": parsed.drivername,
            "username": parsed.username,
            "host": parsed.host,
            "port": parsed.port,
            "database": parsed.database,
            "password_set": bool(parsed.password),
        }
    )

    # The '@' trap. A correctly-encoded password leaves exactly one '@' in the
    # URL; a raw one leaves two or more and steals part of the hostname.
    if parsed.host and "@" in parsed.host:
        info["warnings"].append("unencoded_at_in_password")
    if not parsed.password:
        info["warnings"].append("no_password")
    if parsed.host in ("localhost", "127.0.0.1"):
        info["warnings"].append("localhost_default")

    return info


def public_database_report(url: str) -> dict[str, Any]:
    """The subset of describe_database_url() safe to serve unauthenticated.

    Warning codes and booleans only — no host, account name, or error text.
    Set DEBUG_ENDPOINT_ENABLED to get the full picture from /api/debug/env,
    or read the container log, where start.sh prints everything.
    """
    info = describe_database_url(url)
    return {
        "warnings": info["warnings"],
        "password_set": info.get("password_set", False),
        "parsed": "unparseable" not in info["warnings"],
    }


def format_database_summary(url: str) -> str:
    """One-line-per-field summary for the container start log.

    Unlike public_database_report() this includes the host and account name —
    the log is privileged, and seeing the host is what makes a mangled URL
    obvious at a glance.
    """
    info = describe_database_url(url)
    warnings = info.pop("warnings", [])
    lines = [f"  {key} = {value}" for key, value in info.items()]
    lines += [f"  WARNING [{code}]: {WARNING_MESSAGES[code]}" for code in warnings]
    return "\n".join(lines) if lines else "  (no information)"


def migrations_failed() -> bool:
    """True when start.sh recorded a failed `alembic upgrade head`."""
    return os.path.exists(MIGRATION_FAILURE_MARKER)


def migration_failure_detail() -> str:
    """The tail of the failed migration output, if start.sh recorded any."""
    try:
        with open(MIGRATION_FAILURE_MARKER) as handle:
            return handle.read().strip()
    except OSError:
        return ""


def check_database(engine, verbose: bool = False) -> dict[str, Any]:
    """Probe the database with a trivial query. Never raises.

    Without verbose, only the exception class is reported: driver messages
    quote the host ("could not translate host name ...") and this ends up on
    an unauthenticated endpoint.
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as exc:
        report = {"status": "error", "error": type(exc).__name__}
        if verbose:
            report["detail"] = str(exc)
        return report
