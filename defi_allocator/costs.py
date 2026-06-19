"""Switching-cost model for the DeFi lending allocator.

C = gas + slippage + MEV   (per the paper, §III "Switching cost model")

  gas_cost   = G * gas_price_wei * eth_price_usd / 1e18      (USD)
  slippage   = V * delta_slip_bp / 1e4                       (USD)
  mev        = V * delta_mev_bp  / 1e4                       (USD)

where G ~= 200_000 is the rebalance gas, V the position size in USD.
For retail/mid sizes slippage is ~0.01-0.1 bp and second-order vs gas;
MEV is bounded above by the Flashbots private-mempool path (so 0 by
default here, disclosed as a modelling choice).

Reference: Solovev, "Event-Time MCDM Allocation across DeFi Lending
Protocols" (WorldQuant University), §III.
"""
from __future__ import annotations

from dataclasses import dataclass

GAS_USED_PER_REBALANCE = 200_000     # typical supply+withdraw rebalance tx
DEFAULT_ETH_PRICE_USD = 3_500.0


@dataclass(frozen=True)
class CostParams:
    gas_used: int = GAS_USED_PER_REBALANCE
    slippage_bp: float = 0.0          # per-fill slippage in basis points
    mev_bp: float = 0.0               # Flashbots-protected => ~0 by default
    eth_price_usd: float = DEFAULT_ETH_PRICE_USD


def switching_cost_usd(position_usd: float, gas_price_gwei: float,
                       params: CostParams = CostParams()) -> float:
    """Total cost C (USD) of one A->B rebalance: gas + slippage + MEV."""
    gas = params.gas_used * (gas_price_gwei * 1e9) * params.eth_price_usd / 1e18
    slip = position_usd * params.slippage_bp / 1e4
    mev = position_usd * params.mev_bp / 1e4
    return gas + slip + mev
