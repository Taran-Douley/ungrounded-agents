#!/usr/bin/env bash
# Open-weights sweep, Gate 2 (real unmodified MCP catalogues).
# Model selection rule, declared before results were seen: the largest
# general-purpose instruct model in each open-weights family that advertises
# tool support on OpenRouter, excluding vision, coder and thinking variants and
# anything under 30B -- below that, tool-calling reliability confounds the
# measurement in the way filesystem x gpt-5.6-terra already demonstrates.
set -uo pipefail
cd "$(dirname "$0")/.."
for M in "openai/gpt-oss-120b" "meta-llama/llama-3.3-70b-instruct" \
         "qwen/qwen3-235b-a22b-2507" "google/gemma-4-31b-it"; do
  ./gate2/run_openweights.sh "$M" 20
done
touch OW_DONE
