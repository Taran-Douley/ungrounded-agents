#!/usr/bin/env python3
"""
Study 9 - what does an agent substitute, and why that tool?

Study 8 established that correct tool selection collapses when the referent
cannot be grounded. It did not say what gets chosen instead. The pattern in the
raw data suggests something sharper than "it picks a worse tool":

    git_show  needs (repo_path, revision)   -> substituted by git_log (repo_path)
    git_diff  needs (repo_path, target)     -> substituted by git_status (repo_path)
    read_text_file needs (path)             -> substituted by list_allowed_directories ()

**Hypothesis (fixed before running this analysis).** An agent that cannot ground
a referent cannot fill the argument that names it, so it substitutes a tool whose
schema does not require that argument. Substitution is therefore predictable from
the tool schemas alone, without reference to semantics.

Three predictions, in decreasing order of how much they would tell us:

  H1  The substituted tool requires FEWER arguments than the expected tool.
  H2  The substituted tool specifically LACKS the expected tool's referent
      argument - the required parameter that is not common to the catalogue.
  H3  H1 and H2 hold more strongly in the ungroundable condition than in the
      grounded one, i.e. this is about grounding and not a general preference
      for simple tools.
  H4  (added after H3 failed, and marked exploratory) a single argument-light
      tool absorbs a disproportionate share of all misselection in a catalogue.

Null model: a tool drawn uniformly from the same catalogue, excluding the
expected tool. If the observed substitutions are no lower-arity than chance, H1
is unsupported.

This analysis uses only data already collected in Study 8. It spends nothing.

    python3 exp8_substitution.py
    python3 exp8_substitution.py --show 8     # list example substitutions
"""

import argparse, csv, json, os, random, statistics, sys
from collections import Counter, defaultdict

GATE2 = "/mnt/c/Users/Taran/Documents/Ungrounded_v3/gate2"
CELLS = [("git", "claude", "claude-sonnet-4-6"), ("git", "gpt", "gpt-5.6-terra"),
         ("filesystem", "claude", "claude-sonnet-4-6"),
         ("filesystem", "gpt", "gpt-5.6-terra")]
#: filesystem x gpt is void per Study 8 (1.7% correct even when grounded) and is
#: excluded from the pooled tests, reported separately.
VOID = {("filesystem", "gpt")}


def load_catalogue(cat):
    d = json.load(open(f"{GATE2}/catalogues/{cat}.json", encoding="utf-8"))
    tools = d if isinstance(d, list) else d.get("tools", d)
    out = {}
    for t in tools:
        sch = (t.get("inputSchema") or t.get("input_schema")
               or t.get("parameters") or {})
        out[t["name"]] = {
            "required": set(sch.get("required", [])),
            "params": set((sch.get("properties") or {}).keys()),
        }
    return out


def common_args(cat_tools):
    """Arguments required by most tools carry no referent - they are the
    ambient context (`repo_path` for git). The referent argument is what is
    left once those are removed."""
    n = len(cat_tools)
    c = Counter()
    for spec in cat_tools.values():
        c.update(spec["required"])
    return {a for a, k in c.items() if k >= 0.6 * n}


def referent_args(spec, common):
    return spec["required"] - common


def load_trials(cat, label):
    path = f"{GATE2}/results_v2/{cat}_{label}.csv"
    if not os.path.exists(path):
        return []
    stim = {s["id"]: s for s in
            json.load(open(f"{GATE2}/stimuli/{cat}.json", encoding="utf-8"))}
    rows = []
    for r in csv.DictReader(open(path, newline="", encoding="utf-8")):
        if r["status"] != "OK":
            continue
        called = [t for t in (r["tools_called"] or "").split("|") if t]
        if not called:
            continue
        exp = stim[r["triple_id"]]["expected_tool"]
        if exp in called:
            continue                     # correct selection, not a substitution
        rows.append({"cat": cat, "label": label, "triple": r["triple_id"],
                     "condition": r["condition"], "expected": exp,
                     "called": called, "sub": called[0]})
    return rows


