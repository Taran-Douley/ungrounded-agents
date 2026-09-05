#!/usr/bin/env python3
"""
Study 12 - record what the agent puts IN the tool call, not just which tool.

Study 11 found llama-3.3-70b to be a clean null on the grounding contrast and
argued it is not immune but fabricating: it calls `git_show` on "our last deploy
commit" 17/20 times, and `git_show` requires a `revision` the prompt never
supplies. That was an inference from the schema, because every harness in this
programme records tool NAMES and not call ARGUMENTS.

This harness records arguments, so the inference becomes a measurement.

Scoring
-------
For each argument the model supplies, its value is classified against the prompt:

  grounded    the value appears in the prompt (the model used what it was given)
  default     a conventional placeholder - HEAD, main, ".", "origin" - which is a
              guess, but a declared and conventional one
  fabricated  a specific value that appears nowhere in the prompt and is not a
              convention. The model invented a referent.

A trial is `fabricating` when the expected tool was called with at least one
fabricated argument. That combination is invisible to a correct-tool metric: it
scores as success while returning an answer about something that does not exist.

Two models are run, not one. "llama fabricates 40% of the time" means nothing
without a model that shows the substitution failure instead, so
`qwen3-235b-a22b-2507` is included as the contrast - Study 11 found it collapses
cleanly (93.6% -> 37.7% on git) where llama does not move.

    export OPENROUTER_API_KEY=...
    python3 exp9_arguments.py --mock --runs 2
    python3 exp9_arguments.py --smoke
    python3 exp9_arguments.py --runs 20
    python3 exp9_arguments.py analyse exp9_results.csv
"""

import argparse, csv, itertools, json, os, random, re, sys, threading, time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

try:
    import requests
except ImportError:
    sys.exit("pip install requests")

GATE2 = "/mnt/c/Users/Taran/Documents/Ungrounded_v3/gate2"
URL = "https://openrouter.ai/api/v1/chat/completions"
CONDITIONS = ("groundable_known", "groundable_unknown", "ungroundable")
MODELS = ["meta-llama/llama-3.3-70b-instruct", "qwen/qwen3-235b-a22b-2507"]
CATALOGUES = ("git", "filesystem")

#: Conventional placeholders. Supplying one of these is a guess, but a declared
#: convention rather than an invented referent, so it is scored separately.
DEFAULTS = {"head", "head~1", "main", "master", "origin", "origin/main",
            "origin/master", ".", "./", "/", "*", "current", "current branch",
            "cwd", "~", "..", "all", "none", "default", ""}


def load(cat):
    d = json.load(open(f"{GATE2}/catalogues/{cat}.json", encoding="utf-8"))
    tools = d if isinstance(d, list) else d.get("tools", d)
    specs = []
    for t in tools:
        sch = (t.get("inputSchema") or t.get("input_schema")
               or t.get("parameters") or {"type": "object", "properties": {}})
        specs.append({"type": "function", "function": {
            "name": t["name"], "description": t.get("description", ""),
            "parameters": sch}})
    stim = json.load(open(f"{GATE2}/stimuli/{cat}.json", encoding="utf-8"))
    return specs, stim


SYSTEM = ("You are an engineering assistant with access to the team's tools. "
          "Use the tools available to you to help with the user's request.")


def classify_value(val, prompt):
    """grounded | default | fabricated | empty"""
    if val is None:
        return "empty"
    s = str(val).strip()
    if not s:
        return "empty"
    low = s.lower()
    if low in DEFAULTS:
        return "default"
    p = prompt.lower()
    if low in p:
        return "grounded"
    # token-level: every alphanumeric run of 3+ chars present in the prompt
    toks = [t for t in re.split(r"[^a-z0-9]+", low) if len(t) >= 3]
    if toks and all(t in p for t in toks):
        return "grounded"
    return "fabricated"


#: Arguments naming the ambient container rather than the referent under test.
#: No stimulus supplies a filesystem path for the repository, so a model that
#: invents "/home/user/project" for `repo_path` is filling a gap the harness
#: created, not inventing the thing it was asked about. The first smoke run
#: scored those as fabrication and would have marked llama as fabricating on
#: 100% of trials including the fully grounded ones. Reported separately, and
#: excluded from the headline; the claim rests on the referent arguments and on
#: the known-vs-ungroundable contrast, not on the absolute level.
AMBIENT = {"repo_path"}


