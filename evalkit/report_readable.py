"""Human-readable conflict/HITL review, rendered directly from a case's
already-extracted candidate timeline (runs/candidate_timelines/<case>.json).
Deterministic, no LLM call, no new API cost -- re-runs the existing
deterministic pipeline stages (already free, since they're pure code) on
the cached candidates purely to recover cluster/conflict/canonical object
linkage, which the saved JSON doesn't preserve directly.

Built in direct response to a concrete problem: reading the raw JSON
wasn't enough to tell, for cluster cl003, that it was one real vitals
check documented independently by three different people with no way to
credit a single provider (PROGRESS.md/DECISIONS.md). This module is the
"simplify what's shown, not the pipeline" fix for that.
"""

from __future__ import annotations

import json
from pathlib import Path

from evalkit.extraction.canonicalize import CanonicalEvent, canonicalize_clusters
from evalkit.extraction.cluster import Cluster, cluster_candidates
from evalkit.extraction.conflict import ConflictRecord, detect_conflicts
from evalkit.extraction.hitl import build_hitl_queue
from evalkit.extraction.normalize import normalize_candidates
from evalkit.extraction.project import project_event
from evalkit.extraction.salience import select_material_timeline_events

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"
CANDIDATE_TIMELINES_DIR = Path(__file__).resolve().parents[1] / "runs" / "candidate_timelines"

FIELD_LABELS = {
    "normalized_date": "the date",
    "provider": "who documented it",
    "status": "whether it happened, was planned, or was just ordered",
}


def _source_label(candidate: dict) -> str:
    return f"{candidate.get('source_doc_id')} p{candidate.get('source_page')}"


def _field_label(field: str) -> str:
    return FIELD_LABELS.get(field, field.replace("_", " "))


def _render_conflict(conflict: ConflictRecord) -> str:
    values = ", ".join(f'"{v["value"]}" ({v["source"]})' for v in conflict.candidate_values)
    label = _field_label(conflict.field)
    if conflict.needs_review:
        return f"They disagree on {label}: {values}. {conflict.resolution_reason}"
    return f'They initially disagreed on {label} ({values}), but this resolved to "{conflict.suggested_resolution}" -- {conflict.resolution_reason}'


def _outcome_sentence(event: CanonicalEvent, was_selected: bool) -> str:
    if not was_selected:
        return (
            "This is a routine, repetitive-type event -- it was compressed out of the final "
            "timeline (grouped with similar routine visits, not because of the disagreement above)."
        )
    final = project_event(event)
    if final is None:
        if event.needs_review and event.materiality != "high":
            return (
                "Because of the unresolved disagreement above, and since this event isn't "
                "high-materiality, it was left out of the final timeline entirely rather than guessed."
            )
        return "It was left out of the final timeline -- nothing groundable enough to state could be composed."
    date_note = ""
    if final.get("date") is None and event.date:
        date_note = " (its date was left blank/null, since the date itself was one of the disputed fields)"
    return f'It IS in the final timeline{date_note}: "{final.get("detail")}"'


def render_case_review(case_id: str) -> str:
    path = CANDIDATE_TIMELINES_DIR / f"{case_id}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    candidates = normalize_candidates(data["candidates"])
    clusters = cluster_candidates(candidates, id_prefix=case_id)
    conflicts = detect_conflicts(clusters, candidates)
    hitl_queue = build_hitl_queue(clusters, candidates, conflicts)
    canonical = canonicalize_clusters(clusters, candidates, conflicts)
    selected_ids = {e.canonical_id for e in select_material_timeline_events(canonical)}

    conflicts_by_cluster: dict[str, list[ConflictRecord]] = {}
    for c in conflicts:
        conflicts_by_cluster.setdefault(c.cluster_id, []).append(c)
    hitl_by_cluster = {it.cluster_id: it for it in hitl_queue}
    clusters_by_id: dict[str, Cluster] = {c.cluster_id: c for c in clusters}
    canonical_by_id: dict[str, CanonicalEvent] = {e.canonical_id: e for e in canonical}

    interesting_ids = sorted(set(conflicts_by_cluster) | set(hitl_by_cluster))

    lines = [f"# Conflict review -- {case_id}", ""]
    lines.append(
        f"{len(interesting_ids)} of {len(clusters)} clusters had at least one field disagreement "
        f"or a HITL-queue flag; everything else clustered and resolved cleanly and isn't listed "
        f"below. Generated directly from `runs/candidate_timelines/{case_id}.json` -- deterministic, "
        f"no live judging, reproducible any time by re-running `python -m evalkit.report_readable`."
    )
    lines.append("")

    for cid in interesting_ids:
        cluster = clusters_by_id.get(cid)
        event = canonical_by_id.get(cid)
        if cluster is None or event is None:
            continue
        members = cluster.members(candidates)
        sources = sorted({_source_label(m) for m in members})
        dates = sorted({m.get("normalized_date") for m in members if m.get("normalized_date")})

        label = (event.clinical_facts or {}).get("concept") or event.type
        lines.append(f"## `{cid}` -- {label}")
        count = len(members)
        who = (
            f"{count} mention{'s' if count != 1 else ''} of what looks like the same real event, "
            f"documented independently in: {', '.join(sources)}."
        )
        when = f" All place it on {dates[0]}." if len(dates) == 1 else (
            f" Dates mentioned: {', '.join(d for d in dates)}." if dates else ""
        )
        lines.append(who + when)

        for conflict in conflicts_by_cluster.get(cid, []):
            lines.append(f"- {_render_conflict(conflict)}")

        hitl_item = hitl_by_cluster.get(cid)
        if hitl_item:
            lines.append(f"- Flagged for human review (priority {hitl_item.priority}/9): {', '.join(hitl_item.reasons)}.")

        lines.append(_outcome_sentence(event, event.canonical_id in selected_ids))
        lines.append("")

    return "\n".join(lines)


