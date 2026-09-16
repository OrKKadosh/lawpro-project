# Final Scorecard — Controlled Summarizer Benchmark

Every score below is indexed `(case_id, tool_letter)`. A/B/C/D are case-local identifiers, not stable backends across cases (PLAN.md §1) — this table is never read as "tool X wins" across both rows, only per case.

## case-vance

| Tool | Faithfulness | Ship-eligible | Coverage | Usefulness | Shared-topic agreement | Content-overlap stability | Critical cross-run conflicts | Mean cost/summary |
|---|---|---|---|---|---|---|---|---|
| A | 0.949 | **NO** | 0.875 | 4.57 | 1.0 | 0.72 | 0 | $0.0292 |
| B | 0.831 | **NO** | 0.88 | 4.57 | 0.706 | 0.6 | 0 | $0.0285 |
| C | 0.969 | yes | 0.449 | 3.79 | 0.333 | 0.286 | 0 | $0.0073 |
| D | 1.0 | yes | 0.898 | 4.57 | 0.867 | 0.619 | 1 | $0.0296 |

*Shared-topic agreement* = agree / (agree + disagree) across material facts BOTH runs mention -- silent on content only one run mentions. *Content-overlap stability* = agree / (agree + disagree + run1-only + run2-only) -- the number that actually catches a run silently dropping or adding a large chunk of material content (FINDINGS.md: shared-topic agreement alone can show 1.0 even when one run omits most of the other's material facts -- never read that number alone as "stability").

## case-davis

| Tool | Faithfulness | Ship-eligible | Coverage | Usefulness | Shared-topic agreement | Content-overlap stability | Critical cross-run conflicts | Mean cost/summary |
|---|---|---|---|---|---|---|---|---|
| A | 0.992 | yes | 0.817 | 3.93 | 0.938 | 0.882 | 0 | $0.0213 |
| B | 0.807 | **NO** | 0.786 | 4.57 | 0.833 | 0.75 | 2 | $0.02 |
| C | 1.0 | yes | 0.494 | 3.93 | 1.0 | 0.625 | 0 | $0.0046 |
| D | 1.0 | yes | 0.836 | 3.93 | 0.944 | 0.708 | 0 | $0.0213 |

*Shared-topic agreement* = agree / (agree + disagree) across material facts BOTH runs mention -- silent on content only one run mentions. *Content-overlap stability* = agree / (agree + disagree + run1-only + run2-only) -- the number that actually catches a run silently dropping or adding a large chunk of material content (FINDINGS.md: shared-topic agreement alone can show 1.0 even when one run omits most of the other's material facts -- never read that number alone as "stability").
