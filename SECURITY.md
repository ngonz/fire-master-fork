# Security Policy

FIREMaster is self-hosted software that holds financial credentials (a Monarch Money session)
and financial data. Security reports are taken seriously and read by the author personally.

## Reporting a vulnerability

**Do not open a public issue for security problems.**

Report privately via **GitHub's private vulnerability reporting** (Security tab → "Report a
vulnerability" on this repo), or email **gdborshukov@gmail.com** with `[FIREMaster security]`
in the subject.

Include what you can: affected component, reproduction steps, and impact as you understand
it. You'll get a human reply — typically within a few days, no SLA — and credit in the fix
commit if you want it.

## Scope notes for researchers

- The threat model assumes a **single-user deployment on localhost or a private network**.
  The app has one admin user and is not designed to be exposed to the public internet;
  reports assuming a hardened multi-tenant deployment are out of scope.
- **https://demo.firemaster.io is a shared sandbox with synthetic data** that resets every
  two hours. It is in scope for responsible testing (please don't DoS it), and nothing on
  it is secret — including the demo password.
- Secrets live in `backend/.env` and the repo-root `.env` (both gitignored, both written
  `chmod 0600`) and are generated per-install by `app.setup`. If you find a way for any real
  secret or PII to reach the repo, the image, or the logs, that is exactly the class of bug
  to report.

## Deployment hardening defaults

These are the defaults this fork ships. They matter because Postgres and Redis sit *behind*
the login screen — reaching either one directly bypasses JWT authentication entirely and
yields the full transaction history.

- **All published ports bind to `127.0.0.1`**, not `0.0.0.0`. The `BIND_HOST` variable is kept
  separate from the `*_HOST_PORT` variables on purpose, so remapping a port cannot silently
  drop the loopback restriction. Setting `BIND_HOST=0.0.0.0` exposes Postgres, Redis, the API
  and the UI to the whole network; do that only behind real authentication.
- **Postgres and Redis passwords are randomly generated** by `app.setup` (`secrets.token_urlsafe`)
  and written to the root `.env`. If those variables are absent, the compose files fall back to
  an obvious `CHANGEME-run-app-setup` placeholder so an unconfigured stack fails loudly rather
  than running on a guessable credential.
- **Redis requires a password** (`requirepass`). Without it, anything that can reach the port can
  read cached data and enqueue arbitrary Celery jobs.
- **Images default to locally built tags**, so `docker compose up --build` runs the code in the
  checkout. Pulling a mutable `:latest` from a registry would silently discard local fixes.
- **The Monarch session file is created `0600` before any secret is written to it.** That file is
  a bearer token for the entire Monarch account, so it is never allowed to exist world-readable,
  even briefly. The login script also reads the password via `getpass` rather than echoing it.
- **The Monarch client is pinned to an exact version**, not a range. It is an unofficial
  community package that receives the plaintext password and MFA code, so upgrades should be a
  reviewed decision rather than something a fresh dependency resolution picks up.

Known caveat: Postgres only applies `POSTGRES_PASSWORD` when initialising an empty data
directory. Rotating it against an existing volume requires `docker compose down -v` (destructive)
or an in-place `ALTER USER`.

## Supported versions

The latest commit on `main` (and the GHCR images built from it) is the only supported
version.
