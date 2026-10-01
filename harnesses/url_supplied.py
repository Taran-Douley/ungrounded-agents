#!/usr/bin/env python3
"""
Study 5 - supplied-URL condition. See PREREG_url_supplied.md.

2 x 2 on the named-vendor prompts of Study 4: familiar vs unfamiliar vendor, with and
without the status-page URL in the request. Reuses cross_vendor.py's request building,
retry logic and call extraction unchanged, so only the prompts differ from Study 4.

  export ANTHROPIC_API_KEY=... OPENAI_API_KEY=...
  python3 url_supplied.py --pilot                # 2 runs, all models
  python3 url_supplied.py --runs 10              # full study
  python3 url_supplied.py analyse ../data/url_supplied_results.csv
"""

import argparse, csv, os, random, sys, threading
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cross_vendor as cv  # noqa: E402

MODELS = [
    "anthropic:claude-opus-5",
    "anthropic:claude-sonnet-4-6",
    "anthropic:claude-haiku-4-5-20251001",
    "openai:gpt-5.6-sol",
    "openai:gpt-5.6-terra",
    "openai:gpt-5.6-luna",
]
VARIANT = "medium"   # configuration export only; see pre-registration

# Status-page URLs, in TRIPLES order: (familiar, unfamiliar).
# Fictional vendors use https://status.<name>.com. No URL is ever fetched.
URLS = [
    ("https://www.cloudflarestatus.com", "https://status.northbrookcdn.com"),
    ("https://status.stripe.com", "https://status.hallowaypayments.com"),
    ("https://status.sendgrid.com", "https://status.trellidgemail.com"),
    ("https://status.datadoghq.com", "https://status.vansgatemonitoring.com"),
    ("https://health.aws.amazon.com/health/status", "https://status.calderwickdns.com"),
    ("https://health.aws.amazon.com/health/status", "https://status.pellmorestorage.com"),
    ("https://status.auth0.com", "https://status.ashcombeidentity.com"),
    ("https://status.sentry.io", "https://status.riversend.com"),
    ("https://status.cloudamqp.com", "https://status.wrenfieldqueue.com"),
    ("https://www.dockerstatus.com", "https://status.duncastleregistry.com"),
    ("https://status.splunk.com", "https://status.marlbrooklogging.com"),
    ("https://status.elastic.co", "https://status.ferngatesearch.com"),
]
CONDITIONS = ("familiar", "familiar_url", "unfamiliar", "unfamiliar_url")
assert len(URLS) == len(cv.TRIPLES)


def with_url(prompt, url):
    """Insert '(url)' before the final punctuation mark; nothing else changes."""
    return f"{prompt[:-1]} ({url}){prompt[-1]}"


def prompt_for(pid, cond):
    _, familiar, unfamiliar = cv.TRIPLES[pid]
    furl, uurl = URLS[pid]
    return {"familiar": familiar,
            "familiar_url": with_url(familiar, furl),
            "unfamiliar": unfamiliar,
            "unfamiliar_url": with_url(unfamiliar, uurl)}[cond]


def run(args):
    keys = {}
    for spec in args.models:
        p = spec.split(":", 1)[0]
        if not os.environ.get(cv.ENV_KEYS[p]):
            sys.exit(f"{cv.ENV_KEYS[p]} not set")
        keys[p] = os.environ[cv.ENV_KEYS[p]]
    if args.reasoning_effort:
        cv.REASONING_EFFORTS[:] = [args.reasoning_effort]

    trials = [(spec, pid, cond, prompt_for(pid, cond), r)
              for spec in args.models
              for pid in range(len(cv.TRIPLES))
              for cond in CONDITIONS
              for r in range(args.runs)]

    done = set()
    if os.path.exists(args.out):
        for row in csv.DictReader(open(args.out, newline="", encoding="utf-8")):
            if row["status"] == "OK":
                done.add((row["model"], int(row["idx"]), row["condition"], int(row["run"])))
    todo = [t for t in trials if (t[0], t[1], t[2], t[4]) not in done]
    print(f"{len(trials)} total, {len(todo)} remaining", file=sys.stderr)

    new = not os.path.exists(args.out)
    fh = open(args.out, "a", newline="", encoding="utf-8")
    w = csv.writer(fh)
    if new:
        w.writerow(["model", "variant", "idx", "condition", "run", "prompt", "status",
                    "tools_called", "fetch_called", "decoy_called", "error"])
    lock = threading.Lock()
    n, errs = [0], [0]
    dname = cv.DECOYS[VARIANT][0]

    def work(t):
        spec, pid, cond, text, r = t
        rng = random.Random(f"{spec}|{pid}|{cond}|{r}")
        called, err = cv.call(spec, text, VARIANT, False, rng, cond, None, keys)
        with lock:
            w.writerow([spec, VARIANT, pid, cond, r, text, "ERROR" if err else "OK",
                        "|".join(called), int("fetch_url" in called),
                        int(dname in called), err])
            fh.flush()
            n[0] += 1
            if err:
                errs[0] += 1
                if errs[0] <= 5:
                    print(f"  ERROR {spec}: {err}", file=sys.stderr)
            if n[0] % 100 == 0:
                print(f"  {n[0]}/{len(todo)}  errors={errs[0]}", file=sys.stderr)

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(work, todo))
    fh.close()
    print(f"done: {n[0]} trials, {errs[0]} errors", file=sys.stderr)


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "analyse":
        import subprocess
        here = os.path.dirname(os.path.abspath(__file__))
        sys.exit(subprocess.call([sys.executable,
                                  os.path.join(here, "..", "analysis", "url_supplied_stats.py"),
                                  sys.argv[2]]))
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=MODELS)
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--pilot", action="store_true", help="2 runs per cell")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--reasoning-effort", default=None)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                  "..", "data", "url_supplied_results.csv"))
    args = ap.parse_args()
    if args.pilot:
        args.runs = 2
        args.out = args.out.replace(".csv", "_pilot.csv")
    run(args)


if __name__ == "__main__":
    main()
