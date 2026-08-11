"""Tests for the startup/health diagnostics.

These encode the two failure modes that cost this deploy a day: a DATABASE_URL
mangled by an unencoded '@', and migrations failing in a way nothing surfaced.
"""

import pytest

from app.diagnostics import (
    WARNING_MESSAGES,
    describe_database_url,
    format_database_summary,
    migration_failure_detail,
    migrations_failed,
    public_database_report,
)

GOOD_URL = (
    "postgresql://postgres.abc:s3cret@aws-0-ap-southeast-2.pooler.supabase.com"
    ":5432/postgres"
)


def warnings_for(url):
    return describe_database_url(url)["warnings"]


def test_good_url_parses_with_no_warnings():
    info = describe_database_url(GOOD_URL)
    assert info["warnings"] == []
    assert info["host"] == "aws-0-ap-southeast-2.pooler.supabase.com"
    assert info["username"] == "postgres.abc"
    assert info["port"] == 5432
    assert info["database"] == "postgres"
    assert info["password_set"] is True


def test_password_is_never_reported():
    """The summary goes to logs and an unauthenticated endpoint."""
    info = describe_database_url(GOOD_URL)
    assert "s3cret" not in repr(info)
    assert "s3cret" not in format_database_summary(GOOD_URL)


def test_unencoded_at_in_password_is_flagged():
    """SQLAlchemy splits on the FIRST '@', so the host swallows the password."""
    url = (
        "postgresql://postgres.abc:pa@ss@aws-0-ap-southeast-2.pooler.supabase.com"
        ":5432/postgres"
    )
    info = describe_database_url(url)
    # The mangling itself — this is what makes the deploy fail on DNS.
    assert info["host"] == "ss@aws-0-ap-southeast-2.pooler.supabase.com"
    assert info["warnings"] == ["unencoded_at_in_password"]


def test_percent_encoded_at_is_accepted():
    url = (
        "postgresql://postgres.abc:pa%40ss@aws-0-ap-southeast-2.pooler.supabase.com"
        ":5432/postgres"
    )
    info = describe_database_url(url)
    assert info["host"] == "aws-0-ap-southeast-2.pooler.supabase.com"
    assert info["warnings"] == []


def test_psql_command_paste_is_flagged():
    """Supabase's Connect panel copies the whole `psql "..."` line."""
    assert "psql_command_pasted" in warnings_for(f'psql "{GOOD_URL}"')


def test_postgres_scheme_alias_is_flagged():
    """SQLAlchemy 2 dropped the postgres:// alias."""
    url = GOOD_URL.replace("postgresql://", "postgres://")
    assert "postgres_scheme_alias" in warnings_for(url)


def test_localhost_default_is_flagged():
    """config.py's fallback means DATABASE_URL was never set on the host."""
    assert "localhost_default" in warnings_for("postgresql://localhost:5432/inventory")


def test_empty_url_is_flagged():
    assert warnings_for("") == ["empty"]


def test_missing_password_is_flagged():
    url = "postgresql://postgres.abc@aws-0-ap-southeast-2.pooler.supabase.com/postgres"
    assert "no_password" in warnings_for(url)


def test_every_warning_code_has_a_message():
    """format_database_summary() looks codes up directly and would KeyError."""
    codes = set()
    for url in (
        "",
        f'psql "{GOOD_URL}"',
        GOOD_URL.replace("postgresql://", "postgres://"),
        "postgresql://postgres.abc:pa@ss@host:5432/postgres",
        "postgresql://postgres.abc@host/postgres",
        "postgresql://localhost:5432/inventory",
        "not a url at all",
    ):
        codes.update(warnings_for(url))
    assert codes, "expected the sample URLs to trigger warnings"
    assert codes <= set(WARNING_MESSAGES)


def test_public_report_withholds_host_and_account():
    """/api/health is unauthenticated — codes and booleans only."""
    report = public_database_report(GOOD_URL)
    assert report == {"warnings": [], "password_set": True, "parsed": True}


def test_public_report_still_identifies_the_at_bug():
    """Withholding values must not cost the diagnosis."""
    url = "postgresql://postgres.abc:pa@ss@aws-0-ap-southeast-2.pooler.supabase.com/x"
    report = public_database_report(url)
    assert report["warnings"] == ["unencoded_at_in_password"]
    assert "aws-0" not in repr(report)


def test_unparseable_url_reports_rather_than_raises():
    report = public_database_report("psql postgres@@@:::")
    assert report["parsed"] is False


@pytest.fixture
def marker(tmp_path, monkeypatch):
    path = tmp_path / "migrations-failed"
    monkeypatch.setattr("app.diagnostics.MIGRATION_FAILURE_MARKER", str(path))
    return path


def test_no_marker_means_migrations_ok(marker):
    assert migrations_failed() is False
    assert migration_failure_detail() == ""


def test_marker_surfaces_the_failure_text(marker):
    marker.write_text("sqlalchemy.exc.OperationalError: could not translate host\n")
    assert migrations_failed() is True
    assert "could not translate host" in migration_failure_detail()
