# Final Scorecard — Controlled Summarizer Benchmark

Every score below is indexed `(case_id, tool_letter)`. A/B/C/D are case-local identifiers, not stable backends across cases (PLAN.md §1) — this table is never read as "tool X wins" across both rows, only per case.

## case-vance

| Tool | Faithfulness | Ship-eligible | Coverage | Usefulness | Shared-topic agreement | Content-overlap stability | Critical cross-run conflicts | Mean cost/summary |
|---|---|---|---|---|---|---|---|---|
| A | 0.896 | **NO** | 0.892 | 4.14 | 1.0 | 0.7 | 0 | $0.0292 |
| B | 0.736 | **NO** | 0.869 | 4.21 | 0.722 | 0.591 | 0 | $0.0285 |
| C | 0.927 | **NO** | 0.489 | 3.79 | 0.6 | 0.429 | 0 | $0.0073 |
| D | 1.0 | yes | 0.938 | 4.64 | 0.909 | 0.625 | 1 | $0.0296 |

*Shared-topic agreement* = agree / (agree + disagree) across material facts BOTH runs mention -- silent on content only one run mentions. *Content-overlap stability* = agree / (agree + disagree + run1-only + run2-only) -- the number that actually catches a run silently dropping or adding a large chunk of material content (FINDINGS.md: shared-topic agreement alone can show 1.0 even when one run omits most of the other's material facts -- never read that number alone as "stability").

## case-davis

| Tool | Faithfulness | Ship-eligible | Coverage | Usefulness | Shared-topic agreement | Content-overlap stability | Critical cross-run conflicts | Mean cost/summary |
|---|---|---|---|---|---|---|---|---|
| A | 0.983 | yes | 0.872 | 3.93 | 0.944 | 0.85 | 0 | $0.0213 |
| B | 0.752 | **NO** | 0.792 | 4.36 | 0.812 | 0.812 | 2 | $0.02 |
| C | 0.99 | yes | 0.574 | 3.79 | 0.917 | 0.647 | 0 | $0.0046 |
| D | 0.969 | yes | 0.848 | 3.93 | 1.0 | 0.773 | 0 | $0.0213 |

*Shared-topic agreement* = agree / (agree + disagree) across material facts BOTH runs mention -- silent on content only one run mentions. *Content-overlap stability* = agree / (agree + disagree + run1-only + run2-only) -- the number that actually catches a run silently dropping or adding a large chunk of material content (FINDINGS.md: shared-topic agreement alone can show 1.0 even when one run omits most of the other's material facts -- never read that number alone as "stability").
