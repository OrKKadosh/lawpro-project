# Which summarizer should LawPro ship?

This is the written recommendation. It cites `results/` directly — every number below is reproducible from a committed file without spending anything or rerunning code. Methodology and rationale live in `PLAN.md`/`DECISIONS.md`; concrete data findings live in `FINDINGS.md`.

## Headline answer

**There is no single "ship tool X" recommendation, and that is itself the correct, evidence-based conclusion, not a hedge.** The brief and the data are explicit that A/B/C/D are not stable identifiers across cases (`CLAUDE.md`; confirmed empirically — see "Why no global answer" below). What the evidence actually supports is a **per-case** recommendation:

| Case | Ship | Confidence | Runner-up |
|---|---|---|---|
| **case-vance** | **D** | High | None close — D is the only tool that passes the faithfulness gate at all |
| **case-davis** | **A** | Moderate-high | D (very close, marginally lower faithfulness, perfect stability) |

Both recommendations come from `results/final_scorecard.md`, produced by a controlled benchmark that never depended on our own document-extraction pipeline's quality (`PLAN.md` §2) — so this recommendation is not at risk from anything found or fixed in that pipeline this session.

## The evidence

Every one of the 16 pre-generated summaries (8 per case: 4 tools × 2 runs) was decomposed into atomic factual claims and checked against the exact timeline that tool was given, by an LLM judge whose structured output (claim status, severity tier, cited evidence) is scored by deterministic code — the judge proposes, the code decides the number (`DECISIONS.md`, `evalkit/scoring.py`). The one rule that decides ship-eligibility above everything else: **a single confirmed critical-tier claim (a fabricated fact, a hedge flattened into certainty, a wrong body site, a false attribution) fails the tool outright, regardless of how good its other sentences are.** This rule was sanity-checked against two independently-verified planted errors before being trusted on real results, and it worked — it caught both.

### case-vance

| Tool | Faithfulness | Ship-eligible | Coverage | Usefulness | Stability |
|---|---|---|---|---|---|
| A | 0.896 | **No** | 0.892 | 4.14 | 1.00 |
| B | 0.736 | **No** | 0.869 | 4.21 | 0.72 |
| C | 0.817 | **No** | 0.489 | 3.79 | 0.60 |
| **D** | **0.992** | **Yes** | **0.938** | **4.64** | 0.91 |

A and B both take Dr. Foster's hedged "unclear onset, possibly preexisting" finding and state it as a settled fact shared confidently by both physicians — exactly the overclaimed-tier failure the gate exists to catch, and material here specifically because it bears on causation/pre-existing-condition arguments in an MVA case. C fails the gate too, and separately covers under half of the material facts (0.489) — it both fabricates and under-covers. D is not a marginal winner: it has the best score on every axis measured, not just the one that gates it.

**One caveat, checked rather than smoothed over:** D's two runs disagree on whether Dr. Foster personally performed the surgery or only arranged the consultation. Checked directly against the timeline — the stronger claim (run 1) is the one the source actually supports; run 2 is the one that quietly hedges away an attribution the timeline states plainly. This is a real stability weakness, not a faithfulness violation in either individual run, and it's the reason confidence is "high" rather than "very high."

### case-davis

| Tool | Faithfulness | Ship-eligible | Coverage | Usefulness | Stability |
|---|---|---|---|---|---|
| **A** | **0.954** | **Yes** | **0.872** | 3.93 | 0.94 |
| B | 0.727 | **No** | 0.792 | 4.36 | 0.81 |
| C | 0.863 | **Yes** | 0.574 | 3.79 | 0.92 |
| D | 0.923 | **Yes** | 0.848 | 3.93 | **1.00** |

Three of four pass the gate here, which is itself informative — Davis's summaries are more uniformly faithful than Vance's, plausibly because Davis's benchmark timeline (`input_timeline.json`, shipped directly rather than independently audited) had fewer of the ambiguous, hedge-laden findings that tripped up Vance's tools. B fails on two contradicted claims: a wrong cervical disc level and a fabricated provider name that appears nowhere in the timeline.

Among the three that pass, **A** has the best faithfulness and the best coverage. **D** is a legitimate, very close alternative — marginally lower faithfulness (0.923 vs 0.954) but perfect run-to-run stability (1.00 vs 0.94). **C** is dramatically cheaper ($0.0046 vs $0.02+ per summary) but covers barely half the material facts (0.574) — a real trade-off if cost mattered more than it does here, but at these absolute costs (a few cents either way) it doesn't. A is the recommendation; D is the one worth keeping as a fallback if A's stability edge turns out to matter more in a larger sample.

## Why no global answer

This isn't a methodological hedge — it was checked, not assumed. Two independent things support treating A/B/C/D as case-local:
1. The brief and `CLAUDE.md` state it directly as a non-negotiable constraint.
2. The performance profiles themselves don't line up in a way that would suggest a shared identity: Vance's D is a clear standout on every metric with no close competitor; Davis's D is a strong-but-not-top performer with three tools in real contention. If "D" meant the same underlying model in both cases, this is a plausible but not decisive pattern either way — which is exactly why the identifier is deliberately not treated as meaningful across cases, rather than inferring from suggestive-but-inconclusive score patterns.

