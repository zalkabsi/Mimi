#!/usr/bin/env bash
# E1 reproduction suite. Thin wrapper — see evals/README.md.
set -euo pipefail
cd "$(dirname "$0")/.."
exec python evals/harness.py --suite e1 "$@"
