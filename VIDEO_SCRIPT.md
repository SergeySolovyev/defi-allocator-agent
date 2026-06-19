# Capstone video script (~3–4 min)

A tight, demo-led script. Screen-record while you talk. Show the live service,
then the code, then the result.

---

**0:00–0:30 — Hook + problem.**
"Crypto treasuries leave idle USDC parked in one lending venue while another pays
more. Watching six protocols and deciding when a switch beats the gas cost is a
repetitive, high-value job. I built a non-custodial agent that does it — and never
moves your funds." → show the live page.

**0:30–1:30 — Live demo (the agent).**
Open `https://defi-allocator-1038590668771.europe-west1.run.app`.
"It fetches live supply APYs across Aave, Compound, Spark, Morpho, Euler, Fluid — the
canonical pool per venue, base rate net of incentives — runs my decision rule, and
*proposes* a switch, here aave_v3 → morpho_blue, where the expected gain over the
expected dwell beats the gas cost. It does NOT execute: a human Approves or Rejects."
"And before any funds move it runs a contract-audit skill on the target venue — a
higher rate is a reason to scrutinise contract risk, not to trust it blindly."
Click **Reject** to show it logs intent only.

**1:30–2:15 — The rule (why no black box).**
Open `defi_allocator/decision.py`. "The decision is a deterministic 50-line rule from
my research paper: switch only when the spread times the expected dwell beats the gas
cost. I even tested an ML tier — Cox hazards — and it LOST out of sample. I report
that openly. Honesty is the moat."

**2:15–2:50 — Architecture → course days.**
Show the README table. "Tools (day 2) fetch the rates; a Skill (day 3) is the
allocation rule; a contract-audit Skill and human approval (day 4) are the safety
gates; eval and observability (day 4–5) compare against passive holds; and it's
deployed to Cloud Run (day 1). Explanations use Vertex AI, since the free Gemini API
is region-blocked for me."

**2:50–3:30 — Result + close.**
Run `python scripts/run_replay_demo.py`. "On real per-block data, the agent earns
5.36% — beating every passive hold, including the best venue in hindsight, by half a
point — net of real gas. And it honestly shows the edge shrinking at larger sizes.
Code and live service are linked in the writeup. Thanks!"

---
**Capture checklist:** live page (with a Reject click) · decision.py · README table ·
the replay-demo terminal output. Keep it under 4 minutes.
