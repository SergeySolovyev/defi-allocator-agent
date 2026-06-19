# DeFi Lending Allocator Agent

A **non-custodial, gas-aware USDC rate router**: it watches the supply APY of the
six largest Ethereum lending venues — **Aave V3, Compound V3, Spark, Morpho Blue,
Euler V2, Fluid** — and, when a switch clears its cost, **proposes** moving idle
USDC from one venue to a higher-yielding one for a human to approve. It never
moves funds.

Capstone for the **Google × Kaggle "5-Day AI Agents: Intensive Vibe Coding"**
course, built on the paper *"Event-Time MCDM Allocation across DeFi Lending
Protocols"* (Sergei Solovev, WorldQuant University).

## Why this is different

- **The decision is a deterministic ~50-line rule (T1), not a black box.** A
  Cox-hazard ML tier was tested and **lost** out-of-sample — reported openly.
  The edge is event-time resolution + a gas throttle. *Honesty is the moat.*
- **Non-custodial.** The agent proposes; a human signs from their own Safe. The
  agent holds no key that can move funds.
- **Reproducible.** Ships a real per-block data slice; `run_replay_demo.py`
  reproduces the headline number on your machine.

## Headline result (reproducible, `python scripts/run_replay_demo.py`)

Replay over a real per-block slice (Jan–Apr 2026, $1M, net of real gas):

| strategy | net APY | note |
|---|---|---|
| **T1 allocator (us)** | **5.36 %** | 313 switches, **$89** gas |
| hold Euler V2 | 4.85 % | best venue *in hindsight* (unknowable ex-ante) |
| hold Spark | 3.86 % | |
| hold Aave V3 | 3.26 % | the usual "default" park |
| hold Compound V3 | 2.69 % | |

**T1 beats every passive single-protocol hold, including the best-in-hindsight
venue, by +0.51 pp.** The size-haircut table (printed by the demo) honestly shows
the edge eroding as the position grows into the thin venues (Euler ~$16M, Spark
~$29M USDC TVL) — read the row for your size, not the gross headline.

## The rule (T1, paper §III)

```
SWITCH to j  iff   tau_bar_ewma · s_ij  >  (C / V) · BLOCKS_PER_YEAR
```
`s_ij` = cross-protocol spread · `tau_bar_ewma` = EWMA inter-crossover dwell ·
`C` = gas + slippage + MEV · `V` = position size. ~50 lines, no training.
See [`defi_allocator/decision.py`](defi_allocator/decision.py) and the
natural-language contract in [`skills/allocation-decision/SKILL.md`](skills/allocation-decision/SKILL.md).

## Architecture → course days

| course day | piece | file |
|---|---|---|
| Day 2 — Tools | 6-protocol APY fetchers (live DefiLlama / cached panel) | `defi_allocator/fetchers.py` |
| Day 3 — Skills | `allocation-decision` (T1 HOLD/SWITCH) | `skills/allocation-decision/SKILL.md` |
| Day 4 — Skills/Security | `contract-audit` pre-switch gate + STRIDE | `skills/contract-audit/SKILL.md` |
| Day 4 — Human-in-the-loop | propose → human approves (never auto-executes) | `defi_allocator/agent.py` |
| Day 4–5 — Eval / observability | replay + eval vs every passive hold + audit log | `defi_allocator/{replay,eval}.py` |
| Day 1 — Deploy | Cloud Run web UI (approve/reject) | `app/main.py`, `app/Dockerfile` |

Natural-language explanations use **Vertex AI** (the billed Vertex path — *not*
the region-blocked free Gemini API); the core works without it.

## Run it

```bash
pip install -r requirements.txt

# 1) replay demo: T1 vs the six passive holds (reproduces the table above)
python scripts/run_replay_demo.py --position-usd 1000000

# 2) human-in-the-loop on LIVE rates (proposes a switch, you approve)
python -c "from defi_allocator.agent import human_in_the_loop, T1Allocator; \
           human_in_the_loop(T1Allocator(), start_protocol='aave_v3')"

# 3) web UI locally
uvicorn app.main:app --reload    # then open http://localhost:8000

# tests
pytest -q
```

## Deploy to Cloud Run

```bash
gcloud config set project striking-canyon-499613-f3
gcloud run deploy defi-allocator --source . --region europe-west1 \
    --allow-unauthenticated --set-env-vars USE_VERTEX=1
```

## Honest limitations

Net of gas, **gross of MEV/slippage** (size-haircut table quantifies slippage).
Edge demonstrated on a single 4-month real window at near-zero gas; the gas
throttle's value shows up in high-gas regimes (paper §gas-sensitivity). The live
on-chain execution adapters and a security audit are future work — this capstone
is the **decision agent + honest eval + human-in-the-loop**, deployed.

## License

MIT (see [LICENSE](LICENSE)). Not financial advice; non-custodial; proposals
require human approval.
