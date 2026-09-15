"""Assembles the canonical event from each cluster's resolved/flagged
fields (PLAN.md S3/S6).

Three outcomes per conflicted field, exactly as specified:
- auto-resolved: conflict.py found an unambiguous authoritative value ->
  used directly, losing values kept in `evidence`, never dropped.
- high-materiality, resolved with confidence: same mechanism -- the bar is
  the same authoritative-source rule, not a separate relaxed one.
- high-materiality, unresolved: needs_review=True, and the canonical event
  does NOT get a confidently-worded value for that field. The field is left
  None here; project.py is responsible for expressing that honestly (a null
  date, or a hedged detail sentence) rather than silently guessing.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any, Optional

from evalkit.extraction.cluster import Cluster
from evalkit.extraction.conflict import ConflictRecord, _field_value

MATERIALITY_ORDER = {"high": 3, "relevant": 2, "routine": 1}


@dataclass
class CanonicalEvent:
    canonical_id: str
    member_candidate_ids: list[int]
    date: Optional[str]
    date_basis: Optional[str]
    type: Optional[str]
    status: Optional[str]
    clinical_facts: dict[str, Any]
    attribution: dict[str, Any]
    materiality: str
    confidence: float
    conflict_group_id: Optional[str]
    needs_review: bool
    review_reasons: list[str] = dc_field(default_factory=list)
    evidence: list[dict[str, Any]] = dc_field(default_factory=list)


def _majority_or_single(values: list[Any]) -> Any:
    values = [v for v in values if v not in (None, "")]
    if not values:
        return None
    return max(set(values), key=values.count)


def canonicalize_clusters(
    clusters: list[Cluster], candidates: list[dict[str, Any]], conflicts: list[ConflictRecord]
) -> list[CanonicalEvent]:
    conflicts_by_cluster: dict[str, list[ConflictRecord]] = {}
    for c in conflicts:
        conflicts_by_cluster.setdefault(c.cluster_id, []).append(c)

    canonical_events: list[CanonicalEvent] = []
    for cluster in clusters:
        members = cluster.members(candidates)
        cluster_conflicts = {c.field: c for c in conflicts_by_cluster.get(cluster.cluster_id, [])}
        review_reasons: list[str] = []
        needs_review = False

        def resolve(field_name: str, fallback_values: list[Any]) -> Any:
            nonlocal needs_review
            conflict = cluster_conflicts.get(field_name)
            if conflict is None:
                return _majority_or_single(fallback_values)
            if not conflict.needs_review:
                return conflict.suggested_resolution
            needs_review = True
            review_reasons.append(f"unresolved conflict on '{field_name}'")
            return None

        date = resolve("normalized_date", [m.get("normalized_date") for m in members])
        date_basis = _majority_or_single([m.get("date_basis") for m in members])
        status = resolve("status", [m.get("status") for m in members])
        event_type = _majority_or_single([m.get("event_type_candidate") for m in members])
        provider = resolve("provider", [(m.get("attribution") or {}).get("provider") for m in members])

        clinical_facts: dict[str, Any] = {}
        for cf_field in ("concept", "body_site", "laterality", "diagnosis_or_finding", "procedure", "medication", "dose"):
            clinical_facts[cf_field] = resolve(
                cf_field, [(m.get("clinical_facts") or {}).get(cf_field) for m in members]
            )

        materiality = max(
            (m.get("materiality_hint", "relevant") for m in members),
            key=lambda mh: MATERIALITY_ORDER.get(mh, 0),
        )
        confidence = sum(m.get("extraction_confidence", 0.5) for m in members) / len(members)
        if needs_review:
            confidence = min(confidence, 0.5)  # an unresolved conflict caps how confident we claim to be

        evidence = []
        for m in members:
            entry = {
                "doc": m.get("source_doc_id"), "page": m.get("source_page"),
                "snippet": m.get("evidence_text"),
            }
            # note any field where this member's value lost a conflict resolution
            notes = []
            for field_name, conflict in cluster_conflicts.items():
                if conflict.needs_review or conflict.suggested_resolution is None:
                    continue
                this_value = _field_value(m, field_name)
                if this_value not in (None, "") and this_value != conflict.suggested_resolution:
                    notes.append(f"conflicting {field_name}={this_value!r}, not used -- see resolution policy")
            if notes:
                entry["note"] = "; ".join(notes)
            evidence.append(entry)

        canonical_events.append(
            CanonicalEvent(
                canonical_id=cluster.cluster_id,
                member_candidate_ids=cluster.member_indices,
                date=date,
                date_basis=date_basis,
                type=event_type,
                status=status,
                clinical_facts=clinical_facts,
                attribution={
                    "provider": provider,
                    "asserted_by": _majority_or_single([(m.get("attribution") or {}).get("asserted_by") for m in members]),
                    "certainty": _majority_or_single([(m.get("attribution") or {}).get("certainty") for m in members]),
                },
                materiality=materiality,
                confidence=confidence,
                conflict_group_id=cluster.cluster_id if cluster_conflicts else None,
                needs_review=needs_review,
                review_reasons=review_reasons,
                evidence=evidence,
            )
        )

    return canonical_events
