"""Unit tests for the T1 decision rule, cost model, and replay."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from defi_allocator.costs import CostParams, switching_cost_usd
from defi_allocator.decision import BLOCKS_PER_YEAR, BlockState, PROTOCOLS, T1Allocator
from defi_allocator.replay import PassiveHold, replay


def test_gas_cost_scales_with_price():
    c10 = switching_cost_usd(1_000_000, 10.0)
    c100 = switching_cost_usd(1_000_000, 100.0)
    assert c100 == pytest.approx(c10 * 10, rel=1e-6)       # gas leg is linear in gwei


def test_cold_start_invests():
    a = T1Allocator()
    s = BlockState(0, {"aave_v3": 0.03, "euler_v2": 0.05}, 1.0, None, 1_000_000)
    d = a.decide(s)
    assert d.action == "switch" and d.target == "euler_v2"


def test_switch_only_when_gain_beats_cost():
    a = T1Allocator()
    a.dwell_blocks = 1000.0
    # tiny spread, expensive gas -> HOLD
    s_hold = BlockState(1, {"aave_v3": 0.0300, "euler_v2": 0.0301}, 300.0, "aave_v3", 100_000)
    assert a.decide(s_hold).action == "hold"
    # big spread, cheap gas, large position -> SWITCH
    s_sw = BlockState(2, {"aave_v3": 0.03, "euler_v2": 0.08}, 0.3, "aave_v3", 5_000_000)
    assert a.decide(s_sw).action == "switch"


def test_nan_rate_never_poisons_replay():
    # Compound has a data gap (NaN) mid-window; passive-hold must NOT go to -100%.
    n = 5000
    rows = []
    for i in range(n):
        comp = float("nan") if 1000 <= i < 2000 else 0.03
        rows.append({"block_number": i * 5, "gas_price_gwei": 0.3,
                     "aave_v3_lending_apr": 0.03, "compound_v3_lending_apr": comp,
                     "spark_lending_apr": 0.03, "morpho_blue_lending_apr": 0.03,
                     "euler_v2_lending_apr": 0.03, "fluid_lending_apr": 0.03})
    panel = pd.DataFrame(rows)
    r = replay(panel, PassiveHold("compound_v3"), position_usd=1_000_000)
    assert r.net_apy_pct > 0          # not -100%
    assert r.final_usd > 900_000


def test_t1_beats_worst_hold_on_synthetic_crossover():
    # euler pays more in the 2nd half -> an active allocator should beat holding aave.
    n, half = 8000, 4000
    rows = []
    for i in range(n):
        eul = 0.03 if i < half else 0.09
        rows.append({"block_number": i * 5, "gas_price_gwei": 0.3,
                     "aave_v3_lending_apr": 0.03, "compound_v3_lending_apr": 0.02,
                     "spark_lending_apr": 0.02, "morpho_blue_lending_apr": 0.02,
                     "euler_v2_lending_apr": eul, "fluid_lending_apr": 0.02})
    panel = pd.DataFrame(rows)
    t1 = replay(panel, T1Allocator(), position_usd=1_000_000)
    hold_aave = replay(panel, PassiveHold("aave_v3"), position_usd=1_000_000)
    assert t1.net_apy_pct > hold_aave.net_apy_pct
    assert t1.n_switches >= 1


def test_blocks_per_year_constant():
    assert BLOCKS_PER_YEAR == 365 * 24 * 60 * 60 // 12
