"""Cloud Run web UI — human-in-the-loop allocation approval.

GET  /         -> fetches live APYs, runs T1, renders the proposal + approve/reject
POST /decide   -> records the human's decision (the only place a "yes" exists)
GET  /health   -> Cloud Run health check

The service NEVER moves funds. A "yes" only logs intent; signing is the human's
Safe. Natural-language explanation uses Vertex AI if configured (see agent.py).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from defi_allocator.agent import propose
from defi_allocator.decision import PROTOCOLS, T1Allocator
from defi_allocator.fetchers import fetch_live_apys

app = FastAPI(title="DeFi Lending Allocator Agent")
USE_VERTEX = os.environ.get("USE_VERTEX", "0") == "1"
DECISION_LOG: list[dict] = []   # in-memory audit trail (swap for Firestore in prod)


def _page(body: str) -> str:
    return (f"<!doctype html><meta charset=utf-8><title>DeFi Allocator</title>"
            f"<style>body{{font:15px/1.6 system-ui;max-width:720px;margin:2rem auto;padding:0 1rem}}"
            f"code{{background:#f3f3f3;padding:1px 4px;border-radius:4px}}"
            f".sw{{color:#0a7}}.hold{{color:#777}}button{{font-size:15px;padding:8px 16px;"
            f"margin-right:8px;border:1px solid #ccc;border-radius:8px;cursor:pointer}}</style>"
            f"<h2>DeFi Lending Allocator Agent</h2>{body}"
            f"<p style='color:#999;font-size:13px'>Non-custodial proposal engine — "
            f"it never moves funds. Built on Solovev, <i>Event-Time MCDM Allocation "
            f"across DeFi Lending Protocols</i>.</p>")


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def home(position_usd: float = 1_000_000.0, current: str | None = "aave_v3",
         gas_gwei: float = 1.0):
    apys = fetch_live_apys()
    p = propose(T1Allocator(), position_usd=position_usd, current_protocol=current,
                apys=apys, gas_price_gwei=gas_gwei, use_vertex=USE_VERTEX)
    d = p.decision
    rows = "".join(f"<tr><td>{k}</td><td align=right>{v*100:.2f}%</td></tr>"
                   for k, v in sorted(apys.items(), key=lambda kv: -kv[1]))
    if d.action == "switch":
        action_html = (
            f"<p class=sw><b>PROPOSE SWITCH</b>: <code>{current}</code> &rarr; "
            f"<code>{d.target}</code></p><p>{p.explanation}</p>"
            f"<p>spread {d.spread_bp:.1f} bp &nbsp; E[gain] ${d.expected_gain_usd:,.0f} "
            f"&gt; cost ${d.cost_usd:,.0f}</p>"
            f"<form method=post action=/decide>"
            f"<input type=hidden name=target value='{d.target}'>"
            f"<input type=hidden name=current value='{current}'>"
            f"<button name=approve value=yes>✓ Approve (log intent)</button>"
            f"<button name=approve value=no>✗ Reject</button></form>")
    else:
        action_html = f"<p class=hold><b>HOLD</b> — {p.explanation}</p>"
    return _page(f"<p>Position <b>${position_usd:,.0f}</b> in <code>{current}</code> "
                 f"&nbsp;|&nbsp; gas {gas_gwei:.1f} gwei</p>{action_html}"
                 f"<h3>Live supply APYs</h3><table>{rows}</table>")


@app.post("/decide", response_class=HTMLResponse)
def decide(approve: str = Form(...), target: str = Form(...), current: str = Form(...)):
    approved = approve == "yes"
    DECISION_LOG.append({"current": current, "target": target, "approved": approved})
    msg = (f"<p class=sw>✓ Intent logged: move <code>{current}</code> &rarr; "
           f"<code>{target}</code>. Sign it from your Safe — the agent holds no key.</p>"
           if approved else
           f"<p class=hold>✗ Rejected. No action taken.</p>")
    return _page(msg + "<p><a href=/>&larr; back</a></p>")


@app.get("/log")
def log():
    return JSONResponse(DECISION_LOG)
