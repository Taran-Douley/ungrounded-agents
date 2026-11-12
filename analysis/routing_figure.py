#!/usr/bin/env python3
"""Figure 1 of the camera-ready: per-model fetch_url routing in Study 4.

    python analysis/routing_figure.py            # writes figures/routing.pdf
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "cross_vendor_results.csv")
OUT = os.path.join(HERE, "..", "figures", "routing.pdf")

d = pd.read_csv(DATA)
d = d[(d.status == "OK") & (d.set == "core")].drop_duplicates(
    ["model", "variant", "idx", "condition", "run"])
d["fetch"] = d.tools_called.fillna("").str.split("|").apply(lambda t: "fetch_url" in t)
rate = d.groupby(["model", "condition"]).fetch.mean().unstack() * 100
pooled = d.groupby("condition").fetch.mean() * 100

order = ["anthropic:claude-opus-5", "anthropic:claude-sonnet-4-6", "openai:gpt-5.6-terra",
         "openai:gpt-5.6-luna", "openai:gpt-5.6-sol", "anthropic:claude-haiku-4-5-20251001"]
names = ["claude-opus-5", "claude-sonnet-4-6", "gpt-5.6-terra", "gpt-5.6-luna",
         "gpt-5.6-sol", "claude-haiku-4-5", "All six (pooled)"]
K = [rate.loc[m, "resolved_known"] for m in order] + [pooled["resolved_known"]]
F = [rate.loc[m, "resolved_unknown"] for m in order] + [pooled["resolved_unknown"]]
U = [rate.loc[m, "unresolved"] for m in order] + [pooled["unresolved"]]

plt.rcParams.update({"pdf.fonttype": 42, "font.family": "serif", "font.size": 8})
fig, ax = plt.subplots(figsize=(5.5, 1.85))
y = list(range(len(names)))[::-1]
for yi, u, f, k in zip(y, U, F, K):
    ax.plot([min(u, f, k), max(u, f, k)], [yi, yi], color="#d3d2cc", lw=2, zorder=1,
            solid_capstyle="round")
kw = dict(s=26, zorder=3, edgecolors="#ffffff", linewidths=0.8)
off = [(-0.15 if abs(u - f) < 2.5 else 0) for u, f in zip(U, F)]
ax.scatter(K, y, marker="o", color="#2a78d6", label="Familiar, named (Cloudflare)", **kw)
ax.scatter(F, [a - o for a, o in zip(y, off)], marker="s", color="#1baf7a",
           label="Unfamiliar, named (Northbrook CDN)", **kw)
ax.scatter(U, [a + o for a, o in zip(y, off)], marker="^", color="#eb6834",
           label="Unnamed (our CDN provider)", **kw)
ax.set_yticks(y); ax.set_yticklabels(names, fontsize=7)
ax.get_yticklabels()[-1].set_fontweight("bold")
ax.axhline(0.5, color="#e4e3df", lw=0.8)
ax.set_xlim(-3, 103); ax.set_ylim(-0.85, len(names) - 0.45)
ax.set_xticks([0, 25, 50, 75, 100]); ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
ax.set_xlabel("Share of trials calling fetch_url, the tool that serves the request")
ax.xaxis.grid(True, color="#e4e3df", lw=0.6); ax.set_axisbelow(True)
for s in ["top", "right", "left"]:
    ax.spines[s].set_visible(False)
ax.tick_params(length=0)
for v in (pooled["unresolved"], pooled["resolved_unknown"], pooled["resolved_known"]):
    ax.annotate(f"{v:.1f}%", (v, -0.58), ha="center", va="center", fontsize=6.3)
ax.legend(loc="lower center", bbox_to_anchor=(0.45, 0.98), ncol=3, frameon=False, fontsize=6.8)
plt.tight_layout(pad=0.15)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
plt.savefig(OUT)
print("wrote", OUT)