## Confidence levels, stated plainly

- **case-vance → D: High.** The gate result is decisive (only tool to pass, by a wide margin on every secondary metric too), and the gate mechanism itself was validated against two independently-confirmed planted errors before being trusted. The one thing keeping this from "very high": stability was only checked pairwise (n=2 runs), and D's own pair showed one real disagreement. Worth naming plainly, not just implying via the general "two cases, no held-out validation set" limitation below: the severity-tier weights and critical-error gate were calibrated using two source-verified examples, both drawn from this same case — so "high" confidence should be read as high *within what a two-case, self-calibrated rubric can support*, not as independent confirmation from a rubric tuned elsewhere. This doesn't change the recommendation itself (the gate result was also confirmed against facts independent of the calibration examples, e.g. B's run-2 fabricated values), but the calibration-set/scoring-set overlap is a real, specific reason for some caution, not just an abstract one.
- **case-davis → A: Moderate-high.** A wins clearly on the two metrics that matter most (faithfulness, coverage), but the field is genuinely close — three tools pass the gate, and D's perfect stability is a real, not token, advantage that a larger sample could tip the balance on.

## What would change this recommendation

Stated concretely, not as a generic caveat:

1. **More than 2 runs per tool.** Pairwise stability with n=2 is real evidence but not a statistical claim (`DECISIONS.md`). A wider sample could change Davis's A-vs-D call, or surface a stability problem in Vance's D that a single disagreeing pair only hints at.
2. **Independent confirmation of Vance's exact input.** The claim that golden was the literal input behind Vance's 8 summaries rests on the hiring contact's word, not a repo artifact the way Davis's `input_timeline.json` is (`FINDINGS.md`, documented as a known limitation from the start). If that turned out to be wrong, Vance's entire controlled-benchmark comparison would need re-grounding against whatever the real input was.
3. **Confirmation of whether A/B/C/D really are (or aren't) the same backends across cases.** If LawPro can state definitively that the same four tools are used for every case (just relabeled), a genuine cross-case aggregate becomes possible and could change which tool gets recommended as a single default — right now that data simply doesn't exist to check.
4. **Real production cases beyond these two synthetic ones.** Every fix and every conclusion this session is grounded in exactly two test cases, both read repeatedly while debugging. That's a real, acknowledged limitation on how far any of this generalizes (`DECISIONS.md`) — not disqualifying, since the mechanism (severity-tiered faithfulness checking against a timeline) is a general one, but the specific numbers above should be read as "this is what these two cases show," not "this is proven to hold everywhere."
5. **Hardening the extraction-to-summarize handoff.** A real end-to-end run (`results/pipeline_demo_case-vance.json`, `case-davis.json`) fed our own extracted timeline — not golden — into each case's winning tool, and both failed the faithfulness gate on that uncontrolled run. Both failures were verified as real, not scoring artifacts: a hedge our own extraction correctly preserved ("provider disputed across sources") got flattened into certainty by the summarizer, and a real numeric detail got stated wrong. This doesn't change which tool to ship — the controlled benchmark exists specifically so this can't contaminate that decision — but it's a concrete signal that shipping requires more than picking the right tool: the extraction pipeline's own output needs work specifically on how it phrases disputed/hedged facts before a summarizer is trusted to preserve that nuance downstream.

## Cost

Not a factor in either recommendation. Every tool in both cases costs a few cents per summary (`results/final_scorecard.md`) — even the cheapest (`case-davis` tool C at $0.0046) versus the most expensive (`case-vance` tool D at $0.0296) is a difference measured in cents, not dollars, at any realistic volume. If faithfulness were tied, cost would be the tiebreaker; it never came to that here.

## What was deliberately not built, and why

Documented as scope decisions, not omissions (`PLAN.md` §17, `DECISIONS.md`):
- No default re-reading of original scanned PDFs — OCR is trusted by default, escalated to PDF only when something looks corrupted or ambiguous.
- No row-by-row audit of every routine timeline event — full coverage for high-materiality events, a documented deterministic sample for routine ones.
- The optional sparse-input adversarial probe (`PLAN.md` §11) was scoped but not run — low marginal value against the budget/time it would cost, and the faithfulness gate was already validated against two real planted errors without it.
- Visual polish on the application interface — explicitly out of scope per the brief.

## Reproducing this

- `results/final_scorecard.md` — the table this recommendation is built from.
- `results/controlled_benchmark_case-vance.json`, `case-davis.json` — every atomic claim, its evidence, and its verdict, for every summary.
- `results/timeline_eval/case-vance.json`, `case-davis.json` — our own extraction pipeline's independently-audited accuracy (91-94% source-grounded precision), kept structurally separate from this recommendation.
- `results/pipeline_demo_case-vance.json`, `case-davis.json` — the uncontrolled end-to-end demo referenced above.
- `tests/` — 33 tests, no live API calls, covering every deterministic scoring and extraction-logic claim made in this document.
- A field-level guide to reading all of the above, with real excerpts, is available as a published artifact from this session (see conversation history) and as `results/conflict_review_case-vance.md`, `case-davis.md` for the extraction pipeline's own decision log in plain English.
