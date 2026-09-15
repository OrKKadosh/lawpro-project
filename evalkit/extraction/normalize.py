"""Deterministic normalization pass over raw candidate events (PLAN.md S3).

The extraction call already asks the model for normalized_date/date_basis/
status/etc, but LLM output needs validation before anything downstream
trusts it -- this pass enforces the allowed enums, validates ISO dates, and
fills safe, honest defaults for malformed or missing fields rather than
silently propagating garbage. No LLM call here.
"""

from __future__ import annotations

from datetime import date as _date
from typing import Any

EVENT_TYPES = ("encounter", "imaging", "medication", "procedure", "therapy", "diagnosis")
STATUS_VALUES = (
    "performed", "ordered", "recommended", "planned", "considered", "cancelled", "reported_history"
)
DATE_BASIS_VALUES = (
    "explicit_event_date", "relative_to_note_date", "note_signing_date",
    "billing_service_date", "inferred", "unknown",
)
ASSERTED_BY_VALUES = ("patient_reported", "clinician_observed", "clinician_opinion", "billing_system")
CERTAINTY_VALUES = ("confirmed", "suspected", "uncertain")
MATERIALITY_VALUES = ("high", "relevant", "routine")
TEMPORAL_RELATION_VALUES = ("pre-incident", "index-incident", "post-incident", "unknown")


def _valid_iso_date(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 10:
        return False
    try:
        _date.fromisoformat(value)
        return True
    except ValueError:
        return False


def _clamp01(value: Any, default: float = 0.5) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, v))


def normalize_candidate(raw: dict[str, Any]) -> dict[str, Any]:
    """Validate and coerce one raw candidate dict into a clean shape.

    Unknown/malformed enum values fall back to the most conservative,
    honest option rather than a guess dressed up as certainty.
    """
    event_type = raw.get("event_type_candidate")
    if event_type not in EVENT_TYPES:
        event_type = "encounter"  # most conservative fallback: least specific claim

    status = raw.get("status")
    if status not in STATUS_VALUES:
        status = "reported_history"  # do not default to "performed" -- that overclaims

    date_basis = raw.get("date_basis")
    if date_basis not in DATE_BASIS_VALUES:
        date_basis = "unknown"

    normalized_date = raw.get("normalized_date")
    if not _valid_iso_date(normalized_date):
        normalized_date = None
        if date_basis not in ("unknown", "inferred"):
            date_basis = "unknown"  # a claimed basis with no valid date is not honest

    attribution_raw = raw.get("attribution") or {}
    asserted_by = attribution_raw.get("asserted_by")
    if asserted_by not in ASSERTED_BY_VALUES:
        asserted_by = "clinician_observed"
    certainty = attribution_raw.get("certainty")
    if certainty not in CERTAINTY_VALUES:
        certainty = "uncertain"

    materiality = raw.get("materiality_hint")
    if materiality not in MATERIALITY_VALUES:
        materiality = "relevant"

    temporal_relation = raw.get("temporal_relation_to_incident")
    if temporal_relation not in TEMPORAL_RELATION_VALUES:
        temporal_relation = "unknown"

    clinical_facts_raw = raw.get("clinical_facts")
    clinical_facts = clinical_facts_raw if isinstance(clinical_facts_raw, dict) else {}
    for key in ("concept", "body_site", "laterality", "diagnosis_or_finding", "procedure", "medication", "dose"):
        clinical_facts.setdefault(key, None)

    return {
        "source_doc_id": raw.get("source_doc_id"),
        "source_page": raw.get("source_page"),
        "evidence_text": str(raw.get("evidence_text", ""))[:600],
        "raw_date": raw.get("raw_date"),
        "normalized_date": normalized_date,
        "date_basis": date_basis,
        "date_confidence": _clamp01(raw.get("date_confidence")),
        "event_type_candidate": event_type,
        "status": status,
        "attribution": {
            "asserted_by": asserted_by,
            "provider": attribution_raw.get("provider") or None,
            "certainty": certainty,
        },
        "temporal_relation_to_incident": temporal_relation,
        "materiality_hint": materiality,
        "extraction_confidence": _clamp01(raw.get("extraction_confidence")),
        "clinical_facts": clinical_facts,
        "raw_summary": str(raw.get("raw_summary", ""))[:300],
    }


def normalize_candidates(raw_candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_candidate(c) for c in raw_candidates]
