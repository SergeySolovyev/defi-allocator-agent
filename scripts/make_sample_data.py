"""Export a compact REAL per-block slice for the committed demo dataset.

Reads the full research panel (the 3.9M-block 6-protocol parquet that backs
the paper) and writes a small, git-committable slice: the six USDC supply
APRs + utilization + TVL + gas, over the held-out test window, downsampled
to keep the file small while preserving the event-time switching behaviour.

This script is run ONCE by the author (the full panel is not shipped); the
resulting data/sample_panel.parquet is what the repo ships and the demo uses.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

# the full research panel on the author's machine (NOT shipped)
SOURCE = Path(r"D:/DeFi/predictive-mcdm-defi/data/cached/per_block_panel.parquet")
OUT = Path(__file__).resolve().parents[1] / "data" / "sample_panel.parquet"
PROTOCOLS = ("aave_v3", "compound_v3", "spark", "morpho_blue", "euler_v2", "fluid")
STEP = 5             # keep every 5th block (~1 min) -> committable, near-faithful cadence


def main() -> int:
    if not SOURCE.exists():
        print(f"source panel not found: {SOURCE} (author-only step)"); return 1
    df = pd.read_parquet(SOURCE)
    df["block_timestamp"] = pd.to_datetime(df["block_timestamp"], utc=True)
    win = df[(df.block_timestamp >= "2026-01-01") & (df.block_timestamp < "2026-05-01")]
    keep = ["block_number", "block_timestamp", "gas_price_gwei"]
    keep += [c for c in df.columns
             if any(c == f"{p}_{s}" for p in PROTOCOLS for s in ("lending_apr", "utilization", "tvl_usd"))]
    slim = win[keep].iloc[::STEP].reset_index(drop=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    slim.to_parquet(OUT, index=False, compression="zstd")
    mb = OUT.stat().st_size / 1e6
    print(f"wrote {OUT}  ({len(slim):,} rows, {mb:.2f} MB, {slim.block_timestamp.min().date()}"
          f"..{slim.block_timestamp.max().date()})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
