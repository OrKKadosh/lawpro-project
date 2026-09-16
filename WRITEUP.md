# Which summarizer should LawPro ship?

This is the written recommendation. It cites `results/` directly — every number below is reproducible from a committed file without spending anything or rerunning code. Methodology and rationale live in `PLAN.md`/`DECISIONS.md`; concrete data findings live in `FINDINGS.md`.

**This is the final version, following a second pre-submission correction pass.** The first pass fixed two scoring bugs by re-scoring already-collected judge evidence. This second pass went further: it found that the omission-exclusion fix itself relied on an unsafe text heuristic that had never actually been superseded in the committed data (0% of claims in the previously-"corrected" benchmark had a real `summary_quote` — the heuristic was the only mechanism ever in use, and it demonstrably misclassified at least one genuine unsupported claim as an omission). The real fix is structural: every claim must now carry a `summary_quote` that's a verified, actual substring of the summary, enforced with a mandatory repair-retry and a hard failure if it's still invalid — never a heuristic. **All 16 controlled-benchmark summaries (8 per case) were re-judged from scratch** against this corrected schema, not merely re-scored. The numbers below are genuinely new judge output, not a recomputation of old output — and in case-vance, a real, substantive change resulted: tool C now also passes the faithfulness gate, which it did not before. See `FINDINGS.md` for the full account.

## Headline answer

**There is no single "ship tool X" recommendation, and that is itself the correct, evidence-based conclusion, not a hedge.** The brief and the data are explicit that A/B/C/D are not stable identifiers across cases (`CLAUDE.md`; confirmed empirically — see "Why no global answer" below). What the evidence actually supports is a **per-case** recommendation:

| Case | Ship | Confidence | Runner-up |
|---|---|---|---|
| **case-vance** | **D** | High | C also technically clears the faithfulness gate, but is far behind on every other axis (coverage 0.449, worst of all four tools) — not a real alternative |
| **case-davis** | **D** | Moderate | A — an extremely close alternative, narrowly behind on faithfulness and coverage but with a meaningfully better run-to-run stability profile |

Both recommendations come from `results/final_scorecard.md`, produced by a controlled benchmark that never depended on our own document-extraction pipeline's quality (`PLAN.md` §2) — so this recommendation is not at risk from anything found or fixed in that pipeline this session.

## The evidence

Every one of the 16 pre-generated summaries (8 per case: 4 tools × 2 runs) was decomposed into atomic factual claims and checked against the exact timeline that tool was given, by an LLM judge whose structured output (claim status, severity tier, cited evidence, and now a verified `summary_quote` anchoring every claim to real summary text) is scored by deterministic code — the judge proposes, the code decides the number (`DECISIONS.md`, `evalkit/scoring.py`). The one rule that decides ship-eligibility above everything else: **a single confirmed critical-tier claim (a fabricated fact, a hedge flattened into certainty, a wrong body site, a false attribution) fails the tool outright, regardless of how good its other sentences are.** This rule was sanity-checked against two independently-verified planted errors before being trusted on real results, and it worked — it caught both, again, in this fresh re-judge.

### case-vance

| Tool | Faithfulness | Ship-eligible | Coverage | Usefulness | Shared-topic agreement | Content-overlap stability | Cost/summary |
|---|---|---|---|---|---|---|---|
| A | 0.949 | **No** | 0.875 | 4.57 | 1.00 | 0.72 | $0.0292 |
| B | 0.831 | **No** | 0.880 | 4.57 | 0.71 | 0.60 | $0.0285 |
| C | 0.969 | **Yes** | 0.449 | 3.79 | 0.33 | 0.29 | $0.0073 |
| **D** | **1.00** | **Yes** | **0.898** | **4.57** | 0.87 | 0.62 | $0.0296 |

A's remaining faithfulness violation is an overclaim: Dr. Foster's hedged "unclear onset, possibly preexisting" finding stated as a settled fact — exactly the overclaimed-tier failure the gate exists to catch, and material here specifically because it bears on causation/pre-existing-condition arguments in an MVA case. B fails on similar grounds. **C now also clears the faithfulness gate** (0.969) — a genuine, real change from before this correction pass, not an artifact of it — but is not a real alternative to D: its coverage (0.449) is the worst of all four tools, well under half the material facts, and its stability is also the worst of the four (shared-topic agreement 0.33, content-overlap 0.29 — its two runs barely agree on anything). D remains the clear, undiluted winner: best faithfulness (a clean 1.00, zero flawed claims), best coverage (0.898), and tied-best usefulness (4.57).

**One caveat, checked rather than smoothed over:** D's two runs disagree on whether Dr. Foster personally performed the surgery or only arranged the consultation — checked directly against the timeline, the stronger claim (run 1) is the one the source actually supports; run 2 quietly hedges away an attribution the timeline states plainly. This is a real stability weakness (D's *content-overlap stability*, 0.62, is well below its *shared-topic agreement*, 0.87 — the two runs genuinely diverge on some material content, not just phrasing), not a faithfulness violation in either individual run, and it's the reason confidence is "high" rather than "very high."

