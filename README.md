# Chronos — clinical timeline extraction & summarizer evaluation

Turns scanned/OCR'd medical records into a structured timeline, generates an attorney-facing narrative summary from it, and evaluates that summary — with the reasoning behind every score inspectable, not just the number.

**The actual recommendation (which summarizer to ship, why, and what would change that answer) is in [`WRITEUP.md`](WRITEUP.md).** This README is about running the application yourself.

## Setup

Requires Python 3.11+. No third-party dependencies for the application itself (`pytest` only if you want to run the test suite).

1. Copy `.env.example` to `.env` and fill in the two values (provided separately — never commit the real `.env`):
   ```
   INTERVIEW_BASE_URL=...
   INTERVIEW_API_KEY=...
   ```
2. That's it — nothing to install. Everything runs with `python -m ...` from this directory.

## Run it

The simplest way — no arguments, fully interactive:

```bash
python -m evalkit.cli
```

This lists every case it finds under `data/` (dynamically — drop in a new case with its own `data/<case-id>/manifest.json` + `ocr/` + `pdf/` and it appears here automatically, nothing to register), lets you pick one, then walks the whole pipeline: **read the case's documents → build a structured timeline → check the timeline's accuracy → generate a narrative summary → fact-check that summary → show you exactly which claims passed, which failed, and why.**

Every stage that calls the API prints what it's doing in plain language and the running cost against the shared budget.

### Individual stages

If you want to run one step at a time instead:

```bash
python -m evalkit.cli list-cases                       # free, no API calls
python -m evalkit.cli extract <case_id>                 # documents -> timeline
python -m evalkit.cli evaluate-timeline <case_id>        # checks the timeline's accuracy
python -m evalkit.cli summarize <case_id> <tool_letter>  # timeline -> narrative summary
python -m evalkit.cli evaluate <case_id> <summary_file>  # fact-checks a summary you already have
python -m evalkit.cli run <case_id> [--tool D]           # all of the above for one named case
```

`--help` on any of these (or `python -m evalkit.cli --help`) lists the full option set.

## What "evaluate" actually shows you

Every evaluation prints a plain-English breakdown — which specific claims in the summary were checked, which ones failed and exactly why (quoting the timeline text they contradict), and which of the case's material facts were covered, partially covered, or missed. The full underlying JSON (every claim's evidence, reasoning, and score) is also saved alongside it for deeper inspection.

The extraction side has the same treatment: `results/conflict_review_case-vance.md` and `case-davis.md` explain, in plain language, every place the pipeline found conflicting information across source documents and what it decided to do about it.

## Budget

All API calls (extraction, evaluation judging, summarization) draw from one shared budget. Every call prints its cost and what's left; nothing runs once the remaining balance drops below a safety floor. `runs/budget_log.jsonl` has the full, timestamped spend history.

## Where things are

| | |
|---|---|
| `WRITEUP.md` | **The recommendation** — which summarizer to ship, confidence, what would change it |
| `PLAN.md` | The evaluation methodology in full |
| `DECISIONS.md` | Every design decision, with the reasoning (including real bugs found and fixed along the way) |
| `FINDINGS.md` | Concrete data findings from the two test cases |
| `results/` | Every evaluation result, committed — readable without spending anything or rerunning code |
| `evalkit/` | The implementation |
| `tests/` | The test suite (`pytest`), no live API calls |
| `chronos/` | Provided, read-only — the API client and the strict timeline schema |

## Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

No live API calls — pure logic, run freely.
