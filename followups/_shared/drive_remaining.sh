#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")"
set -a; . ./.env; set +a
R() { echo "=== $* ==="; python3 exp5_effort_and_mitigation.py "$@"; echo "=== exit $? ==="; }

# guard v2 first: exploratory, but it is the question the study now turns on.
R --models openai:gpt-5.6-terra --arms responses/default --system guard_v2 \
  --runs 10 --workers 8 --out exp5_results

# luna, plus sol's 3 quota-killed control trials (resume retries them).
R --models openai:gpt-5.6-sol openai:gpt-5.6-luna \
  --arms responses/none responses/default --system baseline \
  --runs 10 --workers 8 --out exp5_results

# positional control - separate CSV, the resume key does not encode shuffle state.
R --models openai:gpt-5.6-terra --arms responses/default --system baseline \
  --variants medium --shuffle-tools --runs 10 --workers 8 \
  --out exp5_shuffled

touch DRIVER_DONE
