# Which summarizer should LawPro ship?

This is the written recommendation. It cites `results/` directly — every number below is reproducible from a committed file without spending anything or rerunning code. Methodology and rationale live in `PLAN.md`/`DECISIONS.md`; concrete data findings live in `FINDINGS.md`.

**This is the final, corrected version**, following a pre-submission review pass that found and fixed two real methodology bugs in the judge/scoring layer itself (not just extraction-side issues): (1) the faithfulness judge sometimes described a summary *omission* as if it were an unsupported factual *claim*, wrongly lowering faithfulness for content the summary never asserted in the first place — fixed at the scoring layer (`evalkit/scoring.py`'s `is_omission_shaped_claim`), and every controlled-benchmark score below has been re-derived from the original judge evidence under the corrected logic; (2) the pairwise-stability metric only measured agreement on topics *both* runs happened to mention, so a run that silently dropped most of its content relative to the other could still score a perfect 1.0 — replaced with two explicitly separate metrics (below). All numbers in this document are the corrected, final ones; see `FINDINGS.md`/`DECISIONS.md` for the full account of what changed and why.

## Headline answer

**There is no single "ship tool X" recommendation, and that is itself the correct, evidence-based conclusion, not a hedge.** The brief and the data are explicit that A/B/C/D are not stable identifiers across cases (`CLAUDE.md`; confirmed empirically — see "Why no global answer" below). What the evidence actually supports is a **per-case** recommendation:

| Case | Ship | Confidence | Runner-up |
|---|---|---|---|
| **case-vance** | **D** | High | None close — D is the only tool that passes the faithfulness gate at all |
| **case-davis** | **A** | Moderate | D (a genuinely close alternative — slightly behind on faithfulness and coverage, but zero cross-run contradictions vs. A's one) |

Both recommendations come from `results/final_scorecard.md`, produced by a controlled benchmark that never depended on our own document-extraction pipeline's quality (`PLAN.md` §2) — so this recommendation is not at risk from anything found or fixed in that pipeline this session.

## The evidence

Every one of the 16 pre-generated summaries (8 per case: 4 tools × 2 runs) was decomposed into atomic factual claims and checked against the exact timeline that tool was given, by an LLM judge whose structured output (claim status, severity tier, cited evidence) is scored by deterministic code — the judge proposes, the code decides the number (`DECISIONS.md`, `evalkit/scoring.py`). The one rule that decides ship-eligibility above everything else: **a single confirmed critical-tier claim (a fabricated fact, a hedge flattened into certainty, a wrong body site, a false attribution) fails the tool outright, regardless of how good its other sentences are.** This rule was sanity-checked against two independently-verified planted errors before being trusted on real results, and it worked — it caught both.

### case-vance

| Tool | Faithfulness | Ship-eligible | Coverage | Usefulness | Shared-topic agreement | Content-overlap stability |
|---|---|---|---|---|---|---|
| A | 0.896 | **No** | 0.892 | 4.14 | 1.00 | 0.70 |
| B | 0.736 | **No** | 0.869 | 4.21 | 0.72 | 0.59 |
| C | 0.927 | **No** | 0.489 | 3.79 | 0.60 | 0.43 |
| **D** | **1.00** | **Yes** | **0.938** | **4.64** | 0.91 | 0.63 |

A and B both take Dr. Foster's hedged "unclear onset, possibly preexisting" finding and state it as a settled fact shared confidently by both physicians — exactly the overclaimed-tier failure the gate exists to catch, and material here specifically because it bears on causation/pre-existing-condition arguments in an MVA case. C fails the gate too, and separately covers under half of the material facts (0.489) — it both fabricates and under-covers. D is not a marginal winner: it has the best score on every axis measured, not just the one that gates it — and after fixing a real judge bug that had been conflating omissions with faithfulness violations (below), D's faithfulness composite is a clean 1.00, zero flawed claims.

**One caveat, checked rather than smoothed over:** D's two runs disagree on whether Dr. Foster personally performed the surgery or only arranged the consultation. Checked directly against the timeline — the stronger claim (run 1) is the one the source actually supports; run 2 is the one that quietly hedges away an attribution the timeline states plainly. This is a real stability weakness (D's *content-overlap stability*, 0.63, is well below its *shared-topic agreement*, 0.91 — the two runs genuinely diverge on some material content, not just phrasing), not a faithfulness violation in either individual run, and it's the reason confidence is "high" rather than "very high."

### case-davis

| Tool | Faithfulness | Ship-eligible | Coverage | Usefulness | Shared-topic agreement | Content-overlap stability |
|---|---|---|---|---|---|---|
| **A** | 0.983 | **Yes** | **0.872** | 3.93 | 0.94 | 0.85 |
| B | 0.752 | **No** | 0.792 | 4.36 | 0.81 | 0.81 |
| C | **0.99** | **Yes** | 0.574 | 3.79 | 0.92 | 0.65 |
| D | 0.969 | **Yes** | 0.848 | 3.93 | **1.00** | 0.77 |

Three of four pass the gate here, which is itself informative — Davis's summaries are more uniformly faithful than Vance's, plausibly because Davis's benchmark timeline (`input_timeline.json`, shipped directly rather than independently audited) had fewer of the ambiguous, hedge-laden findings that tripped up Vance's tools. B fails on two contradicted claims: a wrong cervical disc level and a fabricated provider name that appears nowhere in the timeline.

Among the three that pass, faithfulness is close (0.969–0.99, a 0.021 spread) — **stated plainly: this gap is not shown to be within measurement noise** (this project never ran a repeat-judge experiment to quantify that, so claiming "noise" would be an unsupported technical-sounding excuse, not a measured fact). It's simply a small, real gap. C is excluded from serious contention regardless of exactly how that small gap is read, because C's coverage gap is not small: 0.574 vs. A's 0.872 and D's 0.848 — barely half the material facts, a genuinely large, decisive difference by any reasonable reading. C's near-top faithfulness is not a reason to prefer it: a summary can be faithful to everything it says and still fail the attorney by leaving most of the case out.

Between A and D specifically, the comparison is closer than a single metric can settle, and is stated here with that closeness intact rather than smoothed into one clean number: A leads narrowly on faithfulness (0.983 vs 0.969, a 0.014 gap) and on coverage (0.872 vs 0.848, a 0.024 gap — comparable in size to the faithfulness gap, so neither is being treated as decisive while the other is waved away as noise). D leads on shared-topic agreement (1.00 vs 0.944) and, more substantively, **D's two runs have zero cross-run contradictions, while A's have one** (a minor-materiality disagreement about whether certain labs were pre- or post-operative — checked directly in `results/controlled_benchmark_case-davis.json`'s raw stability data). D's LOWER content-overlap-stability score (0.77 vs A's 0.85) is driven entirely by its run2 mentioning 4 more topics run1 didn't cover (`run2_only: 4`), not by the runs disagreeing about anything — the metric penalizes "said more" exactly as harshly as "contradicted itself," which is a real limitation of reading that one ratio in isolation. So D's apparent stability disadvantage is arguably overstated by that single number: on the dimension that matters most for a faithfulness-first ship decision (actual contradictions between runs, not topic-count asymmetry), D is arguably the more consistent tool.

Given all of this, **A is still the recommendation** — it leads on both faithfulness and coverage, the two dimensions the decision logic weights most heavily, and neither gap is large enough to call reversed. But this is a genuinely close call between A and D, not a clean sweep, and the previous version of this write-up (before this section was corrected) overstated how decisively it favored A. D remains a legitimate alternative, and specifically the tool worth prioritizing if a future, larger sample shows its topic-count asymmetry was itself just first-run-vs-second-run variance rather than a real omission problem.

## Why no global answer

This isn't a methodological hedge — it was checked, not assumed. Two independent things support treating A/B/C/D as case-local:
1. The brief and `CLAUDE.md` state it directly as a non-negotiable constraint.
2. The performance profiles themselves don't line up in a way that would suggest a shared identity: Vance's D is a clear standout on every metric with no close competitor; Davis's D is a strong-but-not-top performer with three tools in real contention. If "D" meant the same underlying model in both cases, this is a plausible but not decisive pattern either way — which is exactly why the identifier is deliberately not treated as meaningful across cases, rather than inferring from suggestive-but-inconclusive score patterns.

## Confidence levels, stated plainly

- **case-vance → D: High.** The gate result is decisive (only tool to pass, by a wide margin on every secondary metric too), and the gate mechanism itself was validated against two independently-confirmed planted errors before being trusted. The one thing keeping this from "very high": stability was only checked pairwise (n=2 runs), and D's own pair showed one real disagreement. Worth naming plainly, not just implying via the general "two cases, no held-out validation set" limitation below: the severity-tier weights and critical-error gate were calibrated using two source-verified examples, both drawn from this same case — so "high" confidence should be read as high *within what a two-case, self-calibrated rubric can support*, not as independent confirmation from a rubric tuned elsewhere. This doesn't change the recommendation itself (the gate result was also confirmed against facts independent of the calibration examples, e.g. B's run-2 fabricated values), but the calibration-set/scoring-set overlap is a real, specific reason for some caution, not just an abstract one.
- **case-davis → A: Moderate.** A leads D narrowly on both faithfulness (0.983 vs 0.969) and coverage (0.872 vs 0.848), which is why it's the recommendation — but neither gap is large, and D has a real, specific point in its favor that a single stability ratio understates: zero cross-run contradictions, against one (minor-materiality) disagreement in A's pair. This is a genuinely close call between two reasonable choices, not a decisive win, which is why confidence is "moderate" rather than "moderate-high" — a small change in a larger sample (more than 2 runs per tool) could plausibly flip this specific comparison. C is excluded from serious contention despite its top faithfulness score: covering barely half the material facts is disqualifying for an attorney-facing summary regardless of how accurate what little it does say is.

## What would change this recommendation

Stated concretely, not as a generic caveat:

1. **More than 2 runs per tool.** Pairwise stability with n=2 is real evidence but not a statistical claim (`DECISIONS.md`). A wider sample could change Davis's A-vs-D call, or surface a stability problem in Vance's D that a single disagreeing pair only hints at.
2. **Independent confirmation of Vance's exact input.** The claim that golden was the literal input behind Vance's 8 summaries rests on the hiring contact's word, not a repo artifact the way Davis's `input_timeline.json` is (`FINDINGS.md`, documented as a known limitation from the start). If that turned out to be wrong, Vance's entire controlled-benchmark comparison would need re-grounding against whatever the real input was.
3. **Confirmation of whether A/B/C/D really are (or aren't) the same backends across cases.** If LawPro can state definitively that the same four tools are used for every case (just relabeled), a genuine cross-case aggregate becomes possible and could change which tool gets recommended as a single default — right now that data simply doesn't exist to check.
4. **Real production cases beyond these two synthetic ones.** Every fix and every conclusion this session is grounded in exactly two test cases, both read repeatedly while debugging. That's a real, acknowledged limitation on how far any of this generalizes (`DECISIONS.md`) — not disqualifying, since the mechanism (severity-tiered faithfulness checking against a timeline) is a general one, but the specific numbers above should be read as "this is what these two cases show," not "this is proven to hold everywhere."
5. **Hardening the extraction-to-summarize handoff.** A real end-to-end run (`results/pipeline_demo_case-vance.json`, `case-davis.json`) fed our own extracted timeline — not golden — into each case's winning tool, and both failed the faithfulness gate on that uncontrolled run (D: 0.852 faithfulness, case-vance; A: 0.808, case-davis). Both failures were verified as real, not scoring artifacts: a hedge our own extraction correctly preserved ("provider disputed across sources") got flattened into certainty by the summarizer, and a real misattribution (crediting the surgeon who *planned* an amputation with *performing* it, when the timeline names a different physician as the one who actually performed it) got stated as fact. This doesn't change which tool to ship — the controlled benchmark exists specifically so this can't contaminate that decision — but it's a concrete signal that shipping requires more than picking the right tool: the extraction pipeline's own output needs work specifically on how it phrases disputed/hedged facts before a summarizer is trusted to preserve that nuance downstream.

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
- `results/timeline_eval/case-vance.json`, `case-davis.json` — our own extraction pipeline's independently-audited accuracy: case-vance 86.1%, case-davis 88.4% source-grounded precision, both now over a **complete** audited sample (101/101 and 86/86 selected events actually received a verdict — a real bug found and fixed this session, see `FINDINGS.md`, previously silently incomplete for case-davis: 35/80). Kept structurally separate from this recommendation either way — extraction accuracy never feeds the controlled benchmark above.
- `results/pipeline_demo_case-vance.json`, `case-davis.json` — the uncontrolled end-to-end demo referenced above.
- `tests/` — 94 tests, no live API calls, covering every deterministic scoring and extraction-logic claim made in this document.
- A field-level guide to reading all of the above, with real excerpts, is available as a published artifact from this session (see conversation history) and as `results/conflict_review_case-vance.md`, `case-davis.md` for the extraction pipeline's own decision log in plain English.
