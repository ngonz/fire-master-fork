#!/bin/bash
# OPTIONAL native/contributor setup — NOT the documented user path.
# The cross-platform equivalent (no bash/openssl/sed, works on Windows) is:
#   docker compose run --rm --no-deps setup
# This bash version generates backend/.env for the native ./scripts/start.sh path.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/backend/.env"
ENV_EXAMPLE="$PROJECT_ROOT/.env.example"

echo "=== FIREMaster Setup ==="
echo ""

if [ ! -f "$ENV_EXAMPLE" ]; then
    echo "ERROR: .env.example not found at $ENV_EXAMPLE"
    exit 1
fi

if [ -f "$ENV_FILE" ]; then
    echo "WARNING: $ENV_FILE already exists."
    read -p "Overwrite? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted. Existing .env unchanged."
        exit 0
    fi
fi

echo "Generating JWT secret key..."
JWT_KEY=$(openssl rand -hex 32)

echo ""
read -s -p "Choose an admin password: " PASSWORD
echo ""
read -s -p "Confirm password: " PASSWORD2
echo ""

if [ "$PASSWORD" != "$PASSWORD2" ]; then
    echo "ERROR: Passwords don't match."
    exit 1
fi

if [ -z "$PASSWORD" ]; then
    echo "ERROR: Password cannot be empty."
    exit 1
fi

echo "Generating bcrypt hash..."
HASH=$(cd "$PROJECT_ROOT/backend" && uv run python -c "from app.core.auth import hash_password; print(hash_password('$PASSWORD'))")

cp "$ENV_EXAMPLE" "$ENV_FILE"

case "$(uname)" in
    Darwin) SED_FLAG=(-i '') ;;
    *)      SED_FLAG=(-i) ;;
esac

sed "${SED_FLAG[@]}" "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$JWT_KEY|" "$ENV_FILE"
sed "${SED_FLAG[@]}" "s|^AUTH_PASSWORD_HASH=.*|AUTH_PASSWORD_HASH=$HASH|" "$ENV_FILE"

echo ""
echo "=== Setup complete ==="
echo "  File:       $ENV_FILE"
echo "  Username:   admin"
echo "  JWT key:    (generated, 64 hex chars)"
echo "  Password:   (hashed with bcrypt)"
echo ""
echo "Next steps:"
echo "  1. docker compose up -d postgres redis"
echo "  2. cd backend && uv run alembic upgrade head"
echo "  3. ./scripts/start.sh"
