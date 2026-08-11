# Deploying the backend (Render)

## Start command

Set Render's **Start Command** to:

```
./start.sh
```

`start.sh` prints a redacted summary of `DATABASE_URL`, runs `alembic upgrade head`,
and then starts uvicorn **whether or not the migration succeeded**.

The previous command was:

```
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

The `&&` is what turned a database problem into a deploy that failed silently: no
port was bound, Render kept the previous instance alive, and the service went on
answering requests with stale code while looking perfectly healthy. Diagnosing it
required the build log, which is the one place nobody looks when the site is up.

### Optional, and better: use a Pre-Deploy Command

If you want a bad migration to stop the release outright, put

- **Pre-Deploy Command:** `alembic upgrade head`
- **Start Command:** `./start.sh`

A failed pre-deploy aborts the deploy, names the error in **Events**, and leaves
the previous instance serving. That is the protection `&&` was reaching for,
without the stale-code ambiguity. `start.sh` will simply find the migrations
already applied and move on.

## Checking a deploy from the terminal

```bash
curl -s https://inventory-saas-4.onrender.com/api/health | python -m json.tool
```

```json
{
  "status": "degraded",
  "database": { "status": "error", "error": "OperationalError" },
  "database_url": { "warnings": ["unencoded_at_in_password"], "password_set": true, "parsed": true },
  "migrations": { "status": "failed" }
}
```

`status` is `ok` or `degraded`. The endpoint **always returns 200**, deliberately:
a non-200 would let Render's health check fail the deploy and roll back to the
old instance, which is exactly the failure this is meant to expose.

It is unauthenticated, so it reports warning **codes** rather than values — no
host, account name, or driver error text. For the full picture either read the
container log (`start.sh` prints everything on boot) or set
`DEBUG_ENDPOINT_ENABLED=true` temporarily, which adds `detail` fields to both
`database` and `migrations`. Unset it afterwards.

### Warning codes

| Code | Meaning |
| --- | --- |
| `unencoded_at_in_password` | The password contains a raw `@`. SQLAlchemy splits the URL on the **first** `@`, so the rest of the password is parsed as part of the hostname and DNS fails. Percent-encode it as `%40`. |
| `psql_command_pasted` | The value starts with `psql ` — Supabase's Connect panel copies a whole shell command. Paste only the URL inside the quotes. |
| `postgres_scheme_alias` | Scheme is `postgres://`; SQLAlchemy 2 dropped that alias. Use `postgresql://`. |
| `localhost_default` | `DATABASE_URL` is not set on the host, so `config.py`'s localhost default is in use — the app is trying to reach Postgres inside its own container. |
| `no_password` | No password in the URL. |
| `unparseable` | SQLAlchemy could not parse the value at all. This crashes at *import*, so uvicorn never binds and Render reports "no open ports detected" — a symptom, never the cause. |

## Connection string shape (Supabase)

Render has no outbound IPv6 and Supabase's **direct** host publishes no A record,
so the direct connection is unreachable. Use the **Session Pooler**:

```
postgresql://postgres.<project-ref>:<password>@aws-0-ap-southeast-2.pooler.supabase.com:5432/postgres
```

Session mode is port `5432`; transaction mode is `6543`. The username is
`postgres.<project-ref>`, not `postgres`. Percent-encode `@ : / ? #` in the
password — `!` needs no encoding.

## Required environment variables

`DATABASE_URL`, `JWT_SECRET`, `TOKEN_ENCRYPTION_KEY`, `SQUARE_APP_ID`,
`SQUARE_APP_SECRET`, `SQUARE_SANDBOX`, `SQUARE_WEBHOOK_SIGNATURE_KEY`,
`BACKEND_URL`, `FRONTEND_URL`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`,
`STRIPE_PRICE_ID`.

Environment variable names are case-sensitive on Linux: a lowercase
`square_app_secret` row is dead weight and does not satisfy `SQUARE_APP_SECRET`.

Verify what is actually set **on Render** rather than trusting local `.env` —
the longest-running bug in this project was a `DATABASE_URL` that had never been
set on the host at all.
