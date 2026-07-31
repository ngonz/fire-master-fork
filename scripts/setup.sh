#!/bin/bash
# OPTIONAL native/contributor setup — NOT the documented user path.
# The cross-platform equivalent (no bash/uv needed, works on Windows) is:
#   docker compose run --rm --no-deps setup
#
# This is a thin wrapper around `python -m app.setup`, the single source of truth.
# It used to `cp .env.example backend/.env` and sed in only JWT_SECRET_KEY and
# AUTH_PASSWORD_HASH, which left the example file's literal `firemaster:firemaster`
# in DATABASE_URL and the `change-me-must-match-REDIS_PASSWORD` placeholder in
# REDIS_URL — while the very next documented step (`docker compose up -d postgres
# redis`) initialised those services with completely different credentials, so the
# native path could never actually connect. Delegating means there is exactly one
# credential generator and the two paths cannot drift again.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

if ! command -v uv >/dev/null 2>&1; then
    echo "ERROR: uv is required for the native path. Install it from https://docs.astral.sh/uv/"
    echo "       Or use the Docker path instead: docker compose run --rm --no-deps setup"
    exit 1
fi

# app.setup writes backend/.env (application config) AND the repo-root .env that
# docker compose interpolates for postgres/redis, keeping both in sync.
cd "$PROJECT_ROOT/backend"
exec uv run python -m app.setup "$@"
