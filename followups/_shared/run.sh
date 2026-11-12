#!/usr/bin/env bash
# Wrapper so the API keys live in one gitignored file instead of the shell
# history. Put them in exp5/.env as:
#     OPENAI_API_KEY=sk-...
#     ANTHROPIC_API_KEY=sk-ant-...
# then:  ./run.sh --smoke --models openai:gpt-5.6-terra
set -euo pipefail
cd "$(dirname "$0")"
[ -f .env ] || { echo "exp5/.env not found - see the header of this script" >&2; exit 1; }
set -a; . ./.env; set +a
exec python3 exp5_effort_and_mitigation.py "$@"
