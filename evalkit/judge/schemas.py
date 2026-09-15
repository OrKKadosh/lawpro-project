"""Expected JSON shapes for every judge in evalkit/judge/ (PLAN.md S10).

Lightweight, structural validation only -- not a full JSON-schema library
dependency (the project stays stdlib-only, matching chronos/'s own
philosophy). Each judge module validates its own call_json() output against
these before scoring.py touches it.
"""

from __future__ import annotations

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


def validate_faithfulness_coverage_output(result: dict[str, Any]) -> None:
    if "claims" not in result or not isinstance(result["claims"], list):
        raise SchemaError("missing or non-list 'claims'")
    for c in result["claims"]:
        if c.get("status") not in CLAIM_STATUS_VALUES:
            raise SchemaError(f"claim has invalid status: {c.get('status')!r}")
        if c.get("materiality") not in MATERIALITY_VALUES:
            raise SchemaError(f"claim has invalid materiality: {c.get('materiality')!r}")
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
