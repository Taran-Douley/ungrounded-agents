#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")"
set -a; . ./.env; set +a
python3 exp5_effort_and_mitigation.py --controls-only --runs 50 \
  --models openai:gpt-5.6-terra --arms responses/default \
  --system baseline guard guard_v2 --workers 8 --out exp5_results
echo "=== exit $? ==="
touch CTRL_DONE
