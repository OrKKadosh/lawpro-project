# Historical results — not current final evidence

Files here are **superseded** by a later fix and are kept only for provenance, not as current reviewer-facing evidence. None of them ever fed the controlled summarizer benchmark or the shipping recommendation (`WRITEUP.md`), which is unaffected.

## `timeline_eval/`

`case-vance.json`, `case-davis.json` (Stage-0 extraction-vs-golden scoring + candidate source-audit coverage) and `case-vance_source_audit.json`, `case-davis_source_audit.json` (reference-timeline source audit) were all generated **before** `evalkit/reference/audit.py`'s page-scoping fix (the judge used to receive an entire OCR document instead of just the cited page, so it could not distinguish "supported on the cited page" from "exists somewhere else in the document" — see `FINDINGS.md`).

Regenerating all four with the corrected methodology would need 4 separate live audit runs (~$0.35–0.75 each, based on this project's own logged costs) — remaining API budget was deliberately reserved for the controlled benchmark and the corrected end-to-end path instead, which are the parts of this exercise actually graded on evaluation methodology. See `WRITEUP.md`'s note on this and `FINDINGS.md` for the full account.

These numbers are **not current** and must not be cited as final evidence of extraction/source-grounding accuracy. The audit *implementation* is fixed and tested (`tests/test_audit.py`); only these specific pre-fix result files are stale.