### case-davis

| Tool | Faithfulness | Ship-eligible | Coverage | Usefulness | Shared-topic agreement | Content-overlap stability | Cost/summary |
|---|---|---|---|---|---|---|---|
| A | 0.992 | **Yes** | 0.817 | 3.93 | 0.94 | **0.88** | $0.0213 |
| B | 0.807 | **No** | 0.786 | 4.57 | 0.83 | 0.75 | $0.0200 |
| C | **1.00** | **Yes** | 0.494 | 3.93 | **1.00** | 0.63 | $0.0046 |
| **D** | **1.00** | **Yes** | **0.836** | 3.93 | 0.94 | 0.71 | $0.0213 |

Three of four pass the gate. B fails on three contradicted critical-tier claims: a fabricated provider name for who performed the amputation (the timeline names a different physician), a laterality error (right arm crushed, when the timeline says left), and a wrong amputation level. C once again passes the faithfulness gate cleanly but is not a real contender: coverage of 0.494 — under half the material facts — is disqualifying for an attorney-facing summary regardless of how accurate what little it says is.

**Between A and D, the real comparison, stated with its actual closeness intact rather than forced into a clean story:** D edges out A on both primary axes — faithfulness (1.00 vs 0.992, a 0.008 gap) and coverage (0.836 vs 0.817, a 0.019 gap) — while A has a clearly better content-overlap stability (0.88 vs D's 0.71). Both tools have exactly one real cross-run disagreement each, neither critical-tier: A's two runs disagree on whether certain lab results were drawn pre- or post-operatively (minor); D's two runs disagree on the same kind of lab-timing detail, at major materiality, plus D's run2 discusses several topics run1 doesn't (`run2_only: 5`), which is what actually drives D's lower content-overlap number — not additional contradictions. Given this pattern held in the previous pass's data too (a run2 that mentions more, not a run that drops or contradicts material content), it's read the same way here: a real stability quirk worth naming, not treated as a decisive strike against D.

Given the decision framework's own stated priority — factual safety and coverage first, stability as pairwise supporting evidence, not a statistical claim — **D is the recommendation**, by the two primary metrics the framework weights most. But this is a close call, not a clean sweep, and A is a fully legitimate, nearly-tied alternative with a real, opposite-direction advantage (consistency). A reviewer who weights run-to-run consistency more heavily than this framework does would reasonably choose A instead; nothing here is decisive enough to call that choice wrong.

## Why no global answer

This isn't a methodological hedge — it was checked, not assumed. Two independent things support treating A/B/C/D as case-local:
1. The brief and `CLAUDE.md` state it directly as a non-negotiable constraint.
2. The performance profiles themselves don't line up in a way that would suggest a shared identity: Vance's D is a clear standout with only a weak, low-coverage competitor (C) also clearing the gate; Davis's D is in a genuine near-tie with A, with C again clearing the gate on faithfulness alone but disqualified on coverage. If "D" meant the same underlying model in both cases, this pattern is at most suggestive, never decisive — exactly why the identifier is deliberately not treated as meaningful across cases.

## Confidence levels, stated plainly

- **case-vance → D: High.** The gate result is close to decisive — D and C both pass, but C is not a serious alternative on any other metric (worst coverage AND worst stability of all four tools) — and the gate mechanism itself was validated against two independently-confirmed planted errors before being trusted. The one thing keeping this from "very high": stability was only checked pairwise (n=2 runs), and D's own pair showed one real attribution disagreement. Worth naming plainly, not just implying via the general "two cases, no held-out validation set" limitation below: the severity-tier weights and critical-error gate were calibrated using two source-verified examples, both drawn from this same case — so "high" confidence should be read as high *within what a two-case, self-calibrated rubric can support*, not as independent confirmation from a rubric tuned elsewhere.
- **case-davis → D: Moderate.** D edges A narrowly on both faithfulness (1.00 vs 0.992) and coverage (0.836 vs 0.817) — the two metrics this framework weights most — but the margins are small (0.008 and 0.019) and A has a real, meaningfully better stability profile (0.88 vs 0.71 content-overlap). This is a genuinely close call between two reasonable choices, which is why confidence is "moderate," not higher: a larger sample (more than 2 runs per tool) could plausibly flip this specific comparison, and a reviewer weighting consistency more heavily than raw faithfulness/coverage margins could reasonably prefer A instead. C is excluded from serious contention despite passing the gate: covering under half the material facts is disqualifying for an attorney-facing summary.

## What would change this recommendation

Stated concretely, not as a generic caveat:

1. **More than 2 runs per tool.** Pairwise stability with n=2 is real evidence but not a statistical claim (`DECISIONS.md`). A wider sample could flip Davis's D-vs-A call specifically, given how close it already is, or surface a stability problem in Vance's D that a single disagreeing pair only hints at.
2. **Independent confirmation of Vance's exact input.** The claim that golden was the literal input behind Vance's 8 summaries rests on the user's own direct confirmation (re-verified explicitly during this pass, `FINDINGS.md`), not a repo artifact the way Davis's `input_timeline.json` is. If that turned out to be wrong, Vance's entire controlled-benchmark comparison would need re-grounding against whatever the real input was.
3. **Confirmation of whether A/B/C/D really are (or aren't) the same backends across cases.** If LawPro can state definitively that the same four tools are used for every case (just relabeled), a genuine cross-case aggregate becomes possible and could change which tool gets recommended as a single default — right now that data simply doesn't exist to check.
4. **Real production cases beyond these two synthetic ones.** Every fix and every conclusion this session is grounded in exactly two test cases, both read repeatedly while debugging. That's a real, acknowledged limitation on how far any of this generalizes (`DECISIONS.md`) — not disqualifying, since the mechanism (severity-tiered faithfulness checking against a timeline, now with verified claim provenance) is a general one, but the specific numbers above should be read as "this is what these two cases show," not "this is proven to hold everywhere."
5. **A remaining, explicit extraction limitation — not affecting this recommendation.** A confirmed bug (the extractor decoding a bare billing/procedure code into an invented clinical description, e.g. "Peripheral nerve, per CPT code convention, not clinically confirmed in text") was found and fixed for case-davis. The broader limitation behind it is not fully closed, and is stated here plainly rather than redesigned under time pressure: candidate evidence in our extraction pipeline is still **model-produced text** (an LLM's own quote/paraphrase of the source), not an immutable raw OCR span — so a grounding check that compares one model-generated field against another from the same call can, in principle, still be fooled by both agreeing on something neither is actually anchored to. This is a real, disclosed limitation of the extraction pipeline only. **It does not affect the controlled summarizer benchmark above** — that benchmark scores the 16 pre-generated summaries against the exact supplied golden/`input_timeline.json`, never our own extraction, and none of this session's extraction work changes any number in the tables above.

## Cost

Not a factor in either recommendation. Every tool in both cases costs a few cents per summary (`results/final_scorecard.md`) — even the cheapest (`case-davis` tool C at $0.0046) versus the most expensive (`case-vance` tool D at $0.0296) is a difference measured in cents, not dollars, at any realistic volume. If faithfulness were tied, cost would be the tiebreaker; it never came to that here.

## What was deliberately not built, and why

Documented as scope decisions, not omissions (`PLAN.md` §17, `DECISIONS.md`):
- No default re-reading of original scanned PDFs — OCR is trusted by default, escalated to PDF only when something looks corrupted or ambiguous.
- No row-by-row audit of every routine timeline event — full coverage for high-materiality events, a documented deterministic sample for routine ones.
- The optional sparse-input adversarial probe (`PLAN.md` §11) was scoped but not run — low marginal value against the budget/time it would cost, and the faithfulness gate was already validated against two real planted errors without it.
- Visual polish on the application interface — explicitly out of scope per the brief.
- A full real-OCR-anchored grounding redesign for extraction (see item 5 above) — the specific confirmed failure pattern was fixed; the deeper architectural fix was scoped but not attempted given remaining budget, rather than rushed and shipped half-verified (`FINDINGS.md`).

## Reproducing this

- `results/final_scorecard.md` — the table this recommendation is built from.
- `results/controlled_benchmark_case-vance.json`, `case-davis.json` — every atomic claim, its evidence, its verified `summary_quote`, and its verdict, for every summary.
- **Source-audit note**: the extraction source-audit implementation was corrected this pass (it now checks only the specific OCR page an event cites, not the whole document — see `FINDINGS.md`). The *old* quantitative audit results predate that fix and are **not reported as current final evidence** — they've been moved to `results/historical/timeline_eval/` rather than left in a reviewer-facing location looking current. Remaining API budget was deliberately spent on the controlled benchmark and the corrected end-to-end path above instead of re-running all 4 audit passes (~$1.4–3.0 estimated) — this is a real, disclosed gap, not a hidden one. This has no effect on the recommendation above: source-audit results never fed the controlled benchmark.
- `results/pipeline_demo_case-vance.json`, `case-davis.json` — the uncontrolled end-to-end demo referenced above. Both current: case-davis was regenerated this pass against the corrected candidate timeline (fresh `/v1/summarize` + judge call, $0.1168) after a real extraction-grounding bug was fixed (see "What would change this recommendation" above) — it now cleanly passes the faithfulness gate (1.00 faithfulness, 0.866 coverage), a genuinely better result than the pre-fix run.
- `tests/` — 110 tests, no live API calls, covering every deterministic scoring and extraction-logic claim made in this document.
- A field-level guide to reading all of the above, with real excerpts, is available as a published artifact from this session (see conversation history) and as `results/conflict_review_case-vance.md`, `case-davis.md` for the extraction pipeline's own decision log in plain English.
