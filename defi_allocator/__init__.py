"""DeFi Lending Allocator Agent — a non-custodial, gas-aware USDC rate router.

Capstone for the Google x Kaggle "5-Day AI Agents: Intensive Vibe Coding"
course, built on the paper "Event-Time MCDM Allocation across DeFi Lending
Protocols" (Sergei Solovev, WorldQuant University).
"""
from defi_allocator.decision import BlockState, Decision, T1Allocator, PROTOCOLS
from defi_allocator.replay import replay, PassiveHold, ReplayResult
from defi_allocator.eval import evaluate, format_report

__all__ = ["BlockState", "Decision", "T1Allocator", "PROTOCOLS",
           "replay", "PassiveHold", "ReplayResult", "evaluate", "format_report"]
__version__ = "0.1.0"
