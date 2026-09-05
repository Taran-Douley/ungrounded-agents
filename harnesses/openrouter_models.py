#!/usr/bin/env python3
"""Pick open-weights models on OpenRouter that can actually do tool calling.

Model ids churn, so choose them at run time rather than hardcoding a list that
will be wrong in a month. Filters to models that (a) advertise tool support and
(b) are open-weights families, then prints ready-to-paste run commands.

    export OPENROUTER_API_KEY=...
    python3 openrouter_models.py
"""
import os, sys, requests

OPEN_FAMILIES = ("meta-llama/", "qwen/", "deepseek/", "mistralai/",
                 "google/gemma", "microsoft/phi", "nousresearch/",
                 "allenai/", "ai21/jamba", "moonshotai/", "z-ai/", "openai/gpt-oss")

key = os.environ.get("OPENROUTER_API_KEY")
if not key:
    sys.exit("OPENROUTER_API_KEY not set")

r = requests.get("https://openrouter.ai/api/v1/models",
                 headers={"Authorization": f"Bearer {key}"}, timeout=60)
r.raise_for_status()
models = r.json().get("data", [])
print(f"{len(models)} models visible\n")

cands = []
for m in models:
    mid = m.get("id", "")
    if not mid.startswith(OPEN_FAMILIES):
        continue
    params = m.get("supported_parameters") or []
    if "tools" not in params:
        continue
    if ":free" in mid:                       # free tiers rate-limit hard
        continue
    pr = m.get("pricing") or {}
    try:
        cost = float(pr.get("prompt", 0)) * 400 + float(pr.get("completion", 0)) * 120
    except (TypeError, ValueError):
        cost = 0.0
    cands.append((cost, mid, m.get("context_length"), m.get("name", "")))

cands.sort()
print(f"{len(cands)} open-weights models with tool support\n")
print(f"{'est. $/1200 trials':<20}{'model id':<52}{'ctx'}")
for cost, mid, ctx, name in cands[:28]:
    print(f"{'$'+format(cost*1200,'.2f'):<20}{mid:<52}{ctx}")

if cands:
    print("\n--- suggested sweep: one from each distinct family, cheapest first ---")
    seen, pick = set(), []
    for cost, mid, ctx, name in cands:
        fam = mid.split("/")[0]
        if fam in seen:
            continue
        seen.add(fam); pick.append(mid)
        if len(pick) >= 4:
            break
    for mid in pick:
        print(f"  {mid}")
    print("\nGate 2 (real catalogues — the headline finding):")
    for mid in pick:
        print(f"  ./gate2/run_openweights.sh '{mid}'")
    print("\nDecoy arm (comparable to Studies 5–6):")
    print("  python3 exp5_effort_and_mitigation.py \\\n"
          "    --models " + " ".join(f"openai:{m}" for m in pick) + " \\\n"
          "    --arms chat/default --system baseline --runs 10 \\\n"
          "    --base-url https://openrouter.ai/api/v1 "
          "--api-key-env OPENROUTER_API_KEY --out exp5_results")