def sign_test(deltas):
    """Two-sided sign test on non-zero deltas. Exact binomial."""
    from math import comb
    neg = sum(1 for d in deltas if d < 0)
    pos = sum(1 for d in deltas if d > 0)
    n = neg + pos
    if n == 0:
        return neg, pos, 1.0
    k = min(neg, pos)
    p = sum(comb(n, i) for i in range(k + 1)) / (2 ** n) * 2
    return neg, pos, min(1.0, p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", type=int, default=0)
    ap.add_argument("--seed", type=int, default=17)
    args = ap.parse_args()
    rng = random.Random(args.seed)

    cats = {c: load_catalogue(c) for c in ("git", "filesystem")}
    commons = {c: common_args(t) for c, t in cats.items()}
    print("=" * 78)
    print("STUDY 9 - substitution is predictable from the tool schemas")
    print("=" * 78)
    for c in cats:
        print(f"  {c}: ambient argument(s) required by most tools = "
              f"{sorted(commons[c]) or '(none)'}")
    print()

    allrows = []
    for cat, label, model in CELLS:
        rows = load_trials(cat, label)
        allrows += [dict(r, model=model) for r in rows]
    if not allrows:
        sys.exit("no Study 8 data found - run gate2 first")

    live = [r for r in allrows if (r["cat"], r["label"]) not in VOID]

    # ---- H1: arity ---------------------------------------------------------
    print("H1  the substituted tool requires fewer arguments than the expected one")
    print("-" * 78)
    print(f"  {'cell':<26}{'n subs':<9}{'mean req(exp)':<15}"
          f"{'mean req(sub)':<15}{'delta':<9}{'sign test p'}")
    for cat, label, model in CELLS:
        rows = [r for r in allrows if r["cat"] == cat and r["label"] == label]
        if not rows:
            continue
        de = [len(cats[cat][r["expected"]]["required"]) for r in rows]
        ds = [len(cats[cat].get(r["sub"], {"required": set()})["required"])
              for r in rows]
        deltas = [b - a for a, b in zip(de, ds)]
        neg, pos, p = sign_test(deltas)
        tag = "   (void cell)" if (cat, label) in VOID else ""
        print(f"  {cat+' x '+label:<26}{len(rows):<9}{statistics.mean(de):<15.2f}"
              f"{statistics.mean(ds):<15.2f}{statistics.mean(deltas):<+9.2f}"
              f"{p:.3g}{tag}")
    de = [len(cats[r['cat']][r["expected"]]["required"]) for r in live]
    ds = [len(cats[r['cat']].get(r["sub"], {"required": set()})["required"])
          for r in live]
    deltas = [b - a for a, b in zip(de, ds)]
    neg, pos, p = sign_test(deltas)
    print(f"  {'POOLED (void excluded)':<26}{len(live):<9}"
          f"{statistics.mean(de):<15.2f}{statistics.mean(ds):<15.2f}"
          f"{statistics.mean(deltas):<+9.2f}{p:.3g}")
    print(f"    lower-arity {neg}, higher-arity {pos}, equal {len(deltas)-neg-pos}")

    # null model
    nulls = []
    for r in live:
        pool = [t for t in cats[r["cat"]] if t != r["expected"]]
        pick = rng.choice(pool)
        nulls.append(len(cats[r["cat"]][pick]["required"])
                     - len(cats[r["cat"]][r["expected"]]["required"]))
    print(f"    null model (uniform tool from the same catalogue): "
          f"mean delta {statistics.mean(nulls):+.2f} vs observed "
          f"{statistics.mean(deltas):+.2f}")

    # ---- H2: the referent argument ----------------------------------------
    print("\nH2  the substitute lacks the expected tool's referent argument")
    print("-" * 78)
    print(f"  {'cell':<26}{'n with a referent arg':<25}{'substitute drops it'}")
    tot_h, tot_n = 0, 0
    for cat, label, model in CELLS:
        rows = [r for r in allrows if r["cat"] == cat and r["label"] == label]
        rows = [r for r in rows if referent_args(cats[cat][r["expected"]],
                                                 commons[cat])]
        if not rows:
            continue
        h = 0
        for r in rows:
            ref = referent_args(cats[cat][r["expected"]], commons[cat])
            sub = cats[cat].get(r["sub"], {"required": set(), "params": set()})
            if not (ref & sub["required"]):
                h += 1
        if (cat, label) not in VOID:
            tot_h += h; tot_n += len(rows)
        tag = "   (void cell)" if (cat, label) in VOID else ""
        print(f"  {cat+' x '+label:<26}{len(rows):<25}"
              f"{h}/{len(rows)} = {100*h/len(rows):.1f}%{tag}")
    if tot_n:
        print(f"  {'POOLED (void excluded)':<26}{tot_n:<25}"
              f"{tot_h}/{tot_n} = {100*tot_h/tot_n:.1f}%")

    # H2 is mostly definitional and saying so is the point: in both catalogues
    # nearly every referent argument is unique to its own tool, so ANY
    # substitution necessarily drops it. The figure above is therefore inflated.
    # The honest test is the subset where a tool requiring the same argument
    # existed and could have been chosen.
    nontrivial, avoided = 0, 0
    for r in live:
        cat = r["cat"]
        ref = referent_args(cats[cat][r["expected"]], commons[cat])
        if not ref:
            continue
        alts = [n for n, sp in cats[cat].items()
                if n != r["expected"] and (ref & sp["required"])]
        if not alts:
            continue
        nontrivial += 1
        avoided += r["sub"] not in alts
    print(f"\n  CAVEAT: most referent arguments are unique to their own tool, so")
    print(f"  the figure above is largely definitional. Non-trivial subset - cases")
    print(f"  where another tool requiring the same argument existed:")
    if nontrivial:
        print(f"    {avoided}/{nontrivial} = {100*avoided/nontrivial:.1f}% still avoided it")
        print(f"    (all from one argument pair in one catalogue; treat as suggestive)")
    else:
        print("    none - H2 is untestable on these catalogues")

    # ---- the attractor -----------------------------------------------------
    print("\nH4  an argument-light tool absorbs most of the misselection")
    print("-" * 78)
    print("  Not definitional, and the practically useful result: a catalogue's")
    print("  low-arity orienting tool acts as a sink for substitution.")
    print(f"  {'catalogue':<14}{'top substitute':<30}{'share of all misselections'}")
    for cat in ("git", "filesystem"):
        sub = [r for r in live if r["cat"] == cat]
        if not sub:
            continue
        c = Counter(r["sub"] for r in sub)
        top, n = c.most_common(1)[0]
        req = sorted(cats[cat][top]["required"])
        print(f"  {cat:<14}{top+' '+str(req):<30}{n}/{len(sub)} = {100*n/len(sub):.1f}%")
    print("\n  Arity is necessary but not sufficient: git_status and git_diff_staged")
    print("  both require one argument, and substitution concentrates on the former.")
    print("  Among equally argument-light tools, the one that reads as 'orient me'")
    print("  wins. Arity predicts the candidate set; semantics picks within it.")

    # ---- H3: is it about grounding? ---------------------------------------
    print("\nH3  the pattern is stronger when the referent cannot be grounded")
    print("-" * 78)
    print(f"  {'condition':<24}{'n subs':<9}{'mean arity delta':<20}"
          f"{'drops referent arg'}")
    for cond in ("groundable_known", "groundable_unknown", "ungroundable"):
        rows = [r for r in live if r["condition"] == cond]
        if not rows:
            continue
        d = [len(cats[r['cat']].get(r["sub"], {"required": set()})["required"])
             - len(cats[r['cat']][r["expected"]]["required"]) for r in rows]
        withref = [r for r in rows
                   if referent_args(cats[r['cat']][r["expected"]], commons[r['cat']])]
        h = sum(1 for r in withref
                if not (referent_args(cats[r['cat']][r["expected"]], commons[r['cat']])
                        & cats[r['cat']].get(r["sub"], {"required": set()})["required"]))
        frac = f"{h}/{len(withref)} = {100*h/len(withref):.1f}%" if withref else "-"
        print(f"  {cond:<24}{len(rows):<9}{statistics.mean(d):<+20.2f}{frac}")

    # ---- what actually gets chosen ----------------------------------------
    print("\n  most common substitutions (ungroundable condition)")
    c = Counter((r["cat"], r["expected"], r["sub"]) for r in live
                if r["condition"] == "ungroundable")
    for (cat, exp, sub), n in c.most_common(10):
        re_ = sorted(cats[cat][exp]["required"])
        rs = sorted(cats[cat].get(sub, {"required": set()})["required"])
        print(f"    [{cat}] {exp}{re_}  ->  {sub}{rs}   x{n}")

    if args.show:
        print("\n  example trials")
        for r in [x for x in live if x["condition"] == "ungroundable"][:args.show]:
            print(f"    {r['triple']} {r['model']}: expected {r['expected']}, "
                  f"called {'|'.join(r['called'])}")


if __name__ == "__main__":
    main()
