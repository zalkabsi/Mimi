#!/usr/bin/env bash
# E3 routing suite. Run once per routing config, then compare.
#   ./evals/run_e3.sh routed
#   ./evals/run_e3.sh ultra
#   ./evals/run_e3.sh super
#   python evals/harness.py --compare evals/out/results_e3_*.json
set -euo pipefail
cd "$(dirname "$0")/.."
MODE="${1:-routed}"
shift || true
exec python evals/harness.py --suite e3 --force-model "$MODE" "$@"
