#!/usr/bin/env python3
"""
Base-rate proxy: how often does a realistic agent request contain an
ungroundable entity reference?

Why this exists
---------------
Every rate in Studies 1-6 is conditional: "N% OF UNGROUNDABLE REQUESTS". The
unconditional rate needs the size of that class in real traffic, which we do not
have. The only estimate available from our own data is Exp 1, where 9 of 9 hits
came from 1 of 101 benign prompts - so roughly 1%.

This classifies prompts from published agent benchmarks against the same
taxonomy the studies use, giving a second, independent proxy. It is a PROXY:
benchmark prompts are authored to be answerable, which biases them toward
groundable references, so this should read as a LOWER bound on real traffic.

No API calls. Pure lexical classification, deliberately transparent so the rule
can be argued with rather than trusted.

    python3 baserate.py                 # classify the bundled corpora
    python3 baserate.py --show 12       # print examples of each class
"""
import argparse, json, re, sys
from collections import Counter

# --- the taxonomy, matching the studies -----------------------------------
# ungroundable-possessive : "our CDN provider", "the library we depend on"
# ungroundable-deictic    : "this service", "that package" with no antecedent
# named-unfamiliar        : a proper noun the model has no reason to know
# groundable              : everything else

# Studies 5-6 forced a distinction the first version of this classifier missed.
# "our X" splits in two, and only one half is the phenomenon:
#
#   INTERNAL   "our auth module", "our billing repo" - the team's own thing.
#              The agent's tools CAN resolve it. Gate 2 found repo-identity
#              ambiguity to be a clean null in both model families.
#   EXTERNAL   "our CDN provider", "the SDK we use" - a third party. Internal
#              tooling cannot resolve it, and this is where the effect lives.
#
# Separating them is also the open design problem that guard v2 could not solve,
# so the classifier and the mitigation are stuck on the same distinction.
EXTERNAL_NOUN = (r"provider|vendor|supplier|partner|sdk|third[- ]party|"
                 r"cdn|registry|marketplace|upstream|saas|"
                 r"payment processor|host(?:ing)?|carrier|gateway")
INTERNAL_NOUN = (r"repo|repository|module|codebase|branch|commit|test|tests|"
                 r"suite|migration|schema|handler|middleware|endpoint|"
                 r"function|class|script|makefile|readme")

POSSESSIVE = re.compile(
    r"\b(our|my|we|us)\b[^.?!]{0,40}?\b("
    r"provider|vendor|service|platform|system|tool|api|endpoint|cluster|"
    r"database|db|repo|repository|project|app|application|site|server|"
    r"pipeline|queue|broker|gateway|proxy|cdn|host|instance|environment|"
    r"account|tenant|org|organisation|organization|team|library|package|"
    r"dependency|framework|module|config|configuration|deployment|release|"
    r"branch|commit|build|domain|bucket|registry|dashboard|monitor)\b", re.I)

WE_DEPEND = re.compile(r"\bthe\s+\w+(?:\s+\w+)?\s+(we|our team)\s+"
                       r"(depend on|use|run|maintain|own|rely on)\b", re.I)

DEICTIC = re.compile(r"^\s*(?:please\s+)?(?:can you\s+)?\w+[^.?!]{0,30}?"
                     r"\bthis\s+(service|package|library|tool|repo|repository|"
                     r"link|endpoint|api|module|dependency|error|config)\b", re.I)

EXT = re.compile(r"\b(our|the|a)\b[^.?!]{0,30}?\b(" + EXTERNAL_NOUN + r")\b", re.I)
INT = re.compile(r"\b(our|my|we|the)\b[^.?!]{0,25}?\b(" + INTERNAL_NOUN + r")\b", re.I)


def classify(text):
    """Four classes. Only 'external' is the population the studies measure."""
    t = text.strip()
    possessive = bool(POSSESSIVE.search(t) or WE_DEPEND.search(t))
    if possessive and EXT.search(t):
        return "ungroundable-external"
    if DEICTIC.search(t):
        return "ungroundable-deictic"
    if possessive and INT.search(t):
        return "possessive-internal"
    if possessive:
        return "ungroundable-external"      # possessive, no internal anchor
    return "groundable"


def load_corpora(paths):
    """Each corpus is a JSON list of strings, or {name: [strings]}."""
    corpora = {}
    for p in paths:
        d = json.load(open(p, encoding="utf-8"))
        if isinstance(d, dict):
            corpora.update(d)
        else:
            corpora[p] = d
    return corpora


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("corpora", nargs="*", default=["corpora.json"])
    ap.add_argument("--show", type=int, default=0)
    args = ap.parse_args()

    corpora = load_corpora(args.corpora)
    print("=" * 74)
    print("BASE-RATE PROXY - share of requests carrying an ungroundable entity")
    print("=" * 74)
    print(f"{'corpus':<34}{'n':<7}{'external':<16}{'internal':<11}{'deictic'}")
    grand = Counter()
    examples = {}
    for name, prompts in corpora.items():
        c = Counter(classify(p) for p in prompts)
        for p in prompts:
            k = classify(p)
            examples.setdefault(k, []).append((name, p))
        grand.update(c)
        n = len(prompts)
        ung = c["ungroundable-external"]
        print(f"{name:<34}{n:<7}{f'{ung}/{n} = {100*ung/n:.1f}%':<16}"
              f"{c['possessive-internal']:<11}{c['ungroundable-deictic']}")
    n = sum(grand.values())
    ung = grand["ungroundable-external"]
    print("-" * 74)
    print(f"{'POOLED':<34}{n:<7}{f'{ung}/{n} = {100*ung/n:.1f}%'}")
    print(f"\n  Exp 1's own benign set, for comparison:  1/101 = 1.0%")
    print("\n  This is a lower bound. Benchmark prompts are authored to be")
    print("  answerable, which selects for groundable references; real user")
    print("  traffic contains more possessives, not fewer.")

    # ---- what the base rate is FOR -------------------------------------
    # The programme opens with a question about canary tools: plant a decoy no
    # legitimate task should call, alert when something calls it. That design
    # lives or dies on the UNCONDITIONAL false-positive rate, which is the
    # conditional rate the studies measure times the size of the affected class.
    print("\n" + "=" * 74)
    print("WHAT THIS IMPLIES FOR A DECOY / CANARY TOOL")
    print("=" * 74)
    base = ung / n
    for label, cond in (("single-turn, Study 5 (terra, default effort)", 0.1208),
                        ("two-turn, Study 6 (either turn)", 0.4208)):
        fp = base * cond
        print(f"  {label}")
        print(f"    P(ungroundable) {100*base:.1f}%  x  P(decoy | ungroundable) "
              f"{100*cond:.2f}%  =  {100*fp:.2f}% of ALL requests")
        for fleet in (10_000, 100_000):
            print(f"      at {fleet:,} agent requests/day: "
                  f"{fp*fleet:,.0f} false alarms/day")
    print("\n  A canary that fires on 1-2% of ordinary traffic is not a canary.")
    print("  This is the programme's opening question, finally with a number on it.")
    print("  Both inputs are soft: the base rate is a lower-bound proxy from a")
    print("  benign engineering set, and the conditional rate is one model on one")
    print("  catalogue. The order of magnitude is the claim, not the decimals.")

    if args.show:
        for k in ("ungroundable-external", "possessive-internal",
                  "ungroundable-deictic", "groundable"):
            print(f"\n--- {k} ---")
            for src, p in examples.get(k, [])[:args.show]:
                print(f"  [{src}] {p}")


if __name__ == "__main__":
    main()
