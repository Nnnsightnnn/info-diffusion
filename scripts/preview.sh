#!/usr/bin/env bash
# Preview the static site locally — mirrors what .github/workflows/pages.yml
# does on deploy: composes .brand/ and assets/ into docs/, then serves.
#
# Usage:
#   bash scripts/preview.sh           # serves on port 8000
#   bash scripts/preview.sh 8765      # serves on a custom port
#
# The composed docs/.brand and docs/assets are gitignored so they won't be
# committed — they exist only for local dev parity with the deployed site.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${1:-8000}"

cd "$REPO_ROOT"

rm -rf docs/.brand docs/assets
cp -r .brand docs/.brand
cp -r assets docs/assets

echo "Site composed in docs/. Serving on http://localhost:${PORT}/ — Ctrl+C to stop."
cd docs && exec python3 -m http.server "$PORT"
