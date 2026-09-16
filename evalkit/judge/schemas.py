"""Expected JSON shapes for every judge in evalkit/judge/ (PLAN.md S10).

Lightweight, structural validation only -- not a full JSON-schema library
dependency (the project stays stdlib-only, matching chronos/'s own
philosophy). Each judge module validates its own call_json() output against
these before scoring.py touches it.
"""

from __future__ import annotations

import re
from typing import Any

CLAIM_STATUS_VALUES = ("supported", "unsupported", "contradicted", "overclaimed")
MATERIALITY_VALUES = ("critical", "major", "minor")
REFLECTED_VALUES = ("yes", "no", "partial")
RELATION_VALUES = ("agree", "disagree", "run1_only", "run2_only")

USEFULNESS_DIMENSIONS = (
    "chronological_clarity", "concision", "organization", "preserves_uncertainty",
    "separates_pre_existing_vs_post", "emphasis_on_material_facts", "avoids_repetitive_clutter",
)


class SchemaError(ValueError):
    pass


def _normalize_for_substring_check(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def validate_faithfulness_coverage_output(result: dict[str, Any], summary_text: str) -> None:
    """`summary_text` is now required, not optional -- every claim must be
    STRUCTURALLY validated against it here, not filtered out later by a
    heuristic over the judge's own `reason` text (FINDINGS.md: that
    heuristic was found operating on 100% of the real committed benchmark
    data, since summary_quote was never actually enforced, and it
    demonstrably misclassified a genuine major-materiality unsupported
    claim as an omission just because its `reason` happened to contain
    "does not state"). A claim's `summary_quote` must be non-empty and an
    actual (whitespace-normalized) substring of the summary it's judging --
    if it isn't, the WHOLE judge output is invalid and must be retried,
    never silently patched around by excluding just that one claim from
    the denominator."""
    if "claims" not in result or not isinstance(result["claims"], list):
        raise SchemaError("missing or non-list 'claims'")
    normalized_summary = _normalize_for_substring_check(summary_text)
    for c in result["claims"]:
        if c.get("status") not in CLAIM_STATUS_VALUES:
            raise SchemaError(f"claim has invalid status: {c.get('status')!r}")
        if c.get("materiality") not in MATERIALITY_VALUES:
            raise SchemaError(f"claim has invalid materiality: {c.get('materiality')!r}")
        quote = c.get("summary_quote")
        if not isinstance(quote, str) or not quote.strip():
            raise SchemaError(f"claim {c.get('claim_id')!r} has no summary_quote -- every claim must be traceable to actual summary text")
        if _normalize_for_substring_check(quote) not in normalized_summary:
            raise SchemaError(
                f"claim {c.get('claim_id')!r}'s summary_quote {quote!r} is not an actual substring of the summary"
            )
    if "fact_coverage" not in result or not isinstance(result["fact_coverage"], list):
        raise SchemaError("missing or non-list 'fact_coverage'")
    for fc in result["fact_coverage"]:
        if fc.get("reflected") not in REFLECTED_VALUES:
            raise SchemaError(f"fact_coverage entry has invalid reflected: {fc.get('reflected')!r}")
    usefulness = result.get("usefulness")
    if not isinstance(usefulness, dict):
        raise SchemaError("missing or non-dict 'usefulness'")


def validate_stability_output(result: dict[str, Any]) -> None:
    if "claim_pairs" not in result or not isinstance(result["claim_pairs"], list):
        raise SchemaError("missing or non-list 'claim_pairs'")
    for cp in result["claim_pairs"]:
        if cp.get("relation") not in RELATION_VALUES:
            raise SchemaError(f"claim_pair has invalid relation: {cp.get('relation')!r}")