CLAIM_LABELS = {
    "supported": "OK",
    "overclaimed": "OVERCLAIMED (states a hedge as settled fact)",
    "contradicted": "WRONG (disagrees with the timeline)",
    "unsupported": "UNSUPPORTED (nothing in the timeline backs this up)",
}


def render_judge_output(case_id: str, tool: str, judged: dict, scorecard: dict) -> str:
    """Plain-English rendering of one summary's evaluation -- the "review
    the evaluation details supporting the score" requirement, for the
    summary-judging side of the pipeline (mirrors render_case_review's job
    on the extraction/conflict side). Turns the same structured claims/
    fact_coverage/usefulness JSON every score is computed from into
    something a non-engineer reviewer can actually read, instead of
    requiring them to parse raw JSON to see WHY a score is what it is."""
    f = scorecard["faithfulness"]
    lines = [f"# Evaluation results -- {case_id}, tool {tool}", ""]
    verdict = "SHIP-ELIGIBLE" if f["ship_eligible"] else "NOT SHIP-ELIGIBLE -- at least one critical problem found below"
    lines.append(f"Faithfulness score: {f['composite']}  ({verdict})")
    lines.append(f"Coverage of material facts: {scorecard['coverage']['weighted_coverage_rate']}")
    lines.append(f"Writing quality (1-5, separate from correctness): {scorecard['usefulness']['mean']}")
    lines.append("")

    if f["gate_triggering_claims"]:
        lines.append("## Why this failed the safety check")
        for c in f["gate_triggering_claims"]:
            lines.append(f'- "{c["text"]}"')
            lines.append(f'  {CLAIM_LABELS.get(c["status"], c["status"])}. {c["reason"]}')
        lines.append("")

    lines.append(f"## Every factual claim checked ({len(judged['claims'])})")
    for c in judged["claims"]:
        label = CLAIM_LABELS.get(c["status"], c["status"])
        lines.append(f'- [{label}] "{c["text"]}"')
        if c["status"] != "supported":
            lines.append(f'    -> {c["reason"]}')
    lines.append("")

    lines.append(f"## Material facts this summary should have covered ({len(judged['fact_coverage'])})")
    for fc in judged["fact_coverage"]:
        tag = {"yes": "COVERED", "partial": "PARTIALLY COVERED", "no": "MISSING"}.get(fc["reflected"], fc["reflected"])
        note = f" -- {fc['notes']}" if fc.get("notes") else ""
        lines.append(f"- [{tag}] {fc['fact_id']}{note}")

    return "\n".join(lines)


if __name__ == "__main__":
    from evalkit.discover import discover_cases

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    for case in discover_cases():
        candidate_path = CANDIDATE_TIMELINES_DIR / f"{case.case_id}.json"
        if not candidate_path.is_file():
            print(f"{case.case_id}: no candidate timeline found, skipping")
            continue
        report = render_case_review(case.case_id)
        out_path = RESULTS_DIR / f"conflict_review_{case.case_id}.md"
        out_path.write_text(report, encoding="utf-8")
        print(f"{case.case_id}: written to {out_path}")
