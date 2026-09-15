# Chunking experiment (PLAN.md S5)

Frozen local dev set built before any configuration ran (see `DEV_SET` in `evalkit/extraction/chunk_experiment.py`), scored with deterministic keyword+date matching -- not a semantic judge call, kept cheap and transparent. `unsupported_rate` is approximate (candidates not matching any dev-set keyword; for `billing_window` the dev set is not exhaustive of every line item, so this overstates true unsupported claims there -- `therapy_window`'s dev set IS exhaustive of its 12 real events, so its unsupported_rate is a cleaner signal).

| Config | Window | Calls | Cost | Recall | Date fidelity | Duplicate rate | Unsupported rate | Trap aware |
|---|---|---|---|---|---|---|---|---|
| small | billing_window | 6 | $0.7507 | 100% | 100% | 55% | 80% | yes |
| small | prior_records | 2 | $0.1021 | 100% | 100% | 45% | 27% | n/a |
| small | therapy_window | 6 | $0.3382 | 100% | 100% | 72% | 24% | n/a |
| medium | billing_window | 3 | $0.5321 | 100% | 100% | 49% | 76% | yes |
| medium | prior_records | 1 | $0.0685 | 100% | 100% | 20% | 27% | n/a |
| medium | therapy_window | 3 | $0.2060 | 100% | 100% | 53% | 40% | n/a |
| large | billing_window | 2 | $0.3902 | 100% | 100% | 38% | 81% | yes |
| large | prior_records | 1 | $0.0628 | 100% | 100% | 21% | 21% | n/a |
| large | therapy_window | 2 | $0.1445 | 100% | 100% | 45% | 34% | n/a |

| Config | Total calls | Total cost |
|---|---|---|
| small | 14 | $1.1909 |
| medium | 7 | $0.8065 |
| large | 5 | $0.5975 |