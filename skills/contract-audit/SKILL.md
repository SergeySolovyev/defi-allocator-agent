---
name: contract-audit
description: >
  Sanity-check the on-chain target lending contract BEFORE proposing a SWITCH
  into it. Use right after allocation-decision returns action=switch, as a
  safety gate in the human-in-the-loop flow.
---

# Skill: contract-audit (pre-switch safety gate)

Before the agent proposes moving USDC into a venue, verify the target is safe.
This is a *gate*, not advice: if any check fails, downgrade the proposal to
HOLD and tell the human why.

## Checks (per proposed target protocol)
1. **Known address** — the target's market/pool address is on the project's
   allow-list (the six audited venues only). Reject anything not allow-listed.
2. **Liveness & depth** — the venue's USDC market is active and its TVL is large
   enough to absorb the position without an outsized rate impact (flag if the
   position exceeds ~10–25% of the venue's USDC supply — the thin-venue ceiling).
3. **Peg / anomaly** — USDC is within peg tolerance and no utilization/exploit
   anomaly is flagging on the target (peg dev < ~50 bp; utilization not pinned
   at 100%).
4. **Rate sanity** — the proposed APR is within a plausible band (e.g. 0–30%);
   reject obviously spoofed/oracle-glitched rates.

## Output
```
{ "target": "<protocol>", "verdict": "pass" | "block",
  "reasons": ["..."],
  "size_warning": "<position is N% of venue USDC TVL>" | null }
```
On `block`, the orchestrator MUST present HOLD to the human instead of SWITCH.

## STRIDE note (course Day 4)
Maps to **Tampering / Information-disclosure / Denial-of-service** on the data
path: a spoofed APY (T) or a thin-pool sandwich (D) would otherwise drive a bad
SWITCH. This gate + the human approval + Flashbots private execution are the
mitigations. Funds are non-custodial throughout (no Elevation-of-privilege: the
agent never holds a key that can move funds).
