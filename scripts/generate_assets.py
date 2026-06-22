"""Generate the two required visual assets for the Kaggle submission.

  docs/architecture.png  -> embedded in README (Documentation criterion, 20 pts:
                            "relevant diagrams or images where appropriate").
  docs/cover.png         -> the Media Gallery COVER IMAGE (required to submit
                            the Writeup), 1200x630.

Pure matplotlib (Agg) so it runs headless and commits real raster files.

    python scripts/generate_assets.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

DOCS = Path(__file__).resolve().parents[1] / "docs"
DOCS.mkdir(exist_ok=True)

INK = "#0b1f33"
ACCENT = "#1f6feb"
GOOD = "#1a7f4b"
WARN = "#b54708"
PAPER = "#f6f8fa"


def _box(ax, x, y, w, h, title, body, face, edge):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.06",
                                linewidth=1.6, edgecolor=edge, facecolor=face, zorder=2))
    ax.text(x + w / 2, y + h - 0.16, title, ha="center", va="top",
            fontsize=11, fontweight="bold", color=INK, zorder=3)
    ax.text(x + w / 2, y + h - 0.42, body, ha="center", va="top",
            fontsize=8.4, color=INK, zorder=3, linespacing=1.35)


def _arrow(ax, x0, y0, x1, y1, color=ACCENT):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=16,
                                 linewidth=1.8, color=color, zorder=1))


def architecture() -> None:
    fig, ax = plt.subplots(figsize=(11.0, 5.2), dpi=130)
    ax.set_xlim(0, 11); ax.set_ylim(0, 5.2); ax.axis("off")
    fig.patch.set_facecolor("white")

    ax.text(5.5, 5.0, "DeFi Lending Allocator Agent — architecture", ha="center",
            va="top", fontsize=15, fontweight="bold", color=INK)
    ax.text(5.5, 4.62, "non-custodial · gas-aware · proposes, never moves funds",
            ha="center", va="top", fontsize=9.5, color=ACCENT)

    y, h, w = 2.55, 1.35, 2.32
    _box(ax, 0.20, y, w, h, "Tools · Day 2",
         "live 6-protocol APYs\nDefiLlama (canonical\nmax-TVL, apyBase)\nfetchers.py", PAPER, ACCENT)
    _box(ax, 2.78, y, w, h, "Decision skill · Day 3",
         "T1 rule:\nτ̄·s > (C/V)·BPY\n~50 lines, no ML\ndecision.py", PAPER, ACCENT)
    _box(ax, 5.36, y, w, h, "Safety gate · Day 4",
         "contract-audit skill\n(STRIDE) +\nHUMAN approve/reject", "#fff6ec", WARN)
    _box(ax, 7.94, y, w, h, "Action",
         "PROPOSAL only\nno key that moves\nfunds · to user Safe", "#eafaf0", GOOD)

    for x in (2.52, 5.10, 7.68):
        _arrow(ax, x, y + h / 2, x + 0.26, y + h / 2)

    _box(ax, 2.78, 0.55, 5.48, 1.25, "Eval / observability · Day 4–5",
         "replay T1 vs all 6 passive holds on real per-block data → 5.36% net APY,\n"
         "beats best-in-hindsight venue +0.51pp · size-haircut · audit log\n"
         "replay.py · eval.py", "#f0f4ff", ACCENT)
    _arrow(ax, 3.94, y, 4.6, 1.80, color="#7a8aa0")

    ax.text(5.5, 0.26, "Deployed on Google Cloud Run (Day 1) · Vertex AI natural-language "
            "explanations (graceful-degrade)", ha="center", va="bottom", fontsize=8.5,
            color=INK, style="italic")

    fig.tight_layout(pad=0.4)
    fig.savefig(DOCS / "architecture.png", facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print("wrote", DOCS / "architecture.png")


def cover() -> None:
    fig = plt.figure(figsize=(12.0, 6.30), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
    ax.set_xlim(0, 12); ax.set_ylim(0, 6.3)
    ax.add_patch(plt.Rectangle((0, 0), 12, 6.3, color=INK, zorder=0))
    ax.add_patch(plt.Rectangle((0, 0), 12, 0.18, color=ACCENT, zorder=1))
    ax.add_patch(plt.Rectangle((0, 6.12), 12, 0.18, color=ACCENT, zorder=1))

    ax.text(0.7, 5.05, "DeFi Lending Allocator Agent", fontsize=33, fontweight="bold",
            color="white", va="top")
    ax.text(0.72, 4.18, "Non-custodial, gas-aware USDC rate-router — it proposes a switch,",
            fontsize=15.5, color="#c9d6e5", va="top")
    ax.text(0.72, 3.72, "a human approves. It never moves funds.", fontsize=15.5,
            color="#c9d6e5", va="top")

    chips = [("5.36% net APY", "beats all 6 passive holds"),
             ("6 protocols", "Aave · Compound · Spark\nMorpho · Euler · Fluid"),
             ("human-in-the-loop", "propose → approve/reject")]
    x = 0.7
    for head, sub in chips:
        w = 3.5
        ax.add_patch(FancyBboxPatch((x, 1.55), w, 1.45, boxstyle="round,pad=0.05,rounding_size=0.12",
                                    linewidth=1.4, edgecolor=ACCENT, facecolor="#12304f", zorder=2))
        ax.text(x + w / 2, 2.72, head, ha="center", va="top", fontsize=14.5,
                fontweight="bold", color="white", zorder=3)
        ax.text(x + w / 2, 2.28, sub, ha="center", va="top", fontsize=9.6,
                color="#9fb3c8", zorder=3, linespacing=1.3)
        x += w + 0.35

    ax.text(0.72, 0.78, "Google × Kaggle · 5-Day AI Agents: Intensive Vibe Coding — Capstone",
            fontsize=12.5, color="#7f97b0", va="center")
    ax.text(11.3, 0.78, "Sergei Solovev · WorldQuant University", fontsize=11,
            color="#7f97b0", va="center", ha="right")

    fig.savefig(DOCS / "cover.png", facecolor=INK)
    plt.close(fig)
    print("wrote", DOCS / "cover.png")


if __name__ == "__main__":
    architecture()
    cover()
