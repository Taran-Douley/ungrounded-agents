#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")"
set -a; . ./.env; set +a
python3 exp6_multiturn.py --runs 10 --workers 8 --out exp6_results
echo "=== exit $? ==="
touch EXP6_DONE
