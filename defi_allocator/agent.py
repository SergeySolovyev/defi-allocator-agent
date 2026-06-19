"""The DeFi Lending Allocator Agent (human-in-the-loop).

The agent wraps the deterministic T1 rule (decision.py). It NEVER moves
funds: it MONITORS the six venues, and when T1 says SWITCH it emits a
*proposal* (target, spread, expected gain, cost, rationale) for a human to
approve. Non-custodial by construction.

Optional natural-language explanation comes from Vertex AI (Gemini via the
billed Vertex path — NOT the free Gemini API, which is region-blocked for
this account). If Vertex isn't configured the deterministic rationale is
used verbatim, so the agent always works.
"""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass

from defi_allocator.decision import BlockState, Decision, T1Allocator
from defi_allocator.fetchers import fetch_live_apys

GCP_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "striking-canyon-499613-f3")
GCP_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "europe-west1")
VERTEX_MODEL = os.environ.get("VERTEX_MODEL", "gemini-2.0-flash-001")


@dataclass
class Proposal:
    decision: Decision
    current_protocol: str | None
    position_usd: float
    explanation: str

    def to_dict(self) -> dict:
        d = asdict(self.decision)
        d.update(current_protocol=self.current_protocol, position_usd=self.position_usd,
                 explanation=self.explanation)
        return d


def propose(allocator: T1Allocator, *, position_usd: float,
            current_protocol: str | None, apys: dict | None = None,
            gas_price_gwei: float = 1.0, block_number: int = 0,
            use_vertex: bool = False) -> Proposal:
    """Run one decision and wrap it as a human-reviewable proposal."""
    apys = apys if apys is not None else fetch_live_apys()
    state = BlockState(block_number, apys, gas_price_gwei, current_protocol, position_usd)
    d = allocator.decide(state)
    explanation = d.rationale
    if use_vertex and d.action == "switch":
        explanation = _explain_with_vertex(d, current_protocol, apys) or d.rationale
    return Proposal(d, current_protocol, position_usd, explanation)


def _explain_with_vertex(d: Decision, current: str | None, apys: dict) -> str | None:
    """One-sentence plain-English justification via Vertex AI. Never raises."""
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel
        vertexai.init(project=GCP_PROJECT, location=GCP_LOCATION)
        model = GenerativeModel(VERTEX_MODEL)
        prompt = (
            "You are a non-custodial DeFi treasury assistant. In ONE plain sentence, "
            "explain to a treasurer why to move idle USDC. Be precise, no hype, state it is "
            "a proposal they must approve.\n"
            f"current venue: {current}\nproposed: {d.target}\n"
            f"spread: {d.spread_bp:.1f} bp; expected gain ${d.expected_gain_usd:.0f} > "
            f"switching cost ${d.cost_usd:.0f}; dwell {d.dwell_blocks:.0f} blocks.\n"
            f"live APYs: {{ {', '.join(f'{k}:{v*100:.2f}%' for k, v in apys.items())} }}")
        return model.generate_content(prompt).text.strip()
    except Exception as exc:  # noqa: BLE001 - Vertex optional
        print(f"[agent] Vertex explanation unavailable ({exc!r}); using rule rationale")
        return None


def human_in_the_loop(allocator: T1Allocator, *, position_usd: float = 1_000_000.0,
                      start_protocol: str | None = None, use_vertex: bool = False) -> dict:
    """Interactive single-step: fetch live -> propose -> human approves."""
    p = propose(allocator, position_usd=position_usd, current_protocol=start_protocol,
                gas_price_gwei=1.0, use_vertex=use_vertex)
    print("\n=== ALLOCATOR PROPOSAL ===")
    print(f"  position : ${position_usd:,.0f}  in {start_protocol or '(uninvested)'}")
    print(f"  action   : {p.decision.action.upper()}"
          + (f" -> {p.decision.target}" if p.decision.target else ""))
    print(f"  why      : {p.explanation}")
    if p.decision.action != "switch":
        print("  -> HOLD: nothing to approve.")
        return {"approved": False, **p.to_dict()}
    ans = input("  Approve this SWITCH? [y/N] ").strip().lower()
    approved = ans in ("y", "yes")
    print("  -> " + ("APPROVED — hand calldata to your Safe to sign." if approved
                     else "REJECTED — no action taken."))
    return {"approved": approved, **p.to_dict()}
