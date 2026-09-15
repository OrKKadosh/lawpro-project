# Errors

Log budget stops, API failures, and validation failures here as they
happen — don't just print and move on. Format: timestamp, what failed,
context, how it was resolved (or that it's still blocking).

---

(entries below)

## 2026-09-10 — Chunking experiment: 2 truncated JSON responses, ~$0.21 spent on discarded calls

**What failed:** `evalkit/extraction/candidates.py`'s first version asked for verbatim `evidence_text` quotes with no length guidance and capped `max_tokens` at 8000. Against the dense `08_billing_and_claims` document (many CPT line items), the model tried to extract one candidate per billing line item, and the response was cut off mid-JSON-string before the array closed. `evalkit.llm.LLMCallError: Still not valid JSON after one retry` — the automatic repair-retry also got cut off the same way, since the underlying cause (too much content requested) wasn't fixed by asking again.
**Cost:** 2 calls (~$0.10 + ~$0.11) were paid for and discarded before the fix.
**Resolution:**
1. Tightened the prompt: `evidence_text` capped at ~150 chars, and explicit scope guidance to extract clinical events only (encounters/diagnoses/procedures/imaging/medications/therapy) — not individual billing/supply/equipment line items, which aren't clinical events and was what caused the candidate-list to balloon.
2. Raised `max_tokens` to 16000 (Sonnet 5's ceiling) as a second safety margin.
3. Added best-effort truncation salvage to `evalkit/llm.py` (`_salvage_truncated_array`): if a response is still cut off mid-array despite the above, parse as many complete top-level JSON objects out of the array as possible instead of discarding the whole paid-for response. Smoke-tested against synthetic truncated input before relying on it live.

Re-run after the fix completed cleanly (26/26 calls parsed, 0 failures) — see `results/chunking_experiment.md`.

## Later — CLI smoke test overwrote the real case-vance candidate timeline with fake data

**What happened:** Building `evalkit/cli.py`'s `extract` subcommand, I smoke-tested it by monkeypatching `run_full_extraction` to return a tiny fake result (`{'timeline_event_count': 5, 'timeline': {'events': []}}`) and calling `cli.main(['extract', 'case-vance'])` directly. `cmd_extract` always writes its result to the real, fixed path (`runs/candidate_timelines/case-vance.json`) — the mock didn't stop at verifying dispatch, it ran the real write step too, and overwrote a real file (202 real, extensively-fixed events, hours of this session's work) with the fake 0-event stub.
**Caught:** immediately after the smoke test, by checking the file's actual content rather than trusting the "OK" print output — the same "verify the real state, don't just trust the test passed" habit this session had already been applying to paid API results, applied here to a local file for the first time.
**Recovered, no new API spend:** `runs/prompt_log.jsonl` logs every raw LLM response, including the 15 real extraction calls (of a 22-call run also covering case-davis) that produced case-vance's 337 raw candidates. Reconstructed the raw candidate list by parsing the last 15 `category: "extraction"` log entries (identified by document coverage matching Vance's 8 documents, in the frozen chunk order) with the same JSON-extraction logic `evalkit/llm.py` uses, then re-ran the deterministic pipeline stages (normalize → cluster → conflict → canonicalize → salience → project, all already fixed and unit-tested) on the recovered candidates. Result matched the lost file exactly: 337 candidates → 315 clusters → 42 conflicts → 202 final timeline events, identical counts and spot-checked identical content (the CPT-27535 grounding fix, the Turner attribution fix) to what existed before the overwrite.
**Lesson, applied going forward:** a "verify wiring with mocks" smoke test must not be allowed to reach a real, fixed-path write step — either mock the write function itself, or point any file-writing dependency at a temp path for the duration of the test. Didn't re-test `cmd_extract` again after fixing this understanding, since the actual risk (the real function being called for real) was never really in question — `run_full_extraction` itself is already proven correct by its own real runs this session; only the CLI's argument-dispatch wiring needed checking, and that was already confirmed working before the file got overwritten.

## 2026-09-10 — Budget estimate recalibrated after real chunking-experiment costs

**Not a failure, but worth logging as a live budget correction.** `PLAN.md` §12 estimated ~$0.5 for the full chunking experiment based on a token/cost model (~500 tokens/OCR-page, ~130 tokens/candidate). Actual cost was $2.60 for 26 calls (~$0.10/call average) — roughly 5x the estimate. Likely driver: candidate JSON output (with the full `clinical_facts`/`attribution` schema per event) is more verbose per real event than the earlier back-of-envelope model assumed, and dense documents produce more real candidates than the ~150–250/case guess. Cumulative session spend after this step: ~$3.9 / $20 cap (`remaining_usd` per the live budget response) — still ample headroom, but the remaining phases (full extraction across both cases, judges, benchmark) should be expected to run higher than `PLAN.md` §12's table too. Will reconcile the budget section with real figures once the full extraction (step 5) confirms the pattern.
