#!/usr/bin/env bash
# Gate 2 on an open-weights model via OpenRouter.
#
# The CLI builds its OpenAI client with openai.OpenAI(), which reads
# OPENAI_BASE_URL and OPENAI_API_KEY from the environment -- so pointing it at
# an OpenAI-compatible gateway needs no code change. Both are set ONLY in this
# script's own environment, so the real OpenAI arms are unaffected.
#
#   ./run_openweights.sh 'meta-llama/llama-3.3-70b-instruct' [runs]
set -uo pipefail
cd "$(dirname "$0")/.."
MODEL="${1:?usage: run_openweights.sh <openrouter-model-id> [runs]}"
RUNS="${2:-20}"
set -a; . /mnt/c/Users/Taran/Documents/Decoy-experiment/exp5/.env; set +a
: "${OPENROUTER_API_KEY:?OPENROUTER_API_KEY not in exp5/.env}"
export OPENAI_API_KEY="$OPENROUTER_API_KEY"
export OPENAI_BASE_URL="https://openrouter.ai/api/v1"
SLUG=$(echo "$MODEL" | tr '/:' '__')
mkdir -p gate2/results_ow
for pair in "git git_status" "filesystem list_allowed_directories"; do
  set -- $pair
  echo "=== $1 / $MODEL ==="
  .venv/bin/ungrounded run --tools "gate2/catalogues/$1.json" \
    --stimuli "gate2/stimuli/$1.json" --decoy-name "$2" \
    --model "openai:$MODEL" --runs "$RUNS" --workers 6 \
    --out "gate2/results_ow/$1_$SLUG.csv" --json \
    > "gate2/results_ow/$1_$SLUG.json" 2> "gate2/results_ow/$1_$SLUG.log"
  echo "  exit $?"
done
