"""Field-level conflict detection inside/across clusters (PLAN.md S3/S6).

For every cluster with more than one member, checks whether date, status,
provider, or clinical_facts fields actually agree. Where they don't,
produces a conflict_group record rather than silently picking a value.
Resolution principle: prefer the source most directly authoritative for
the SPECIFIC field in question (an operative report's explicit date beats
a billing form's service date; a clinician's direct observation beats a
billing-system attribution) -- never a blanket "document A always wins"
hierarchy. Deterministic, no LLM call.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any, Optional

from evalkit.extraction.cluster import Cluster

# Lower rank = more authoritative for that field. Ties are genuine conflicts.
DATE_BASIS_RANK = {
    "explicit_event_date": 1,
    "inferred": 2,
    "relative_to_note_date": 3,
    "note_signing_date": 3,
    "billing_service_date": 4,
    "unknown": 5,
}
ASSERTED_BY_RANK = {
    "clinician_observed": 1,
    "clinician_opinion": 2,
    "patient_reported": 3,
    "billing_system": 4,
}

FIELDS_CHECKED = ("normalized_date", "status", "provider")
CLINICAL_FACT_FIELDS = ("concept", "body_site", "laterality", "diagnosis_or_finding", "procedure", "medication", "dose")


@dataclass
class ConflictRecord:
    conflict_group_id: str
    cluster_id: str
    field: str
    candidate_values: list[dict[str, Any]] = dc_field(default_factory=list)
    suggested_resolution: Optional[Any] = None
    resolution_reason: str = ""
    needs_review: bool = True


def _field_value(candidate: dict, field_name: str) -> Any:
    if field_name == "provider":
        return (candidate.get("attribution") or {}).get("provider")
    if field_name in CLINICAL_FACT_FIELDS:
        return (candidate.get("clinical_facts") or {}).get(field_name)
    return candidate.get(field_name)


def _authority_rank(candidate: dict, field_name: str) -> int:
    if field_name == "normalized_date":
        return DATE_BASIS_RANK.get(candidate.get("date_basis"), 5)
    if field_name == "provider":
        asserted_by = (candidate.get("attribution") or {}).get("asserted_by")
        return ASSERTED_BY_RANK.get(asserted_by, 4)
    # status / clinical_facts fields: fall back to extraction confidence, inverted to a rank
    return round((1.0 - candidate.get("extraction_confidence", 0.5)) * 10)


def _source_label(candidate: dict) -> str:
    return f"{candidate.get('source_doc_id')} p{candidate.get('source_page')}"


def detect_conflicts(
    clusters: list[Cluster], candidates: list[dict[str, Any]]
) -> list[ConflictRecord]:
    conflicts: list[ConflictRecord] = []
    for cluster in clusters:
        members = cluster.members(candidates)
        if len(members) < 2:
            continue

        fields_to_check = list(FIELDS_CHECKED) + [
            f for f in CLINICAL_FACT_FIELDS if any((m.get("clinical_facts") or {}).get(f) for m in members)
        ]

        for field_name in fields_to_check:
            values_present = [(m, _field_value(m, field_name)) for m in members]
            values_present = [(m, v) for m, v in values_present if v not in (None, "")]
            distinct_values = {v for _, v in values_present}
            if len(distinct_values) <= 1:
                continue  # agreement (or only one source states it) -- not a conflict

            ranked = sorted(values_present, key=lambda mv: _authority_rank(mv[0], field_name))
            best_rank = _authority_rank(ranked[0][0], field_name)
            top_values = {v for m, v in ranked if _authority_rank(m, field_name) == best_rank}

            record = ConflictRecord(
                conflict_group_id=f"{cluster.cluster_id}-{field_name}",
                cluster_id=cluster.cluster_id,
                field=field_name,
                candidate_values=[
                    {"value": v, "source": _source_label(m), "authority_rank": _authority_rank(m, field_name)}
                    for m, v in values_present
                ],
            )
            if len(top_values) == 1:
                record.suggested_resolution = next(iter(top_values))
                record.resolution_reason = (
                    f"Unambiguous: only one value comes from the most-authoritative source "
                    f"available for '{field_name}' among this cluster's members."
                )
                record.needs_review = False
            else:
                record.suggested_resolution = None
                record.resolution_reason = (
                    f"Multiple equally-authoritative-ranked sources disagree on '{field_name}' "
                    f"({len(top_values)} distinct values tied) -- no unambiguous resolution."
                )
                record.needs_review = True
            conflicts.append(record)

    return conflicts
