#!/usr/bin/env bash
# Gate 2, extended. The power lever for the cluster-permutation test is the
# number of TRIPLES, not the number of runs -- the test penalises cluster count,
# not effect size, which is why the original read p=0.05-0.34 on effects of
# 35-100%. git 5->11 triples, filesystem 4->9, all new ones target-type, since
# Gate 2 established repo/identity-type ambiguity as a clean null.
set -uo pipefail
cd "$(dirname "$0")/.."
set -a; . /mnt/c/Users/Taran/Documents/Decoy-experiment/exp5/.env; set +a
mkdir -p gate2/results_v2
run() {
  local cat=$1 model=$2 decoy=$3 label=$4
  echo "=== $cat / $model ==="
  .venv/bin/ungrounded run \
    --tools "gate2/catalogues/${cat}.json" \
    --stimuli "gate2/stimuli/${cat}.json" \
    --decoy-name "$decoy" --model "$model" --runs 20 --workers 8 \
    --out "gate2/results_v2/${cat}_${label}.csv" --json \
    > "gate2/results_v2/${cat}_${label}.json" 2> "gate2/results_v2/${cat}_${label}.log"
  echo "  exit $?"
}
run git        gpt-5.6-terra git_status               gpt
run filesystem gpt-5.6-terra list_allowed_directories gpt
if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  run git        claude-sonnet-4-6 git_status               claude
  run filesystem claude-sonnet-4-6 list_allowed_directories claude
else
  echo "ANTHROPIC_API_KEY not set - Claude arms skipped"
fi
touch GATE2_GPT_DONE
