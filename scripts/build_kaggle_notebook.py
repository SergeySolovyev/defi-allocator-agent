"""Build the Kaggle public-notebook version of the capstone.

Emits ../kaggle_notebook.ipynb: a thin, runnable notebook that clones the
real repo and exercises the ACTUAL modules (rule -> live tools -> agent
proposal -> replay/eval), so a Kaggle grader can open it, hit "Run all",
and reproduce the headline table. No code is re-implemented inline.

    python scripts/build_kaggle_notebook.py
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "kaggle_notebook.ipynb"


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip("\n")}


def code(text: str) -> dict:
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": text.strip("\n")}


CELLS = [
    md("""
# DeFi Lending Allocator Agent — Kaggle Capstone

**Google × Kaggle · "5-Day AI Agents: Intensive Vibe Coding"**  ·  Author: **Sergei Solovev** (WorldQuant University)

A **non-custodial, gas-aware USDC rate-router agent**. It monitors the supply APY of the six largest Ethereum
lending venues — **Aave V3, Compound V3, Spark, Morpho Blue, Euler V2, Fluid** — and, when a switch clears its
gas cost, **proposes** moving idle USDC to the higher-yielding venue for a human to approve. **It never moves funds.**

The decision is a deterministic ~50-line rule (T1) from the author's research paper — *not* a black box. An ML tier
(Cox proportional-hazards) was tested and **lost** out-of-sample; that negative is reported openly. *Honesty is the moat.*

| | |
|---|---|
| 🔗 **Live agent (Cloud Run)** | https://defi-allocator-1038590668771.europe-west1.run.app |
| 💻 **Code (GitHub)** | https://github.com/SergeySolovyev/defi-allocator-agent |
| 📄 **Research basis** | *Event-Time MCDM Allocation across DeFi Lending Protocols* (Solovev, WorldQuant University) |

> ⚙️ **Before Run all:** set **Internet = ON** in the notebook sidebar (Settings → Internet). The setup cell clones the
> repo and the live-rate cell calls DefiLlama. If internet is off the live cell degrades to the last committed panel row,
> and the replay (cell 6) is fully offline either way.
"""),

    md("## 1 · Setup — clone the repo and run the *real* modules\n\n"
       "We clone the GitHub repo into the Kaggle working dir and import the actual `defi_allocator` package "
       "(plus a committed per-block data slice). Nothing below is a re-implementation."),

    code("""
import os, sys, subprocess

REPO_URL = "https://github.com/SergeySolovyev/defi-allocator-agent.git"
BASE = "/kaggle/working" if os.path.isdir("/kaggle/working") else os.getcwd()
path = os.path.join(BASE, "defi-allocator-agent")

if os.path.isdir("defi_allocator"):                     # already inside the repo
    path = os.getcwd()
    print("running inside the repo:", path)
elif os.path.isdir(os.path.join(path, "defi_allocator")):
    print("repo already cloned:", path)
else:
    subprocess.run(["git", "clone", "--depth", "1", REPO_URL, path], check=True)
    print("cloned to", path)

os.chdir(path)
sys.path.insert(0, path)
# pandas / pyarrow / requests are preinstalled on Kaggle; this is a no-op there.
subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                "pandas>=2.0", "pyarrow>=14.0", "requests>=2.31"], check=False)
print("cwd:", os.getcwd())
"""),

    md("""
## 2 · The decision core (T1 rule) — *Day 3 skill*

```
SWITCH to venue j   iff   tau_bar_ewma · s_ij   >   (C / V) · BLOCKS_PER_YEAR
```
- `s_ij` — cross-protocol supply-rate spread (the decision variable)
- `tau_bar_ewma` — EWMA of how long the best venue tends to stay best (expected dwell)
- `C = gas + slippage + MEV` — switching cost · `V` — position size · `BLOCKS_PER_YEAR = 2,628,000`

Equivalently: *switch only when the expected extra yield over the dwell beats the cost.* Below we feed one synthetic
block — parked in Aave at 3.1% while Morpho pays 5.4% — and read the rule's decision and its plain-text rationale.
"""),

    code("""
from defi_allocator.decision import T1Allocator, BlockState

