#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

# Types follow the backend contract on their own: a newer openapi.json never fails the check.
node scripts/gen-api.mjs
pnpm exec tsc -b
pnpm exec eslint .
pnpm exec prettier --check .
pnpm exec steiger ./src
pnpm exec vitest run --passWithNoTests

pnpm build

echo "all checks passed"