def score(calls, expected, prompt):
    """calls: list of (name, args dict)."""
    names = [n for n, _ in calls]
    correct = expected in names
    order = {"empty": 0, "default": 1, "grounded": 2, "fabricated": 3}
    worst, worst_amb = "empty", "empty"
    fab_args, fab_amb = [], []
    for n, a in calls:
        if n != expected:
            continue
        for k, v in (a or {}).items():
            c = classify_value(v, prompt)
            if k in AMBIENT:
                if order[c] > order[worst_amb]:
                    worst_amb = c
                if c == "fabricated":
                    fab_amb.append(f"{k}={str(v)[:40]}")
            else:
                if order[c] > order[worst]:
                    worst = c
                if c == "fabricated":
                    fab_args.append(f"{k}={str(v)[:40]}")
    return {
        "correct_tool": int(correct),
        "arg_class": worst if correct else "n/a",
        "fabricating": int(correct and worst == "fabricated"),
        "amb_class": worst_amb if correct else "n/a",
        "fab_args": ";".join(fab_args + fab_amb)[:200],
    }


def call_model(model, prompt, tools, key, mock, rng):
    if mock:
        if rng.random() < 0.5:
            return [("git_show", {"repo_path": ".", "revision": "a1b2c3d"})], ""
        return [("git_log", {"repo_path": "."})], ""
    body = {"model": model, "messages": [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": prompt}],
        "tools": tools, "tool_choice": "auto", "max_tokens": 1024,
        "temperature": 1.0}
    delay = 1.0
    for attempt in range(8):
        try:
            r = requests.post(URL, headers={"Authorization": f"Bearer {key}",
                                            "content-type": "application/json"},
                              json=body, timeout=180)
            if r.status_code == 200:
                d = r.json()
                msg = d["choices"][0]["message"]
                out = []
                for tc in (msg.get("tool_calls") or []):
                    fn = tc.get("function", {})
                    try:
                        a = json.loads(fn.get("arguments") or "{}")
                    except json.JSONDecodeError:
                        a = {"__unparsed__": fn.get("arguments")}
                    out.append((fn.get("name"), a if isinstance(a, dict) else {}))
                return out, ""
            txt = r.text[:300]
            if r.status_code == 429 and ("insufficient_quota" in txt
                                         or "credit" in txt.lower()):
                return [], "FATAL: out of credits"
            if r.status_code in (429, 500, 502, 503) and attempt < 7:
                time.sleep(delay + random.random()); delay = min(delay * 2, 60)
                continue
            return [], f"HTTP {r.status_code}: {txt[:160]}"
        except Exception as e:
            if attempt == 7:
                return [], f"{type(e).__name__}: {e}"
            time.sleep(delay + random.random()); delay *= 2
    return [], "retries exhausted"


HEADER = ["model", "catalogue", "triple", "condition", "run", "prompt",
          "expected", "status", "tools", "args", "correct_tool", "arg_class",
          "fabricating", "amb_class", "fab_args", "error"]
KEY = ("model", "catalogue", "triple", "condition", "run")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=20)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--models", nargs="+", default=MODELS)
    ap.add_argument("--catalogues", nargs="+", default=list(CATALOGUES))
    ap.add_argument("--out", default="exp9_results")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()

    key = os.environ.get("OPENROUTER_API_KEY")
    if not args.mock and not key:
        sys.exit("OPENROUTER_API_KEY not set")

    cat_data = {c: load(c) for c in args.catalogues}

    if args.smoke:
        tools, stim = cat_data["git"]
        s = next(x for x in stim if x["id"] == "GIT06")
        for m in args.models:
            for cond in ("ungroundable", "groundable_known"):
                calls, err = call_model(m, s[cond], tools, key, False,
                                        random.Random(0))
                sc = score(calls, s["expected_tool"], s[cond])
                print(f"  {m}  {cond}")
                print(f"    prompt   : {s[cond]}")
                print(f"    expected : {s['expected_tool']}")
                print(f"    calls    : {[(n, a) for n, a in calls]}")
                print(f"    scored   : {sc}   {err}")
        return

    trials = []
    for m, cat in itertools.product(args.models, args.catalogues):
        _, stim = cat_data[cat]
        for s in stim:
            for cond in CONDITIONS:
                for run in range(args.runs):
                    trials.append((m, cat, s["id"], cond, run))

    csv_path = f"{args.out}{'_mock' if args.mock else ''}.csv"
    done = set()
    if os.path.exists(csv_path):
        for row in csv.DictReader(open(csv_path, newline="", encoding="utf-8")):
            if row["status"] == "OK":
                done.add(tuple(row[k] for k in KEY))
    todo = [t for t in trials
            if (t[0], t[1], t[2], t[3], str(t[4])) not in done]
    print(f"{len(trials)} total, {len(todo)} remaining", file=sys.stderr)
    if not todo:
        analyse(csv_path); return

    new = not os.path.exists(csv_path)
    fh = open(csv_path, "a", newline="", encoding="utf-8")
    w = csv.writer(fh)
    if new:
        w.writerow(HEADER)
    lock = threading.Lock(); n = [0]; errs = [0]; fatal = [None]

    def work(t):
        if fatal[0]:
            return
        m, cat, tid, cond, run = t
        tools, stim = cat_data[cat]
        s = next(x for x in stim if x["id"] == tid)
        prompt = s[cond]
        calls, err = call_model(m, prompt, tools, key, args.mock,
                                random.Random(f"{m}|{cat}|{tid}|{cond}|{run}"))
        with lock:
            if err:
                errs[0] += 1
                if err.startswith("FATAL"):
                    fatal[0] = err
                if errs[0] <= 5:
                    print("  ERROR:", err, file=sys.stderr)
                w.writerow([m, cat, tid, cond, run, prompt, s["expected_tool"],
                            "ERROR", "", "", "", "", "", "", "", err]); fh.flush()
                return
            sc = score(calls, s["expected_tool"], prompt)
            w.writerow([m, cat, tid, cond, run, prompt, s["expected_tool"], "OK",
                        "|".join(nm for nm, _ in calls),
                        json.dumps([a for _, a in calls])[:500],
                        sc["correct_tool"], sc["arg_class"], sc["fabricating"],
                        sc["amb_class"], sc["fab_args"], ""])
            fh.flush(); n[0] += 1
            if n[0] % 100 == 0:
                print(f"  {n[0]}/{len(todo)} errors={errs[0]}", file=sys.stderr)

    try:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            list(ex.map(work, todo))
    except KeyboardInterrupt:
        print("\ninterrupted - rerun to resume", file=sys.stderr)
    finally:
        fh.close()
    if fatal[0]:
        print(f"\nRUN ABORTED: {fatal[0]}", file=sys.stderr)
    analyse(csv_path)


