---
name: allocation-decision
description: >
  Decide whether to HOLD idle USDC in the current lending venue or SWITCH it to
  a higher-yielding one, using the gas-aware T1 threshold rule. Use whenever the
  agent has fresh per-protocol supply APYs and must propose an allocation move.
---

# Skill: allocation-decision (T1 gas-aware threshold)

You decide HOLD vs SWITCH for a treasury's idle USDC across six Ethereum
lending venues — **Aave V3, Compound V3, Spark, Morpho Blue, Euler V2, Fluid** —
and you NEVER move funds. You emit a *proposal* a human approves.

## Inputs you receive
- `position_usd` — size of the idle USDC position.
- `current_protocol` — where it sits now (or `null` if uninvested).
- `lending_apr` — `{protocol: supply_APR_fraction}` for the six venues now.
- `gas_price_gwei` — current Ethereum base fee.
- `dwell_blocks` — EWMA of how long the best venue tends to stay best.

## The rule (deterministic — do not improvise)
1. `best` = the venue with the highest valid APR; `best_apr` its rate.
2. If `current_protocol is null` → **SWITCH** to `best` (cold start).
3. If `best == current_protocol` → **HOLD** (already optimal).
4. Else let `spread = best_apr − current_apr`, and compute:
   - expected gain `E = position_usd · spread · dwell_blocks / BLOCKS_PER_YEAR`
   - switching cost `C = gas + slippage + MEV`
     (`gas = 200000 · gas_price_gwei·1e9 · eth_price / 1e18`; slippage/MEV ≈ 0
     at retail/mid size with Flashbots protection)
   - **SWITCH** to `best` iff `E > C`, else **HOLD**.

`BLOCKS_PER_YEAR = 2_628_000` (12-second blocks).

## Output (always)
A proposal object:
```
{ "action": "hold" | "switch",
  "target": "<protocol or null>",
  "spread_bp": <float>, "expected_gain_usd": <float>, "cost_usd": <float>,
  "rationale": "E[gain]=$… vs C=$… (spread … bp, dwell … blocks)" }
```
State plainly: this is a **proposal**; the human must approve before any tx,
and funds never leave their Safe.

## Why this rule (not ML)
The cross-protocol spread is the decision variable; the gas-aware threshold
captures it. A Cox-hazard ML tier was tested and **lost** out-of-sample — we
report that openly. The edge is event-time resolution + a gas throttle, not a
black box. (Solovev, "Event-Time MCDM Allocation across DeFi Lending Protocols".)

## Reference implementation
`defi_allocator/decision.py::T1Allocator.decide` — this skill is the natural-
language contract for that exact code; they must agree.
