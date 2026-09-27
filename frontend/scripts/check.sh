#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

pnpm exec tsc -b
pnpm exec eslint .
pnpm exec prettier --check .
pnpm exec steiger ./src
pnpm exec vitest run --passWithNoTests

tmp_dir="$(mktemp -d)"
trap 'rm -rf "${tmp_dir}"' EXIT
pnpm exec openapi-typescript ../backend/openapi.json -o "${tmp_dir}/schema.d.ts" > /dev/null
if ! diff -q --strip-trailing-cr "${tmp_dir}/schema.d.ts" src/shared/api/schema.d.ts > /dev/null; then
    echo "src/shared/api/schema.d.ts is outdated: run pnpm gen:api"
    exit 1
fi

pnpm build

echo "all checks passed"
