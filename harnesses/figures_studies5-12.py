#!/usr/bin/env python3
"""Emit every number the briefing page shows, as JSON, straight from the CSVs.

The page is generated from this file's output so a figure can never drift from
the data behind it. Rerun after any new trials and rebuild.
"""
import json, sys
import exp5_effort_and_mitigation as X
from scipy.stats import fisher_exact

rows, bad = X.load("exp5_results.csv")
srows, _ = X.load("exp5_shuffled.csv")
UNG = ("unresolved", "resolved_unknown")


def cell(model, arm, sysv="baseline", conds=None, setn="core",
         pred="decoy_called", idxf=None, src=None):
    z = [r for r in (src or rows) if model in r["model"] and r["arm"] == arm
         and r["system"] == sysv and r["set"] == setn
         and (conds is None or r["condition"] in conds)
         and (idxf is None or int(r["idx"]) in idxf)]
    h = sum(int(r[pred]) for r in z)
    lo, hi = X.wilson(h, len(z))
    return {"hits": h, "n": len(z), "rate": 100 * h / len(z) if z else 0,
            "lo": 100 * lo, "hi": 100 * hi}


def p2(a, b):
    return fisher_exact([[a["hits"], a["n"] - a["hits"]],
                         [b["hits"], b["n"] - b["hits"]]])[1]


out = {"trials": len(rows) + len(srows), "errors": len(bad),
       "truncated": sum(int(r["truncated"]) for r in rows)}

# fig 1 - effort, by model
out["effort"] = []
for m, label in (("terra", "gpt-5.6-terra"), ("sol", "gpt-5.6-sol"),
                 ("luna", "gpt-5.6-luna")):
    a = cell(m, "responses/none", conds=UNG)
    b = cell(m, "responses/default", conds=UNG)
    out["effort"].append({"model": label, "none": a, "default": b,
                          "p": p2(a, b)})

# fig 2 - endpoint, terra, unresolved, by decoy variant
out["endpoint"] = []
for v, label in (("medium", "internal_config_export"),
                 ("high", "list_service_credentials"),
                 ("low", "legacy_batch_reconcile_v1")):
    row = {"decoy": label}
    for arm in ("chat/none", "responses/none", "responses/default"):
        z = [r for r in rows if "terra" in r["model"] and r["arm"] == arm
             and r["system"] == "baseline" and r["set"] == "core"
             and r["variant"] == v and r["condition"] == "unresolved"]
        h = sum(int(r["decoy_called"]) for r in z)
        row[arm] = {"hits": h, "n": len(z), "rate": 100 * h / len(z)}
    out["endpoint"].append(row)
out["endpoint_pooled"] = {a: cell("terra", a, conds=UNG)
                          for a in ("chat/none", "responses/none",
                                    "responses/default")}

# fig 3 - the mitigation frontier
out["guards"] = []
for sysv, label in (("baseline", "No guard"), ("guard", "Guard v1"),
                    ("guard_v2", "Guard v2")):
    d = cell("terra", "responses/default", sysv, conds=UNG)
    k = cell("terra", "responses/default", sysv, conds=("resolved_known",),
             pred="expected_called")
    c = cell("terra", "responses/default", sysv, conds=None, setn="control",
             pred="expected_called", idxf={1, 3})
    ask = cell("terra", "responses/default", sysv, conds=UNG,
               pred="asked_user")
    out["guards"].append({"label": label, "key": sysv, "decoy": d,
                          "known": k, "control": c, "asked": ask})
base = out["guards"][0]
for g in out["guards"][1:]:
    g["p_decoy"] = p2(base["decoy"], g["decoy"])
    g["p_control"] = p2(base["control"], g["control"])
    g["p_known"] = p2(base["known"], g["known"])

# fig 4 - positional control
by = {}
for r in srows:
    if r["set"] == "core" and r["condition"] in UNG:
        p = int(r["decoy_pos"])
        h, n = by.get(p, (0, 0))
        by[p] = (h + int(r["decoy_called"]), n + 1)
last = max(by)
lh, ln = by[last]
oh = sum(by[k][0] for k in by if k != last)
on = sum(by[k][1] for k in by if k != last)
out["position"] = {
    "bars": [{"pos": p, "hits": by[p][0], "n": by[p][1],
              "rate": 100 * by[p][0] / by[p][1]} for p in sorted(by)],
    "last": {"hits": lh, "n": ln, "rate": 100 * lh / ln},
    "rest": {"hits": oh, "n": on, "rate": 100 * oh / on},
    "p": fisher_exact([[lh, ln - lh], [oh, on - oh]])[1]}

json.dump(out, open("figures.json", "w"), indent=1)
print(f"figures.json written - {out['trials']} trials, {out['errors']} errors, "
      f"{out['truncated']} truncated")