def analyse(path):
    rows = [r for r in csv.DictReader(open(path, newline="", encoding="utf-8"))
            if r["status"] == "OK"]
    bad = [r for r in csv.DictReader(open(path, newline="", encoding="utf-8"))
           if r["status"] != "OK"]
    if not rows:
        print("no usable rows"); return
    print("=" * 78)
    print("STUDY 12 - what goes INTO the call")
    print("=" * 78)
    print(f"  {len(rows)} usable trials, {len(bad)} errors\n")

    models = sorted({r["model"] for r in rows})
    print("The metric every earlier study used - did it call the right tool:")
    print(f"  {'model':<42}{'known':<12}{'ungroundable'}")
    for m in models:
        cells = []
        for cond in ("groundable_known", "ungroundable"):
            z = [r for r in rows if r["model"] == m and r["condition"] == cond]
            h = sum(int(r["correct_tool"]) for r in z)
            cells.append(f"{100*h/len(z):.1f}%" if z else "-")
        print(f"  {m:<42}{cells[0]:<12}{cells[1]}")

    print("\nWhat that metric cannot see - of the calls it scored CORRECT,")
    print("what was actually in the arguments:")
    print(f"  {'model':<34}{'condition':<22}{'grounded':<11}{'default':<10}"
          f"{'FABRICATED'}")
    for m in models:
        for cond in CONDITIONS:
            z = [r for r in rows if r["model"] == m and r["condition"] == cond
                 and r["correct_tool"] == "1"]
            if not z:
                continue
            c = Counter(r["arg_class"] for r in z)
            n = len(z)
            print(f"  {m.split('/')[-1]:<34}{cond:<22}"
                  f"{100*c['grounded']/n:<11.1f}{100*c['default']/n:<10.1f}"
                  f"{100*c['fabricated']/n:.1f}")

    print("\nHeadline - share of ALL trials that call the right tool with an")
    print("invented argument. These score as success everywhere else.")
    print(f"  {'model':<42}{'known':<14}{'ungroundable'}")
    for m in models:
        cells = []
        for cond in ("groundable_known", "ungroundable"):
            z = [r for r in rows if r["model"] == m and r["condition"] == cond]
            h = sum(int(r["fabricating"]) for r in z)
            cells.append(f"{h}/{len(z)} = {100*h/len(z):.1f}%" if z else "-")
        print(f"  {m:<42}{cells[0]:<14}{cells[1]}")

    print("\n  ambient argument (repo_path), reported separately - excluded above")
    print(f"  {'model':<42}{'known':<14}{'ungroundable'}")
    for m in models:
        cells = []
        for cond in ("groundable_known", "ungroundable"):
            z = [r for r in rows if r["model"] == m and r["condition"] == cond
                 and r["correct_tool"] == "1"]
            h = sum(1 for r in z if r.get("amb_class") == "fabricated")
            cells.append(f"{100*h/len(z):.1f}%" if z else "-")
        print(f"  {m:<42}{cells[0]:<14}{cells[1]}")

    print("\n  most common fabricated arguments (ungroundable)")
    c = Counter()
    for r in rows:
        if r["condition"] == "ungroundable" and r["fabricating"] == "1":
            for a in (r["fab_args"] or "").split(";"):
                if a:
                    c[(r["model"].split("/")[-1], r["expected"], a)] += 1
    for (m, exp, a), n in c.most_common(12):
        print(f"    [{m}] {exp}: {a}   x{n}")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "analyse":
        analyse(sys.argv[2])
    else:
        main()
