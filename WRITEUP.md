# DeFi Lending Allocator Agent — Capstone Writeup

**Google × Kaggle "5-Day AI Agents: Intensive Vibe Coding"**
Author: **Sergei Solovev** (WorldQuant University)

- 🔗 **Live agent (Cloud Run):** https://defi-allocator-1038590668771.europe-west1.run.app
- 💻 **Code (GitHub):** https://github.com/SergeySolovyev/defi-allocator-agent
- 📄 **Research basis (paper):** *Event-Time MCDM Allocation across DeFi Lending Protocols* (Solovev, WorldQuant University)

---

## 1. The problem

Crypto treasuries (DAOs, funds, on-chain businesses) leave **idle USDC** parked in
one lending venue while another pays more. Moving it manually means watching the
supply-rate sheet of six protocols and judging, every few minutes, whether a switch
clears its gas cost. It is a repetitive, judgment-laden, high-value workflow — exactly
the kind an agent should run, *if* it can be trusted.

## 2. What I built

A **non-custodial, gas-aware USDC rate-router agent**. It monitors the supply APY of
the six largest Ethereum lending venues — **Aave V3, Compound V3, Spark, Morpho Blue,
Euler V2, Fluid** — and, when a switch clears its cost, **proposes** moving idle USDC
to the higher-yielding venue for a human to approve. **It never moves funds.**

The decision is **not** a black box. It is a deterministic ~50-line rule (T1) from my
research paper. I even tested an ML tier (Cox proportional-hazards) and it **lost**
out-of-sample — I report that openly. *Honesty is the moat.*

## 3. The decision core (T1 rule)

```
SWITCH to venue j   iff   τ̄_ewma · s_ij   >   (C / V) · BLOCKS_PER_YEAR
```
- `s_ij` — cross-protocol supply-rate spread (the decision variable)
- `τ̄_ewma` — EWMA of how long the best venue tends to stay best (expected dwell)
- `C = gas + slippage + MEV` — switching cost; `V` — position size
- `BLOCKS_PER_YEAR = 2,628,000` (12-second blocks)

Equivalently: *switch only when the expected extra yield over the dwell beats the cost.*
~50 lines, no training. (`defi_allocator/decision.py`.)

## 4. Architecture → course days

| Course day | Component | Where |
|---|---|---|
| Day 2 — Tools | 6-protocol APY fetchers (live DefiLlama + committed real panel) | `defi_allocator/fetchers.py` |
| Day 3 — Skills | `allocation-decision` (T1 HOLD/SWITCH, NL contract) | `skills/allocation-decision/SKILL.md` |
| Day 4 — Skills / Security | `contract-audit` pre-switch gate + STRIDE | `skills/contract-audit/SKILL.md` |
| Day 4 — Human-in-the-loop | propose → human Approves/Rejects (never auto-executes) | `defi_allocator/agent.py` |
| Day 4–5 — Eval / observability | replay + eval vs every passive hold + audit log | `defi_allocator/{replay,eval}.py` |
| Day 1 — Deploy | Cloud Run web UI (live) | `app/main.py`, `Dockerfile` |

Natural-language explanations use **Vertex AI** (the billed Vertex path — *not* the
region-blocked free Gemini API), and degrade gracefully to the deterministic rationale.

## 5. Live demo

The deployed service fetches **live** supply APYs, runs T1, and shows the proposal with
**Approve / Reject** buttons. In the screenshot it proposes `aave_v3 → euler_v2`
(spread 5223 bp, `E[gain] $199 > cost $1`) and waits for a human.

> The live Euler rate was an incentive-juiced 54% — which is exactly *why* the
> human-in-the-loop + `contract-audit` gate exist: a too-good rate must be scrutinised,
> not blindly executed. The demo demonstrates its own safety rationale.

*(Screenshot in the GitHub README / the video.)*

## 6. Result (reproducible)

`python scripts/run_replay_demo.py` replays T1 vs the six passive holds on a real
per-block slice (Jan–Apr 2026, $1M, net of real gas):

| strategy | net APY |
|---|---|
| **T1 allocator** | **5.36 %** (313 switches, $89 gas) |
| hold Euler V2 | 4.85 % (best venue *in hindsight*) |
| hold Aave V3 | 3.26 % |
| hold Compound V3 | 2.69 % |

**T1 beats every passive hold — including the best-in-hindsight venue — by +0.51 pp.**
A size-haircut table honestly shows the edge eroding as the position grows into the
thin venues (Euler ~$16M, Spark ~$29M USDC TVL).

## 7. Honest limitations

Net of gas, **gross of MEV/slippage** (quantified in the size-haircut). Edge shown on a
single 4-month window at near-zero gas; the gas-throttle's value shows up in high-gas
regimes (paper §gas-sensitivity). Live on-chain execution adapters and a security audit
are future work — this capstone is the **decision agent + honest eval + human-in-the-loop**,
deployed.

## 8. What I learned

- **Tools + Skills + human-in-the-loop** turn a 50-line rule into a trustworthy agent.
- **Vertex AI** is the right path when the free Gemini API is region-blocked.
- **`gcloud run deploy --source .`** builds in the cloud — no local Docker needed.
- The hardest, most valuable part is **honesty**: shipping the ML-negative and the
  size-haircut is what makes a trust-gated buyer (or grader) believe the rest.

## Links

- Live: https://defi-allocator-1038590668771.europe-west1.run.app
- Code: https://github.com/SergeySolovyev/defi-allocator-agent
- Run it: `pip install -r requirements.txt && python scripts/run_replay_demo.py`
