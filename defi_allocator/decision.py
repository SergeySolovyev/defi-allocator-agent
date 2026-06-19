"""T1 — gas-aware threshold allocation rule (the capstone's decision core).

This is the ~50-line, no-ML rule from the paper. It is deliberately a
deterministic closed form: the agent wraps it, but the *decision* is
auditable and reproducible — the moat is honesty, not a black box.

Decision rule (paper §III, "Three-level decision policy", T1):

    SWITCH to j  iff   tau_bar_ewma * s_ij  >  (C / V) * BLOCKS_PER_YEAR

  s_ij           = best_apr - current_apr        (cross-protocol spread, F3)
  tau_bar_ewma   = EWMA of inter-crossover dwell  (expected blocks the
                   current leader stays best)
  C              = switching cost in USD (costs.switching_cost_usd)
  V              = position size in USD
  BLOCKS_PER_YEAR= 365*24*3600 / 12  (12 s post-Merge Ethereum block)

Equivalently, expected extra yield over the dwell beats the cost:
    V * s_ij * tau_bar / BLOCKS_PER_YEAR  >  C.

The EWMA dwell is the ONLY state; everything else is the live block.
Reference: Solovev, "Event-Time MCDM Allocation across DeFi Lending
Protocols" (WorldQuant University).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from defi_allocator.costs import CostParams, switching_cost_usd

BLOCKS_PER_YEAR = 365 * 24 * 60 * 60 // 12  # 2_628_000

PROTOCOLS = ("aave_v3", "compound_v3", "spark", "morpho_blue", "euler_v2", "fluid")


@dataclass(frozen=True)
class BlockState:
    """One block's decision input."""
    block_number: int
    lending_apr: dict          # protocol -> supply APR (fraction, e.g. 0.05)
    gas_price_gwei: float
    current_protocol: str | None
    position_usd: float


@dataclass(frozen=True)
class Decision:
    action: str                # "hold" | "switch"
    target: str | None
    spread_bp: float
    dwell_blocks: float
    expected_gain_usd: float
    cost_usd: float
    rationale: str


@dataclass
class T1Allocator:
    """Gas-aware threshold allocator. Stateful only in the dwell EWMA."""
    ewma_alpha: float = 1.0 / 10.0            # ~10-observation half-life
    initial_dwell_blocks: float = 1_000.0     # ~3.3 h prior
    cost_params: CostParams = field(default_factory=CostParams)

    dwell_blocks: float = field(init=False)
    _last_winner: str | None = field(init=False, default=None)
    _last_winner_block: int | None = field(init=False, default=None)

    def __post_init__(self):
        self.dwell_blocks = float(self.initial_dwell_blocks)

    def _update_dwell(self, state: BlockState) -> None:
        valid = {p: a for p, a in state.lending_apr.items() if not _nan(a)}
        if not valid:
            return
        winner = max(valid, key=valid.get)
        if self._last_winner is None:
            self._last_winner, self._last_winner_block = winner, state.block_number
            return
        if winner != self._last_winner:
            gap = state.block_number - (self._last_winner_block or state.block_number)
            self.dwell_blocks = self.ewma_alpha * gap + (1 - self.ewma_alpha) * self.dwell_blocks
            self._last_winner, self._last_winner_block = winner, state.block_number

    def decide(self, state: BlockState) -> Decision:
        self._update_dwell(state)
        valid = {p: a for p, a in state.lending_apr.items() if not _nan(a)}
        if not valid:
            return Decision("hold", None, 0.0, self.dwell_blocks, 0.0, 0.0, "no APR data")

        best = max(valid, key=valid.get)
        best_apr = valid[best]

        if state.current_protocol is None:               # cold start
            return Decision("switch", best, 0.0, self.dwell_blocks, 0.0, 0.0,
                            f"cold start -> {best} @ {best_apr*100:.2f}%")
        if best == state.current_protocol:
            return Decision("hold", None, 0.0, self.dwell_blocks, 0.0, 0.0,
                            f"already at best ({best_apr*100:.2f}%)")

        cur_apr = valid.get(state.current_protocol, float("nan"))
        if _nan(cur_apr):
            return Decision("switch", best, 0.0, self.dwell_blocks, 0.0, 0.0,
                            "current protocol APR is NaN -> switch defensively")

        spread = best_apr - cur_apr                      # > 0 by construction
        expected_gain = state.position_usd * spread * self.dwell_blocks / BLOCKS_PER_YEAR
        cost = switching_cost_usd(state.position_usd, state.gas_price_gwei, self.cost_params)

        if expected_gain > cost:
            return Decision("switch", best, spread * 1e4, self.dwell_blocks,
                            expected_gain, cost,
                            f"E[gain]=${expected_gain:.2f} > C=${cost:.2f} "
                            f"(spread {spread*1e4:.1f}bp, dwell {self.dwell_blocks:.0f}b) "
                            f"-> {state.current_protocol}->{best}")
        return Decision("hold", None, spread * 1e4, self.dwell_blocks, expected_gain, cost,
                        f"E[gain]=${expected_gain:.2f} < C=${cost:.2f}; hold "
                        f"{state.current_protocol} (gas {state.gas_price_gwei:.1f} gwei)")


def _nan(x) -> bool:
    try:
        return math.isnan(float(x))
    except (TypeError, ValueError):
        return True