alloc = T1Allocator()
state = BlockState(
    block_number=0,
    lending_apr={"aave_v3": 0.031, "compound_v3": 0.032, "spark": 0.036,
                 "morpho_blue": 0.054, "euler_v2": 0.027, "fluid": 0.051},
    gas_price_gwei=1.0,
    current_protocol="aave_v3",
    position_usd=1_000_000,
)
d = alloc.decide(state)
print("action :", d.action.upper(), "->", d.target)
print("why    :", d.rationale)
"""),

    md("## 3 · Tools — live 6-protocol supply APYs · *Day 2*\n\n"
       "`fetch_live_apys()` hits DefiLlama's public yields API and, per venue, picks the **canonical max-TVL USDC pool** "
       "and its **base** supply rate (`apyBase`, net of reward incentives) — so a thin incentive-juiced vault can't "
       "masquerade as a 50%+ rate. Falls back to the last committed panel row if the network is unavailable."),

    code("""
from defi_allocator.fetchers import fetch_live_apys

apys = fetch_live_apys()
print("live USDC supply APYs (base rate, net of incentives):")
for k, v in sorted(apys.items(), key=lambda kv: -kv[1]):
    print(f"  {k:14s} {v*100:5.2f}%")
"""),

    md("## 4 · The agent — propose, then human-in-the-loop · *Day 4*\n\n"
       "The agent wraps T1 and emits a **proposal** (target, spread, expected gain vs cost, rationale). It does **not** "
       "execute — a human approves or rejects; on approval the calldata goes to the user's own Safe. Non-custodial by "
       "construction."),

    code("""
from defi_allocator.agent import propose

p = propose(T1Allocator(), position_usd=1_000_000,
            current_protocol="aave_v3", apys=apys)   # reuse the live rates fetched above
print("PROPOSAL:", p.decision.action.upper(),
      ("-> " + p.decision.target) if p.decision.target else "(hold)")
print("rationale:", p.explanation)
print("\\n(non-custodial: this is a proposal a human must approve; the agent never moves funds.)")
"""),

    md("""
## 5 · Eval — T1 vs **every** passive hold on real per-block data · *Day 4–5*

The honest benchmark is not "beat the market" — it is *"beat passively parking USDC in any single venue, net of gas."*
We replay T1 and all six passive holds over a committed real per-block slice (Jan–Apr 2026), then print the edge,
the time-share, and a per-size **slippage haircut** (so the number is defensible at institutional size, not just $1M).
This is a pure-Python per-block loop — it takes ~1 minute.
"""),

    code("""
from defi_allocator.fetchers import load_panel
from defi_allocator.eval import evaluate, format_report

panel = load_panel()
print(f"replaying over {len(panel):,} blocks (~1 min)...", flush=True)
ev = evaluate(panel, position_usd=1_000_000)
print("\\n" + format_report(ev))
"""),

    md("""
## 6 · What this is, and its honest limits

**T1 beats every passive single-protocol hold — including the best venue *in hindsight* — by ~+0.5 pp, net of real gas.**
The size-haircut row above shows the edge eroding as the position grows into the thin venues (Euler ~$16M, Spark ~$29M
USDC TVL): read the row for *your* size, not the gross headline.

**Course days, end to end:** tools (Day 2, `fetchers.py`) · a decision skill (Day 3, `skills/allocation-decision`) · a
`contract-audit` skill + human approval (Day 4) · replay/eval + audit log (Day 4–5) · deployed to **Cloud Run** (Day 1).
Natural-language explanations use **Vertex AI** (the billed path — the free Gemini API is region-blocked for this account)
and degrade gracefully to the deterministic rationale.

**Honest scope:** net of gas, gross of MEV/slippage (quantified in the haircut); one 4-month window at near-zero gas
(the gas throttle's value shows in high-gas regimes — paper §gas-sensitivity); live on-chain execution adapters and a
security audit are future work. This capstone is the **decision agent + honest eval + human-in-the-loop, deployed.**

- 🔗 Live: https://defi-allocator-1038590668771.europe-west1.run.app
- 💻 Code: https://github.com/SergeySolovyev/defi-allocator-agent
"""),
]


def main() -> None:
    for i, c in enumerate(CELLS):         # nbformat wants source as a list of lines + a cell id
        c["source"] = (c["source"] + "\n").splitlines(keepends=True)
        c["id"] = f"cell-{i:02d}"
    nb = {
        "cells": CELLS,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.10"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    OUT.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT} ({len(CELLS)} cells)")


if __name__ == "__main__":
    main()
