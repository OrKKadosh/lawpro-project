"""Review queue + safe auto-resolution (PLAN.md S6/SG).

Turns conflict.py's records (plus a few other deterministic triggers) into
a prioritized HITL queue: materiality x uncertainty, sorted descending,
default view surfaces priority >= 4. Also decides, per conflict, whether
it's safe to auto-resolve (conflict.py already found an unambiguous
authoritative value) or must stay flagged for canonicalize.py to handle per
the unresolved-conflict policy (PLAN.md S6: a high-materiality unresolved
conflict never becomes a confidently-worded final fact).
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any

from evalkit.extraction.cluster import Cluster
from evalkit.extraction.conflict import ConflictRecord

MATERIALITY_WEIGHT = {"high": 3, "relevant": 2, "routine": 1}
DEFAULT_VIEW_THRESHOLD = 4

REASONS = (
    "SOURCE_CONFLICT", "AMBIGUOUS_DATE", "POSSIBLE_DUPLICATE", "OCR_CORRUPTION",
    "UNCLEAR_PERFORMED_VS_PLANNED", "LOW_EXTRACTION_CONFIDENCE",
    "HIGH_MATERIALITY_LOW_CONFIDENCE", "CAUSATION_AMBIGUITY", "NEGATION_UNCERTAIN",
    "TYPE_AMBIGUITY", "OUTLIER_VALUE",
)

_CAUSATION_KEYWORDS = ("pre-exist", "preexist", "causat", "exacerbat", "aggravat")
_PLANNED_STATUSES = {"ordered", "recommended", "planned", "considered"}


@dataclass
class HITLItem:
    cluster_id: str
    materiality: str
    uncertainty: str
    priority: int
    reasons: list[str] = dc_field(default_factory=list)
    conflicts: list[ConflictRecord] = dc_field(default_factory=list)
    evidence: list[dict] = dc_field(default_factory=list)


def _cluster_materiality(members: list[dict]) -> str:
    order = {"high": 3, "relevant": 2, "routine": 1}
    return max(members, key=lambda m: order.get(m.get("materiality_hint"), 0))["materiality_hint"]


def _cluster_uncertainty(members: list[dict], has_unresolved_conflict: bool) -> str:
    if has_unresolved_conflict:
        return "high"
    avg_conf = sum(m.get("extraction_confidence", 0.5) for m in members) / len(members)
    if avg_conf < 0.5:
        return "high"
    if avg_conf < 0.75:
        return "medium"
    return "low"


def build_hitl_queue(
    clusters: list[Cluster], candidates: list[dict[str, Any]], conflicts: list[ConflictRecord]
) -> list[HITLItem]:
    conflicts_by_cluster: dict[str, list[ConflictRecord]] = {}
    for c in conflicts:
        conflicts_by_cluster.setdefault(c.cluster_id, []).append(c)

    uncertainty_weight = {"high": 3, "medium": 2, "low": 1}
    items: list[HITLItem] = []

    for cluster in clusters:
        members = cluster.members(candidates)
        cluster_conflicts = conflicts_by_cluster.get(cluster.cluster_id, [])
        unresolved = [c for c in cluster_conflicts if c.needs_review]

        materiality = _cluster_materiality(members)
        uncertainty = _cluster_uncertainty(members, bool(unresolved))
        priority = MATERIALITY_WEIGHT[materiality] * uncertainty_weight[uncertainty]

        reasons: list[str] = []
        if unresolved:
            reasons.append("SOURCE_CONFLICT")
            if any(c.field == "normalized_date" for c in unresolved):
                reasons.append("AMBIGUOUS_DATE")
        if len(members) > 3:
            reasons.append("POSSIBLE_DUPLICATE")
        if any(m.get("extraction_confidence", 1.0) < 0.5 for m in members):
            reasons.append("LOW_EXTRACTION_CONFIDENCE")
        if materiality == "high" and any(m.get("extraction_confidence", 1.0) < 0.6 for m in members):
            reasons.append("HIGH_MATERIALITY_LOW_CONFIDENCE")
        if materiality == "high" and any(m.get("status") in _PLANNED_STATUSES for m in members):
            reasons.append("UNCLEAR_PERFORMED_VS_PLANNED")
        text_blob = " ".join(
            (m.get("evidence_text", "") + " " + str((m.get("clinical_facts") or {}).get("diagnosis_or_finding") or ""))
            .lower()
            for m in members
        )
        if any(kw in text_blob for kw in _CAUSATION_KEYWORDS):
            reasons.append("CAUSATION_AMBIGUITY")
        if len({m.get("event_type_candidate") for m in members}) > 1:
            reasons.append("TYPE_AMBIGUITY")

        if not reasons:
            continue  # nothing worth surfacing for this cluster

        items.append(
            HITLItem(
                cluster_id=cluster.cluster_id,
                materiality=materiality,
                uncertainty=uncertainty,
                priority=priority,
                reasons=reasons,
                conflicts=cluster_conflicts,
                evidence=[
                    {"doc": m.get("source_doc_id"), "page": m.get("source_page"), "text": m.get("evidence_text")}
                    for m in members
                ],
            )
        )

    items.sort(key=lambda it: it.priority, reverse=True)
    return items


def default_view(items: list[HITLItem]) -> list[HITLItem]:
    return [it for it in items if it.priority >= DEFAULT_VIEW_THRESHOLD]
