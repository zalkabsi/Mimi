#!/usr/bin/env bash
# E2 slop-discrimination suite. Thin wrapper — see evals/README.md.
set -euo pipefail
cd "$(dirname "$0")/.."
exec python evals/harness.py --suite e2 "$@"
