# Summarizer Evaluation — Implementation Plan

What we're building, why it's structured this way, how it's evaluated, and in what order it gets built. Design rationale lives in `DECISIONS.md`; verified data observations live in `FINDINGS.md`.

## 1. Objective and evaluation principles

- Recommend which of four black-box summarizers (A/B/C/D) LawPro should ship, backed by a defensible evaluation methodology, and deliver a runnable application that demonstrates the pipeline end-to-end.
- Two cases, both with a confirmed exact input behind their 8 supplied summaries: `case-vance` (`golden/case-vance.timeline.json` — confirmed via the hiring contact, `FINDINGS.md`) and `case-davis` (`data/case-davis/summaries/input_timeline.json` — confirmed by the shipped file itself). Each case's 8 summaries form 4 same-tool run1/run2 pairs.
- **A/B/C/D are case-local identifiers, not stable backends.** Every score is indexed `(case_id, tool_letter)`. No claim aggregates a letter across cases. "Not enough evidence for a global winner" is an acceptable conclusion if that's what the evidence shows.
- Two experiments stay structurally separate and never share a scoring path (§2).
- Factual correctness and stylistic quality are scored and reported separately; style can break a tie between factually-safe candidates, never compensate for a factual error.
- A supplied reference timeline (golden, or Davis's `input_timeline.json`) is a **reference**, not unquestionable ground truth — audited against source, never silently rewritten or blindly trusted.
- Budget: $20 cap, $0 spent as of planning. Every call tracked and logged; spend is not the binding constraint, but no call pattern is chosen carelessly (§12).

## 2. Executive architecture

```
CONTROLLED SUMMARIZER BENCHMARK              END-TO-END PIPELINE
   Fixed/reference timeline                      OCR documents
        |                                              |
   /v1/summarize {A,B,C,D}                        our extraction pipeline
        |                                              |
   summary evaluation                              timeline evaluation
        |                                              |
   case-level shipping recommendation              chosen tool(s) -> summary eval
```

The **controlled benchmark** answers: given the same timeline, which summarizer behaves better. The **end-to-end pipeline** answers: does the whole OCR-to-summary system work, and how good is our own extraction. They share code — the same summary-evaluation judges — but never share a scoring path. The controlled benchmark only ever scores a fixed reference timeline (Vance: `golden/case-vance.timeline.json`, unedited; Davis: `input_timeline.json`, unedited); the end-to-end pipeline's output lives under a visibly separate `results/` path so a reviewer never mistakes a pipeline-demo number for a benchmark number. Extraction quality and summarizer quality are never allowed to contaminate each other's measurement (rationale: `DECISIONS.md`).

## 3. Extraction pipeline

```
OCR documents
  -> prepare.py         page loading, document/page-aware chunk boundaries (never blind token slicing)
  -> candidates.py       recall-oriented candidate-event extraction, per chunk
  -> normalize.py        date normalization (raw / basis / confidence), type/status normalization
  -> cluster.py           groups mentions of the same real-world event into a cluster, preserving
                          every field value each mention carries. Selects nothing.
  -> conflict.py          field-level conflict detection inside/across clusters -> conflict_group records
  -> hitl.py               review queue + safe auto-resolution (§6)
  -> canonicalize.py      assembles the canonical event from each cluster's resolved/flagged fields
  -> salience.py           tiered inclusion (select_material_timeline_events) — a distinct problem
                          from clustering: real, repetitive events (e.g. 40+ PT sessions) are not
                          duplicates, and deciding whether they all belong in the final timeline is
                          a separate decision from deciding they're the same event
  -> project.py            canonical event -> strict 4-field schema + detail-grounding check
  -> chronos.timeline.check    schema validation, required before any /v1/summarize call
```

Candidate extraction is recall-oriented: it is not asked to simultaneously judge attorney-relevance, because information discarded at that stage can never be recovered downstream. Clustering never resolves a value — resolution happens only afterward, on top of a cluster's full preserved value set, so competing evidence is never discarded before conflict detection sees it.

## 4. Intermediate schemas and evidence model

**Candidate event** (internal only, never sent to `/v1/summarize`):
```json
{
  "candidate_id": "vance-doc01-ev03",
  "source_doc_id": "01_ems_and_ed", "source_page": 5,
  "evidence_text": "verbatim snippet, not a paraphrase",
  "raw_date": "six days ago", "normalized_date": "2022-09-06",
  "date_basis": "relative_to_note_date", "date_confidence": 0.82,
  "event_type_candidate": "diagnosis",
  "status": "performed | ordered | recommended | planned | considered | cancelled | reported_history",
  "attribution": {
    "asserted_by": "patient_reported | clinician_observed | clinician_opinion | billing_system",
    "provider": "Dr. Elizabeth Foster, MD", "certainty": "confirmed | suspected | uncertain"
  },
  "temporal_relation_to_incident": "pre-incident | index-incident | post-incident | unknown",
  "materiality_hint": "high | relevant | routine",
  "extraction_confidence": 0.0,
  "clinical_facts": {
    "concept": "left humerus ORIF", "body_site": "humerus", "laterality": "left",
    "diagnosis_or_finding": "compound mid-shaft fracture",
    "procedure": "open reduction and internal fixation", "medication": null, "dose": null
  },
  "raw_summary": "one-line human-readable gloss for HITL review"
}
```
`date_basis` distinguishes `explicit_event_date`, `relative_to_note_date`, `note_signing_date`, `billing_service_date`, `inferred`, `unknown` — the distinction that lets an extractor prefer an operative report's explicit date over a billing form's service date for the same event (`FINDINGS.md`). `clinical_facts` is deliberately compact and fully optional field-by-field, not a medical ontology — its only job is giving `cluster.py`/`conflict.py` something structured to block and compare on, and giving `project.py` the pieces to compose the final sentence from.

**Canonical event** (post cluster/conflict/salience, pre-projection):
```json
{
  "canonical_id": "...", "member_candidate_ids": ["..."],
  "date": "2023-09-07", "date_basis": "explicit_event_date",
  "type": "procedure", "status": "performed",
  "clinical_facts": {"...": "..."},
  "attribution": {"asserted_by": "clinician_observed", "provider": "Dr. Myrtle Turner, MD, FACS", "certainty": "confirmed"},
  "materiality": "high", "confidence": 0.95,
  "conflict_group_id": null, "needs_review": false, "review_reasons": [],
  "evidence": [
    {"doc": "02_hospitalization", "page": 4, "snippet": "Date of Surgery: 2023-09-07..."},
    {"doc": "08_billing_and_claims", "page": 1, "snippet": "PRINCIPAL PROCEDURE / DATE: ...09/04/2023...",
     "note": "conflicting billing-system date, not used for the canonical value — see §6"}
  ]
}
```
Losing values from a resolved conflict always stay in `evidence` — never dropped, so the canonical event stays auditable even when auto-resolved.

**Final projection** — the only artifact that ever reaches `/v1/summarize`:
```json
{"date": "2023-09-07", "type": "procedure", "detail": "...", "source": "02_hospitalization p4"}
```
`detail` must not introduce any fact absent from the canonical event/evidence — a grounding-check pass (deterministic keyword/entity check first, LLM-judge fallback for anything flagged) verifies this before schema validation. Detail-length target is a real single sentence in the ~50–220 char range observed in golden's own events; `MAX_DETAIL_CHARS=600` (`chronos/timeline.py`, `chronos/constants.py`) is the server's hard rejection ceiling, not a style target.

## 5. Chunking / development experiment

Not one giant prompt by default, not blind token-count chunking, not a hyperparameter search either.

- **Test set** (Vance only, frozen before touching Davis): bounded representative page windows, not entire documents — a ~12-page window from `08_billing_and_claims` (dense hospital/billing record), `03_prior_records` in full (5pp — the date/pre-existing-condition-ambiguity document), and the first ~12 pages of `05_pt_lang_weimann` (repetitive-therapy document, 33pp total).
- **Configurations**: small (2–3pp + 1pg overlap), medium (~5pp + 1pg overlap), large (~10pp + 1pg overlap) — page-aware, never splitting mid-page. Sonnet 5 for every configuration, including the small ones, since the final extractor is Sonnet 5 and tuning on a different model would test the wrong thing.
- **Local dev set, built before running any configuration**: a small, frozen, manually-reviewed event list for each of the three windows (LLM-assisted drafting, human-verified) — a ground truth scoped to the experiment itself, not the case-wide material-fact set (which doesn't exist yet at this point in the build order, and is a different, case-wide artifact) and not golden.
- **Metrics per config**, scored against that local dev set: material-event recall, unsupported-event rate, date fidelity, duplicate-candidate rate, conflict-detection rate, cost.
- One config is picked and frozen, documented with its comparison table (`results/chunking_experiment.md`). The frozen config then applies unchanged to all of Vance and all of Davis — a weak result on Davis is a generalization finding, not a cue to re-tune on Davis.
- Call-count/budget estimate is computed from real page counts, not assumed 1-call-per-document (§12).

## 6. Conflict resolution + HITL policy

Field-level conflict detection covers: date, procedure status, provider, diagnosis/finding, injury mechanism, medication/dose, laterality/body site, causation/attribution. Resolution principle: **prefer the source most directly authoritative for the specific fact** (operative report for surgery date, not billing; patient-reported history for subjective symptom onset; billing data only for billing facts) — never a blanket source hierarchy. Competing evidence is never silently overwritten.

Three outcomes, chosen by materiality:
- **Auto-resolved** (low/routine materiality, or an unambiguous authoritative-source match): the suggested resolution is accepted, but every losing value and its source stays in `evidence`.
- **High-materiality, resolved with confidence**: same, but only when the authoritative-source rule points unambiguously at one value for that specific field. `needs_review` stays `false` only when this bar is met.
- **High-materiality, unresolved**: `needs_review: true`, and the event does not get a confidently-worded final value. If the unresolved field is `date`, the final projection uses `date: null` — the schema's own definition is "null when no date is recoverable"; using it as a conservative fallback for "recoverable but genuinely disputed" is an implementation policy stated here, not a claim about the schema's literal wording. If the unresolved field is expressible in `detail`, the generated sentence states the disagreement in plain language rather than picking a side. **A high-materiality unresolved conflict must never become a confidently-worded final fact.** Low-materiality unresolved conflicts may simply be omitted from the final timeline rather than building special-case machinery for routine content.

HITL queue reasons: `SOURCE_CONFLICT, AMBIGUOUS_DATE, POSSIBLE_DUPLICATE, OCR_CORRUPTION, UNCLEAR_PERFORMED_VS_PLANNED, LOW_EXTRACTION_CONFIDENCE, HIGH_MATERIALITY_LOW_CONFIDENCE, CAUSATION_AMBIGUITY, NEGATION_UNCERTAIN, TYPE_AMBIGUITY, OUTLIER_VALUE`. Prioritization: `materiality {high=3, relevant=2, routine=1} × uncertainty {high=3, medium=2, low=1}`, queue sorted descending, default view surfaces `priority ≥ 4`. A reviewer sees the candidate event, its evidence snippets, competing values with sources, the suggested resolution and reason, and the trigger reason(s). HITL/conflict-detection recall against the source audit's known-issue list is itself an evaluation dimension (§7).

## 7. Timeline evaluation

Three explicitly separate concepts, never merged into one:
- **Provided Reference** — `golden/case-vance.timeline.json`, `data/case-davis/summaries/input_timeline.json`. **Used unmodified by the controlled benchmark** (§8/§9) — that comparison must keep scoring against the exact file the 8 pre-generated summaries were actually produced from. **For scoring our own extraction specifically**, a manually corrected copy is used instead where one exists (`golden/case-vance.timeline.adjudicated.json`, `Case.adjudicated_reference_timeline_path()`) — exactly 5 changes, each sourced strictly from the Source Audit below (never from our own candidate extraction) and manually verified against a direct source quote (`DECISIONS.md`: "golden is now treated as ground truth for extraction scoring"). The original provided file is never edited. Scored: severity-tiered precision/recall against our candidate timeline (`score_extraction_against_golden`, `DECISIONS.md`) — a missed reference fact, a matched-but-wrong fact, an independently-grounded extra fact, and an ungrounded extra fact are four distinct tiers, not one flat match rate — plus date agreement and type agreement among matched events.
- **Source Audit** — a risk-based, independent read of OCR/PDF evidence against reference and candidate events, producing a report (`likely_reference_omissions`, `likely_reference_errors`, `conflicts_found_in_source`, `questionable_dates`, `incorrect_source_attribution`) — never a rewrite of the reference. Full coverage is guaranteed for all high-materiality events, all detected source conflicts, all candidate/reference disagreements, and every Critical-tier finding cited in the final recommendation; routine/repetitive events get a documented sample instead of row-by-row checking. This is the *only* source a golden correction may be drawn from.
- **Our Candidate Timeline** — reported as `reference_agreement`, `extraction_score` (the severity-tiered result above), `source_grounded_precision`, `reference_events_disputed_by_source_audit`, `additional_source_grounded_events_missing_from_reference`.

**Coverage boundary**: a fact's absence from the provided reference is a Source Audit or Candidate Timeline finding — never a summarizer-faithfulness or summarizer-coverage finding. A tool was never given a fact the reference doesn't contain and has no way to know it exists, so that absence cannot be held against it in the controlled benchmark. It becomes a scorable coverage fact only in the end-to-end pipeline, and only if our own extracted timeline actually contains it. This principle applies generally, not just to the specific example that surfaced it (`FINDINGS.md`).

Other Stage-0 metrics: date fidelity (event-date vs. note/billing/signing date specifically); type-classification accuracy; conflict/HITL detection recall against the source audit's known-issue list; duplicate/compression behavior (true duplicates collapse to one canonical event with multiple evidence entries; distinct-but-repetitive events like PT sessions stay distinguishable pre-salience).

## 8. Controlled summarizer benchmark

Both cases have a confirmed exact input behind their 8 pre-generated summaries: Davis's `input_timeline.json` (the shipped file itself) and Vance's `golden/case-vance.timeline.json` (confirmed via direct communication with the hiring contact — `FINDINGS.md`). With input identity established for both, each case's 8 supplied summaries are the primary controlled benchmark directly.

- **Vance controlled benchmark**: the 8 supplied summaries (`A–D × run1/run2`), scored directly against golden — full faithfulness, coverage, usefulness, and pairwise-stability scores, on the same footing as Davis.
- **Davis controlled benchmark**: unchanged — the 8 supplied summaries, scored directly against `input_timeline.json`.
- Fresh `/v1/summarize` calls for either case are optional (symmetry/sanity-check only — e.g. confirming the endpoint still returns comparable output), not methodologically required for either.

## 9. Summarizer evaluation methodology

**Atomic claims.** Every summary is decomposed into atomic factual claims (a sentence can contain several). Each claim gets `supported | unsupported | contradicted | overclaimed`, a materiality tier, evidence event IDs, and a reason — never a bare score.

**Faithfulness, with a hard gate.** Severity tiers:

| Tier | Examples |
|---|---|
| Critical | fabricated procedure/diagnosis/mechanism; overclaims a hedged finding into certainty; wrong body level/laterality; false causal attribution; misattributes one physician's opinion to another |
| Major | wrong/unsupported date, provider, or finding on a material event; wrong sequencing |
| Minor | unsupported narrative flourish, nothing independently checkable |

Composite score is severity-weighted, but a hard rule sits on top: any confirmed Critical-tier claim caps the summary's ship-eligibility regardless of composite score — a large denominator of correct sentences cannot dilute one fabricated procedure into invisibility. Severity-tier definitions, the gate rule, and the material fact-set (below) are frozen *before* the aggregate A/B/C/D leaderboard is assembled; known factual discrepancies may only sanity-check the frozen rubric, never retune it toward a preferred ranking.

**Coverage — fact-level, case-specific, derived from the benchmark timeline before any summary is read.** A fixed `material_fact_set` is built once per case directly from the exact benchmark timeline, with an ID, category, materiality weight, and supporting event IDs per fact — frozen after a human spot-check, before any tool's output is scored. Every tool's summary for that benchmark is scored against the identical fact set, fact-by-fact (`reflected: yes|no|partial`), not category-by-category — a category like "major injuries" can contain several independently material facts, and category-level yes/no hides partial coverage.

**Pairwise run stability** (not "consistency" — only 2 runs exist per tool/case, so no claim of statistical stability). Primary evidence: both cases' 8 supplied summaries, each forming 4 same-tool run1/run2 pairs against a confirmed, identical input per tool — symmetric for Vance and Davis. Judge aligns claims between run1/run2 (`agree | disagree | run1_only | run2_only`, materiality-tagged); metrics are critical cross-run conflict count and material-fact overlap rate. Lexical/length checks are a secondary sanity signal only.

**Attorney usefulness** (not "prose quality"): chronological clarity, concision, organization, preservation of uncertainty, separation of pre-existing vs. post-incident conditions, emphasis on material facts, avoidance of repetitive clutter. May break a tie between factually-safe candidates; can never compensate for a Critical-tier error, and never touches the ship/no-ship gate.

**Cost** — reported alongside quality, never blended into a ratio: mean cost per summary (from real `cost_usd`), projected cost per 1,000 summaries. If quality is effectively tied, prefer cheaper; if a modest cost premium buys materially better factual safety, quality wins.

## 10. Judge / scoring safeguards

Every judge: structured JSON in/out, schema-validated, one controlled repair-retry on malformed output, prompt+response logged. Deterministic Python computes every composite/gated metric — the judge itself never emits a final score.

- **Material-fact-set construction judge** — runs once per case on the benchmark timeline only, before any summary is judged; frozen after a human spot-check.
- **Faithfulness + coverage + usefulness judge** — combined per summary call; input includes the frozen `material_fact_set`; output is `claims[]`, `fact_coverage[]`, `usefulness{}`. Runs identically for every summary in both cases' controlled benchmarks — both cases have confirmed input identity, so there is no diagnostic-only, unscored path.
- **Pairwise stability judge** — aligns claims between two same-tool runs.
- **Source-audit / reference-agreement judge** — checks an event against its cited source OCR text; used both to audit the provided reference and to score the candidate timeline.
- **Conflict-detection** (used inside extraction) — `{conflict_group_id, field, candidate_values:[{value, source}], suggested_resolution, resolution_reason, needs_review}`.
- **Failure handling**: malformed JSON gets one retry with the parse error appended; still malformed is logged to `ERRORS.md` and excluded from scoring, surfaced as "not scored — judge output invalid." Every Critical-tier finding that feeds the final recommendation gets a manual read-through before being cited in the write-up — the judge proposes, a human verifies.

## 11. Experiment matrix

| | Timeline used | Pre-gen summaries | Fresh `/v1/summarize` | Judge calls | Exact-input certainty |
|---|---|---|---|---|---|
| Vance, controlled | golden, source-audited, unedited | 8 — is the controlled experiment (input confirmed via hiring contact) | Optional: 0–4, low priority | faithfulness+coverage+usefulness ×8; stability ×4 pairs | Yes — confirmed |
| Davis, controlled | `input_timeline.json`, unedited | 8 — is the controlled experiment | Optional: 0–4, low priority | faithfulness+coverage+usefulness ×8; stability ×4 pairs | Yes — confirmed |
| End-to-end, both cases | our extracted candidate timeline | none | 1–2 per case, through the tool(s) the controlled benchmark identifies as strong | reuses the same judges, separate `results/` path | n/a — uncontrolled demo, never cited for shipping |

Secondary/optional: sparse-input hallucination probe (tiny timeline × 4 tools × Vance, ~4 calls) — dropped without weakening the plan if time/budget don't allow.

## 12. Budget

Verified page totals (per manifest): Vance = 115 pages / 8 docs; Davis = 47 pages / 6 docs; 162 total. Chunking is page-aware and never spans documents, so extraction call count is `sum(ceil(doc_pages / effective_stride))` over all 14 documents:

| Config | Chunks (calls) | Est. cost |
|---|---|---|
| small (~2pp stride) | 84 | ~$0.96 |
| medium (~4pp stride) | 47 | ~$0.83 |
| large (~9pp stride) | 23 | ~$0.72 |

The working planning figure uses medium (47 calls, ~$0.83) until §5's experiment freezes the real config.

| Phase | Calls |
|---|---|
| Chunking experiment | ~27 |
| Final candidate extraction | ~47 (23–84 depending on frozen config) |
| Cluster/conflict LLM adjudication (ambiguous only) | ~4–8 |
| Source audit, risk-based | ~6–10 |
| Material-fact-set construction | 2 |
| Detail-grounding check | ~2 |
| Fresh summarize, either case (optional symmetry/sanity check) | 0–8 |
| Faithfulness+coverage+usefulness (8 Vance + 8 Davis pre-generated) | ~16 |
| Pairwise stability (4 Vance pairs + 4 Davis pairs) | 8 |
| End-to-end demo | 2–4 |
| Sparse-input probe (optional) | 0–4 |
| **Total** | **~110–135 calls, ~$2.5–6** |

Lower than earlier estimates: with input identity confirmed for both cases (§8), the 8 required fresh Vance calls and the separate 8+4 diagnostic-only judge calls are no longer needed — both cases' pre-generated summaries are scored directly and identically.

Against a $20 cap at $0 spent — ample headroom. Sonnet 5 throughout (candidate extraction, the chunking experiment, all judges, conflict adjudication) — no deliberately-cheaper-model substitution; budget headroom doesn't justify the risk of a config that doesn't transfer between models.

## 13. Repository / application structure

```
exercise/
  chronos/                         existing, untouched
  pyproject.toml                   deps + Python 3.11+
  .gitignore                       .env, CREDENTIALS.md, __pycache__, runs/, cache/
  evalkit/
    discover.py                    case discovery from data/<case>/
    budget.py                      spend tracker, hard floor, per-call-type accounting
    llm.py                         chronos.client.generate wrapper: JSON-mode, schema validation, one retry, logging
    extraction/
      prepare.py / candidates.py / normalize.py / cluster.py / conflict.py / hitl.py /
      canonicalize.py / salience.py / project.py / chunk_experiment.py
    reference/
      audit.py                     risk-based source audit — produces a report, never a rewrite
      compare.py                   reference-agreement scoring for our candidate timeline
    judge/
      schemas.py / material_facts.py / faithfulness_coverage.py / stability.py
    benchmark/
      controlled.py                fixed-reference-timeline × 4 tools
      pipeline_demo.py             our extraction -> chosen tool(s) — visibly separate output path
      adversarial.py               secondary/optional sparse-input probe
    scoring.py                     aggregates judge output, applies the critical-error gate
    report.py                      renders results/final_report.md + final_scorecard.json
    cli.py                         list-cases, extract, evaluate-timeline, summarize, evaluate, run
  prompts/                         every prompt template, reviewable
  results/                         committed — see §14
  runs/                            gitignored — live re-run scratch, cache
  tests/                           see §15
  PLAN.md / DECISIONS.md / FINDINGS.md / PROGRESS.md / ERRORS.md / WRITEUP.md
```

## 14. Result artifacts

Committed, so a reviewer reads the evidence without spending budget or rerunning anything:
```
results/
  final_scorecard.json      per-(case,tool): faithfulness (weighted + gate status), coverage, stability, usefulness, cost
  final_report.md            ~10-minute human-readable version
  timeline_eval/case-vance.json, case-davis.json    reference agreement, source-grounded precision, disputed/additional events
  critical_findings.json     every Critical-tier claim behind the recommendation, with evidence
  chunking_experiment.md     §5's config comparison and the frozen decision
```
Gitignored: `runs/`, `cache/`, large raw API logs. `WRITEUP.md` cites `results/` directly — the recommendation is checkable without running any code.

## 15. Tests and verification

Deterministic logic gets unit tests, no live API calls: date normalization (relative dates, date-basis classification); clustering (preserves every value, correctly groups true duplicates vs. keeps repetitive-but-distinct events separate); conflict detection (produces a `conflict_group` rather than silently picking a value; authoritative-source rule applied correctly); salience tiering; JSON schema parse/validate/retry (mocked); scoring (severity-weighted math, the critical-error gate, weighted fact-coverage math); budget accounting/floor enforcement; a small end-to-end smoke test (tiny fixture case, no live calls) exercising discover → extract → project → schema-check. `python -m chronos.timeline check` is enforced in code before every real `/v1/summarize` call, not just documented.

## 16. Implementation order

1. `.gitignore` + `pyproject.toml` + scaffolding — no API calls.
2. `budget.py` + `llm.py` — smoke-test against the free `GET /v1/budget` only.
3. Risk-based source audit on the provided references, both cases (finish reading the two remaining unaudited Davis OCR documents as part of this step).
4. Chunking experiment on Vance only — freeze the config.
5. Full extraction pipeline on Vance, then Davis, using the frozen config.
6. Stage-0 timeline evaluation scoring, both cases.
7. Material-fact-set construction per case, frozen before any summary is judged.
8. Controlled benchmark: both cases' 8 supplied summaries scored directly (input identity confirmed for both — Davis via `input_timeline.json`, Vance via `golden/case-vance.timeline.json` per the hiring contact); optional fresh runs for either case only as a sanity check.
9. Judge calls and deterministic scoring — rubric/gate/fact-set already frozen from step 7, no post-hoc adjustment.
10. End-to-end pipeline demo, separate results path.
11. Optional sparse-input probe, if budget/time remain.
12. `results/` artifacts, `final_report.md`, `WRITEUP.md`.
13. CLI — thin layer over already-working, already-tested modules.
14. Tests written alongside each deterministic module in steps 4–9, not deferred.
15. Adversarial review pass before calling any of it done.

## 17. Acceptance criteria / known methodological limitations

- The controlled benchmark's shipping comparison never depends on our own extraction quality; the end-to-end pipeline never feeds the shipping recommendation.
- No score anywhere aggregates a tool letter across cases.
- Both cases' controlled benchmarks are scored identically and symmetrically, since exact input identity is confirmed for each (Davis by the shipped `input_timeline.json`, Vance by hiring-contact confirmation — `FINDINGS.md`).
- No high-materiality conflict is silently resolved into a confident fact.
- Coverage is measured against a fixed, case-specific, pre-frozen fact set — never every timeline row, never a category-level yes/no.
- **Known limitation**: Vance's input-identity confirmation rests on hiring-contact communication, not an artifact shipped in the repo (unlike Davis's `input_timeline.json`) — treated as established for scoring purposes, but its provenance is documented distinctly in `FINDINGS.md` rather than presented as independently repo-verified.
- **Known limitation**: exact severity-tier weights are not fixed in this document. Severity definitions/weights and the critical-error gate are finalized using predefined, source-verified calibration examples (`FINDINGS.md`) before primary controlled-benchmark scoring, then frozen — they must not be tuned after seeing primary leaderboard results. The chunking configuration is likewise not fixed here — it's determined by the frozen local dev-set experiment (§5). Both get recorded in `DECISIONS.md` once set.
- **Known limitation**: two Davis source documents remain unaudited as of this plan (`FINDINGS.md` — UNRESOLVED); flagged explicitly, not assumed clean.
