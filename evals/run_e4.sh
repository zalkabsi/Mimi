#!/usr/bin/env bash
# E4 safety suite. Thin wrapper — see evals/README.md.
set -euo pipefail
cd "$(dirname "$0")/.."
exec python evals/harness.py --suite e4 "$@"
