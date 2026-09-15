
# Final Scorecard — Controlled Summarizer Benchmark

Every score below is indexed `(case_id, tool_letter)`. A/B/C/D are case-local identifiers, not stable backends across cases (PLAN.md §1) — this table is never read as "tool X wins" across both rows, only per case.

## case-davis

| Tool | Faithfulness | Ship-eligible | Coverage | Usefulness | Stability (agree) | Critical cross-run conflicts | Mean cost/summary |
|---|---|---|---|---|---|---|---|
| A | 0.954 | yes | 0.872 | 3.93 | 0.944 | 0 | $0.0213 |
| B | 0.727 | **NO** | 0.792 | 4.36 | 0.812 | 2 | $0.02 |
| C | 0.863 | yes | 0.574 | 3.79 | 0.917 | 0 | $0.0046 |
| D | 0.923 | yes | 0.848 | 3.93 | 1.0 | 0 | $0.0213 |

## case-vance

| Tool | Faithfulness | Ship-eligible | Coverage | Usefulness | Stability (agree) | Critical cross-run conflicts | Mean cost/summary |
|---|---|---|---|---|---|---|---|
| A | 0.896 | **NO** | 0.892 | 4.14 | 1.0 | 0 | $0.0292 |
| B | 0.736 | **NO** | 0.869 | 4.21 | 0.722 | 0 | $0.0285 |
| C | 0.817 | **NO** | 0.489 | 3.79 | 0.6 | 0 | $0.0073 |
| D | 0.992 | yes | 0.938 | 4.64 | 0.909 | 1 | $0.0296 |
