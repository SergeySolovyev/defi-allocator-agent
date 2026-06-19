"""Evaluation: the T1 allocator vs every passive single-protocol hold.

The honest benchmark is NOT "beat the market" — it is "beat passively
parking USDC in any one venue, net of gas". This module runs the
allocator + the six passive holds over the same panel and reports the
edge, the time-share, and the per-size slippage haircut so the number is
defensible to a quant reader (matches the paper's honesty posture).
"""
from __future__ import annotations

import pandas as pd

from defi_allocator.decision import PROTOCOLS, T1Allocator
from defi_allocator.replay import PassiveHold, ReplayResult, replay

# IRM kink slopes for the continuous size-haircut (Krause 2005), per the paper.
IRM_SLOPE = {"aave_v3": 0.04, "compound_v3": 0.05, "spark": 0.04,
             "morpho_blue": 0.06, "euler_v2": 0.05, "fluid": 0.05}
PRETTY = {"aave_v3": "Aave V3", "compound_v3": "Compound V3", "spark": "Spark",
          "morpho_blue": "Morpho Blue", "euler_v2": "Euler V2", "fluid": "Fluid"}


def evaluate(panel: pd.DataFrame, *, position_usd: float = 1_000_000.0) -> dict:
    """Run T1 + all passive holds; return a structured comparison."""
    t1 = replay(panel, T1Allocator(), position_usd=position_usd)
    holds = {p: replay(panel, PassiveHold(p), position_usd=position_usd)
             for p in PROTOCOLS if f"{p}_lending_apr" in panel.columns}

    best_hold = max(holds.values(), key=lambda r: r.net_apy_pct)
    worst_hold = min(holds.values(), key=lambda r: r.net_apy_pct)
    ts = (t1.trajectory["current_protocol"].value_counts(normalize=True) * 100).round(1)

    return {
        "position_usd": position_usd,
        "t1": t1,
        "holds": holds,
        "best_hold": best_hold,
        "worst_hold": worst_hold,
        "edge_vs_best_hold_pp": round(t1.net_apy_pct - best_hold.net_apy_pct, 3),
        "edge_vs_worst_hold_pp": round(t1.net_apy_pct - worst_hold.net_apy_pct, 3),
        "time_share_pct": {PRETTY.get(k, k): float(v) for k, v in ts.items()},
        "size_haircut": _size_haircut(panel, ts, t1.net_apy_pct, best_hold.net_apy_pct),
    }


def _size_haircut(panel, ts, gross_active_apy, passive_apy,
                  sizes=(500_000.0, 2_000_000.0, 5_000_000.0)) -> list:
    """Continuous slippage haircut at several sizes (Krause 2005), weighted by
    the policy's time-share. Honest answer to 'does YOUR size eat the edge?'."""
    means = {}
    for pretty, share in ts.items():
        p = next((k for k, v in PRETTY.items() if v == pretty), pretty)
        tcol, ucol = f"{p}_tvl_usd", f"{p}_utilization"
        if tcol in panel.columns and ucol in panel.columns:
            tvl = float(pd.to_numeric(panel[tcol], errors="coerce").mean())
            util = float(pd.to_numeric(panel[ucol], errors="coerce").mean())
            if tvl > 0 and 0 < util < 1:
                means[p] = (tvl, util, share / 100.0)
    out = []
    for V in sizes:
        impact_bp = sum(sh * 0.5 * IRM_SLOPE.get(p, 0.05) * u * V / (tvl + V) * 1e4
                        for p, (tvl, u, sh) in means.items())
        net = gross_active_apy - impact_bp / 100.0
        out.append({"size_usd": V, "slippage_bp": round(impact_bp, 1),
                    "net_active_apy_pct": round(net, 3),
                    "net_edge_pp": round(net - passive_apy, 3)})
    return out


def format_report(ev: dict) -> str:
    t1: ReplayResult = ev["t1"]
    lines = [
        "DeFi Lending Allocator — replay evaluation",
        f"  position           ${ev['position_usd']:,.0f}",
        f"  window             {t1.n_blocks:,} blocks (~{t1.years:.2f} yr)",
        f"  T1 net APY         {t1.net_apy_pct:.2f}%   "
        f"({t1.n_switches} switches, ${t1.gas_usd:,.0f} gas)",
        "  passive holds:",
    ]
    for p, r in sorted(ev["holds"].items(), key=lambda kv: -kv[1].net_apy_pct):
        lines.append(f"    {PRETTY.get(p, p):<14s} {r.net_apy_pct:6.2f}%")
    lines += [
        f"  edge vs best hold  {ev['edge_vs_best_hold_pp']:+.2f} pp "
        f"({PRETTY.get(ev['best_hold'].policy.replace('hold_',''), ev['best_hold'].policy)})",
        f"  edge vs worst hold {ev['edge_vs_worst_hold_pp']:+.2f} pp",
        "  time-share: " + ", ".join(f"{k} {v:.0f}%" for k, v in ev["time_share_pct"].items()),
        "  size haircut (net-of-slippage edge vs best hold):",
    ]
    for r in ev["size_haircut"]:
        lines.append(f"    ${r['size_usd']/1e6:>4.1f}M  slip {r['slippage_bp']:>5.1f}bp "
                     f"-> net active {r['net_active_apy_pct']:.2f}%  edge {r['net_edge_pp']:+.2f}pp")
    return "\n".join(lines)
