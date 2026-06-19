"""Event-time replay engine: run a policy block-by-block over a panel.

Accrues the held protocol's APR each block, deducts the switching cost on
executed switches, and records the equity + allocation trajectory. O(1)
state per block (no history kept), so it scales to millions of blocks.

Kyle batch-auction semantic: one block = one batch; the APR observed AT a
block is the rate paid during that block (paper §"replay engine").
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from defi_allocator.costs import CostParams, switching_cost_usd
from defi_allocator.decision import BlockState, BLOCKS_PER_YEAR, PROTOCOLS, T1Allocator


@dataclass(frozen=True)
class ReplayResult:
    policy: str
    n_blocks: int
    years: float
    n_switches: int
    gas_usd: float
    final_usd: float
    net_apy_pct: float
    trajectory: pd.DataFrame    # block_number, ts, position_usd, current_protocol


def _apr_dict(row) -> dict:
    """Per-protocol APR for this block, NaN-filtered (a missing rate accrues
    nothing, never poisons the position with NaN)."""
    out = {}
    for p in PROTOCOLS:
        c = f"{p}_lending_apr"
        if c in row.index:
            v = float(row[c])
            if v == v:                      # not NaN
                out[p] = v
    return out


def replay(panel: pd.DataFrame, policy, *, position_usd: float = 1_000_000.0,
           cost_params: CostParams = CostParams()) -> ReplayResult:
    """Replay `policy` (anything with .decide(BlockState)->Decision) over panel.

    Piecewise-constant accrual: between two observed blocks the held rate is
    constant, so we accrue the previously-observed rate over the elapsed
    block gap. This makes a DOWNSAMPLED panel give the same APY as the full
    per-block panel (only the decision cadence coarsens, not the accounting).
    """
    pos = position_usd
    current = None
    gas_total = 0.0
    n_switch = 0
    blk, eq, cur = [], [], []
    prev_block: int | None = None
    prev_rate: float | None = None          # current protocol's rate, observed at prev block

    for _, row in panel.iterrows():
        b = int(row["block_number"])
        apr = _apr_dict(row)
        if prev_block is not None and prev_rate is not None:
            pos *= (1 + prev_rate * (b - prev_block) / BLOCKS_PER_YEAR)   # accrue the gap
        state = BlockState(b, apr, float(row["gas_price_gwei"]), current, pos)
        d = policy.decide(state)
        if d.action == "switch":
            pos -= switching_cost_usd(pos, state.gas_price_gwei, cost_params)
            gp = state.gas_price_gwei                          # track the gas leg for reporting
            gas_total += cost_params.gas_used * (gp * 1e9) * cost_params.eth_price_usd / 1e18
            n_switch += 1
            current = d.target
        prev_block = b
        prev_rate = apr.get(current)        # rate to accrue over the NEXT gap (None if missing)
        blk.append(b); eq.append(pos); cur.append(current)

    n = len(blk)
    span = (blk[-1] - blk[0]) if n > 1 else n
    years = max(span / BLOCKS_PER_YEAR, 1e-9)
    net_apy = ((pos / position_usd) ** (1 / years) - 1) * 100 if pos > 0 else -100.0
    traj = pd.DataFrame({"block_number": blk, "position_usd": eq, "current_protocol": cur})
    if "block_timestamp" in panel.columns:
        traj["ts"] = panel["block_timestamp"].values
    name = getattr(policy, "name", type(policy).__name__)
    return ReplayResult(name, n, years, n_switch, round(gas_total, 2), round(pos, 2),
                        round(net_apy, 4), traj)


class PassiveHold:
    """Buy-and-hold one protocol (the benchmark the agent must beat)."""
    def __init__(self, protocol: str):
        self.protocol = protocol
        self.name = f"hold_{protocol}"

    def decide(self, state: BlockState):
        from defi_allocator.decision import Decision
        if state.current_protocol == self.protocol:
            return Decision("hold", None, 0, 0, 0, 0, "passive")
        return Decision("switch", self.protocol, 0, 0, 0, 0, "cold start")
