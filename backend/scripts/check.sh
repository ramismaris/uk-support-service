#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

docker compose up -d --wait db
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
uv run python scripts/dump_openapi.py --check

head_count="$(uv run alembic heads | wc -l | tr -d ' ')"
if [ "${head_count}" -gt 1 ]; then
    echo "More than one Alembic head:"
    uv run alembic heads
    exit 1
fi

echo "all checks passed"
