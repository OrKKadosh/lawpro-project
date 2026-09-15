# Extraction prompt iteration experiment

Follow-up to `results/chunking_experiment.md`. Chunk size held fixed at the already-frozen `large` config; this experiment varies only the extraction system prompt (`evalkit/extraction/prompt_experiment.py`). Same frozen-dev-set methodology, plus two new trap checks read directly from real OCR text: a CPT-code-grounding trap (`billing_window`) and an attending-vs-consulted-physician attribution trap (`ems_window`, new).

| Variant | Window | Calls | Cost | Recall | Date fidelity | Duplicate rate | Unsupported rate | Grounding trap | Attribution trap |
|---|---|---|---|---|---|---|---|---|---|
| baseline | billing_window | 2 | $0.3902 | 100% | 100% | 35% | 65% | VIOLATED | n/a |
| baseline | prior_records | 1 | $0.0620 | 100% | 100% | 17% | 8% | n/a | n/a |
| baseline | therapy_window | 2 | $0.1356 | 100% | 100% | 32% | 8% | n/a | n/a |
| baseline | ems_window | 1 | $0.1538 | 100% | 100% | 84% | 41% | n/a | correct |
| reinforced | billing_window | 2 | $0.3921 | 100% | 100% | 38% | 67% | clean | n/a |
| reinforced | prior_records | 1 | $0.0562 | 100% | 100% | 9% | 18% | n/a | n/a |
| reinforced | therapy_window | 2 | $0.1251 | 100% | 100% | 33% | 8% | n/a | n/a |
| reinforced | ems_window | 1 | $0.1329 | 100% | 100% | 83% | 38% | n/a | correct |

| Variant | Total calls | Total cost |
|---|---|---|
| baseline | 6 | $0.7417 |
| reinforced | 6 | $0.7063 |