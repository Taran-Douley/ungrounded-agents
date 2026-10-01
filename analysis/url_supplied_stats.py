#!/usr/bin/env python3
"""Study 5 analysis, as pre-registered in PREREG_url_supplied.md.

  python3 analysis/url_supplied_stats.py data/url_supplied_results.csv

Primary outcome: share of trials calling fetch_url at least once.
Contrasts (per model and pooled):
  H1  unfamiliar_url vs unfamiliar       (does supplying the argument restore fetch_url?)
  H2  unfamiliar_url vs familiar_url     (does unfamiliarity matter once the argument is there?)
Tests: within-prompt permutation (trial labels permuted within each prompt, 20,000 draws;
conditional on these prompts) and Wilcoxon signed-rank over prompt-level differences
(towards new prompts). Holm across 2 contrasts x models. Cluster-bootstrap 95% CIs.
"""
import sys
import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

REPS = int(__import__("os").environ.get("PERM_REPS", 20000))
rng = np.random.default_rng(17)
INTERNAL = ("search_docs", "search_code")


def load(path):
    d = pd.read_csv(path, encoding="utf-8")
    d = d[d.status == "OK"].copy()
    d["tools_called"] = d.tools_called.fillna("")
    d = d.drop_duplicates(["model", "idx", "condition", "run"])
    d["internal"] = d.tools_called.apply(
        lambda s: int(any(t in INTERNAL for t in s.split("|"))))
    return d


def perm_p(df, outcome, a, b):
    sub = df[df.condition.isin([a, b])]
    obs = sub[sub.condition == a][outcome].mean() - sub[sub.condition == b][outcome].mean()
    groups = [(g.condition.values == a, g[outcome].values) for _, g in sub.groupby("idx")]
    hit = 0
    for _ in range(REPS):
        s1 = n1 = s0 = n0 = 0
        for lab, y in groups:
            lab = rng.permutation(lab)
            s1 += y[lab].sum(); n1 += lab.sum()
            s0 += y[~lab].sum(); n0 += (~lab).sum()
        if abs(s1 / n1 - s0 / n0) >= abs(obs) - 1e-12:
            hit += 1
    return obs, (hit + 1) / (REPS + 1)


def wilcoxon_p(df, outcome, a, b):
    pl = df[df.condition.isin([a, b])].groupby(["idx", "condition"])[outcome].mean().unstack()
    diff = pl[a] - pl[b]
    if (diff != 0).sum() == 0:
        return 1.0
    return float(wilcoxon(pl[a], pl[b]).pvalue)


def boot_ci(df, outcome, cond, n=4000):
    gs = [g[outcome].values for _, g in df[df.condition == cond].groupby("idx")]
    k = len(gs)
    means = [np.concatenate([gs[i] for i in rng.integers(0, k, k)]).mean() for _ in range(n)]
    return np.percentile(means, [2.5, 97.5]) * 100


def holm(ps):
    order = np.argsort(ps)
    adj = np.empty(len(ps))
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (len(ps) - rank) * ps[i])
        adj[i] = min(1.0, running)
    return adj


def main(path):
    d = load(path)
    conds = ["familiar", "familiar_url", "unfamiliar", "unfamiliar_url"]
    models = sorted(d.model.unique())

    print("=" * 96)
    print("DATA HEALTH")
    print("=" * 96)
    for m in models:
        cells = d[d.model == m].groupby("condition").size().reindex(conds, fill_value=0)
        print(f"  {m:<40} " + "  ".join(f"{c}={cells[c]}" for c in conds))

    for outcome, label in (("fetch_called", "FETCH_URL (primary)"),
                           ("internal", "INTERNAL SEARCH (secondary)"),
                           ("decoy_called", "CONFIG-EXPORT DECOY (secondary)")):
        print("\n" + "=" * 96)
        print(f"{label}: share of trials, cluster-bootstrap 95% CI")
        print("=" * 96)
        for m in models + ["POOLED"]:
            sub = d if m == "POOLED" else d[d.model == m]
            cells = []
            for c in conds:
                r = sub[sub.condition == c][outcome].mean() * 100
                lo, hi = boot_ci(sub, outcome, c) if m != "POOLED" else (float("nan"),) * 2
                cells.append(f"{c}={r:5.1f}%" + (f" [{lo:4.1f}-{hi:4.1f}]" if m != "POOLED" else ""))
            print(f"  {m:<40} " + "  ".join(cells))

    print("\n" + "=" * 96)
    print("PRE-REGISTERED CONTRASTS on fetch_url (Holm across contrasts x models)")
    print("=" * 96)
    rows = []
    for m in models:
        sub = d[d.model == m]
        for name, a, b in (("H1 unfamiliar_url - unfamiliar", "unfamiliar_url", "unfamiliar"),
                           ("H2 unfamiliar_url - familiar_url", "unfamiliar_url", "familiar_url")):
            obs, pp = perm_p(sub, "fetch_called", a, b)
            pw = wilcoxon_p(sub, "fetch_called", a, b)
            rows.append((m, name, obs * 100, pp, pw))
    adj_perm = holm(np.array([r[3] for r in rows]))
    adj_wil = holm(np.array([r[4] for r in rows]))
    print(f"  {'model':<40}{'contrast':<34}{'diff pp':>9}{'perm p':>10}{'Holm':>9}"
          f"{'Wilcoxon p':>12}{'Holm':>9}")
    for r, ap, aw in zip(rows, adj_perm, adj_wil):
        print(f"  {r[0]:<40}{r[1]:<34}{r[2]:>9.1f}{r[3]:>10.2g}{ap:>9.2g}{r[4]:>12.3g}{aw:>9.3g}")
    print("\n  Permutation floor: 1/20,001 = 5.0e-05. Wilcoxon floor with 12 untied pairs: 4.9e-04.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/url_supplied_results.csv")
