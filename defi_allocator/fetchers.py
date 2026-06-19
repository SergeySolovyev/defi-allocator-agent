"""APY data sources for the six USDC supply venues.

Two paths, by design:
  - load_panel(): the committed REAL per-block slice -> deterministic,
    offline, reproducible replay (what the capstone demo + eval use).
  - fetch_live_apys(): a best-effort LIVE snapshot via DefiLlama's public
    yields API (no key) -> what the agent monitors in production. Falls
    back to the last panel row if the network is unavailable.

The six protocols match the paper: Aave V3, Compound V3, Spark, Morpho
Blue, Euler V2, Fluid (USDC supply markets on Ethereum L1).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from defi_allocator.decision import PROTOCOLS

DATA = Path(__file__).resolve().parents[1] / "data" / "sample_panel.parquet"

# DefiLlama project slugs for the USDC supply pool on Ethereum.
LLAMA_PROJECT = {
    "aave_v3": "aave-v3", "compound_v3": "compound-v3", "spark": "spark",
    "morpho_blue": "morpho-blue", "euler_v2": "euler-v2", "fluid": "fluid-lending",
}


def load_panel(path: Path | str = DATA) -> pd.DataFrame:
    """Load the committed real per-block slice used for replay/eval."""
    df = pd.read_parquet(path)
    if "block_timestamp" in df.columns:
        df["block_timestamp"] = pd.to_datetime(df["block_timestamp"], utc=True)
    return df.reset_index(drop=True)


def fetch_live_apys(timeout: float = 12.0) -> dict:
    """Live USDC supply APY per protocol (fraction). Network-best-effort.

    Returns {protocol: apr_fraction}. Missing/unavailable venues are omitted.
    Used by the agent to monitor; the eval/replay use load_panel() instead.
    """
    try:
        import requests
        pools = requests.get("https://yields.llama.fi/pools", timeout=timeout).json()["data"]
    except Exception as exc:  # noqa: BLE001 - network/JSON best effort
        print(f"[fetchers] live fetch failed ({exc!r}); falling back to last panel row")
        return _last_panel_apys()

    want = {v: k for k, v in LLAMA_PROJECT.items()}
    out: dict[str, float] = {}
    for pool in pools:
        if (pool.get("chain") == "Ethereum" and pool.get("symbol", "").upper() == "USDC"
                and pool.get("project") in want):
            proto = want[pool["project"]]
            apy = pool.get("apyBase") if pool.get("apyBase") is not None else pool.get("apy")
            if apy is not None:
                out[proto] = float(apy) / 100.0   # DefiLlama APY is in percent
    if not out:
        return _last_panel_apys()
    return out


def _last_panel_apys() -> dict:
    try:
        row = load_panel().iloc[-1]
        return {p: float(row[f"{p}_lending_apr"]) for p in PROTOCOLS
                if f"{p}_lending_apr" in row.index and pd.notna(row[f"{p}_lending_apr"])}
    except Exception:  # noqa: BLE001
        return {}
