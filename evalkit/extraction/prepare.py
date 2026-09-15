"""Page loading, chunk-boundary logic, and the full-pipeline orchestrator
(PLAN.md S3/S16 step 5).

Chunking is page-aware and never spans documents (PLAN.md S12). The frozen
config from the chunking experiment (DECISIONS.md: large, ~10pp + 1pg
overlap) is the default here.
"""

from __future__ import annotations

import json
from pathlib import Path

from evalkit.budget import BudgetTracker
from evalkit.discover import Case, discover_cases
from evalkit.extraction.candidates import extract_candidates
from evalkit.extraction.canonicalize import canonicalize_clusters
from evalkit.extraction.cluster import cluster_candidates
from evalkit.extraction.conflict import detect_conflicts
from evalkit.extraction.hitl import build_hitl_queue
from evalkit.extraction.normalize import normalize_candidates
from evalkit.extraction.project import project_events
from evalkit.extraction.salience import select_material_timeline_events

# Frozen chunking config (DECISIONS.md: "Chunking config frozen at large").
CHUNK_PAGES = 10
CHUNK_OVERLAP = 1


def chunk_ranges(start: int, end: int, chunk_pages: int = CHUNK_PAGES, overlap: int = CHUNK_OVERLAP) -> list[tuple[int, int]]:
    """1-indexed inclusive page ranges, page-aware, with the given overlap."""
    stride = max(chunk_pages - overlap, 1)
    ranges = []
    p = start
    while p <= end:
        chunk_end = min(p + chunk_pages - 1, end)
        ranges.append((p, chunk_end))
        if chunk_end >= end:
            break
        p += stride
    return ranges


def slice_text(case: Case, doc_id: str, start_page: int, end_page: int) -> str:
    pages = case.ocr_pages(doc_id)
    selected = pages[start_page - 1 : end_page]
    return "\n\n".join(f"[p{start_page + i}]\n{page}" for i, page in enumerate(selected))


def extract_all_candidates(case: Case, tracker: BudgetTracker, category: str = "extraction") -> list[dict]:
    """Recall-oriented candidate extraction across every document in the case,
    using the frozen chunk config."""
    all_candidates: list[dict] = []
    for doc in case.documents:
        for start, end in chunk_ranges(1, doc.pages):
            chunk_text = slice_text(case, doc.doc_id, start, end)
            raw = extract_candidates(tracker, doc_id=doc.doc_id, chunk_text=chunk_text, category=category)
            all_candidates.extend(raw)
    return all_candidates


def run_full_extraction(case: Case, tracker: BudgetTracker) -> dict:
    """The whole pipeline: candidates -> normalize -> cluster -> conflict ->
    hitl -> canonicalize -> salience -> project -> schema validation.

    Returns a dict with the final timeline events plus every intermediate
    artifact (candidates, clusters, conflicts, hitl queue, canonical events,
    validation problems) so the whole chain stays inspectable.
    """
    raw_candidates = extract_all_candidates(case, tracker)
    candidates = normalize_candidates(raw_candidates)

    clusters = cluster_candidates(candidates, id_prefix=case.case_id)
    conflicts = detect_conflicts(clusters, candidates)
    hitl_queue = build_hitl_queue(clusters, candidates, conflicts)
    canonical_events = canonicalize_clusters(clusters, candidates, conflicts)
    material_events = select_material_timeline_events(canonical_events)
    timeline_events, problems = project_events(material_events)

    return {
        "case_id": case.case_id,
        "candidate_count": len(candidates),
        "cluster_count": len(clusters),
        "conflict_count": len(conflicts),
        "hitl_queue_count": len(hitl_queue),
        "canonical_event_count": len(canonical_events),
        "material_event_count": len(material_events),
        "timeline_event_count": len(timeline_events),
        "validation_problems": problems,
        "timeline": {"case_id": case.case_id, "events": timeline_events},
        "candidates": candidates,
        "conflicts": [vars(c) for c in conflicts],
        "hitl_queue": [
            {
                "cluster_id": it.cluster_id, "materiality": it.materiality,
                "uncertainty": it.uncertainty, "priority": it.priority,
                "reasons": it.reasons, "evidence": it.evidence,
            }
            for it in hitl_queue
        ],
    }


CANDIDATE_TIMELINES_DIR = Path(__file__).resolve().parents[2] / "runs" / "candidate_timelines"


if __name__ == "__main__":
    tracker = BudgetTracker()
    CANDIDATE_TIMELINES_DIR.mkdir(parents=True, exist_ok=True)
    for case in discover_cases():
        print(f"=== extracting {case.case_id} ({sum(d.pages for d in case.documents)} pages, "
              f"{len(case.documents)} docs) ===")
        result = run_full_extraction(case, tracker)
        out_path = CANDIDATE_TIMELINES_DIR / f"{case.case_id}.json"
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(
            f"  candidates={result['candidate_count']} clusters={result['cluster_count']} "
            f"conflicts={result['conflict_count']} hitl_queue={result['hitl_queue_count']} "
            f"canonical={result['canonical_event_count']} material={result['material_event_count']} "
            f"final_timeline={result['timeline_event_count']} "
            f"validation_problems={len(result['validation_problems'])}"
        )
        print(f"  written to {out_path}")
    print()
    print(tracker.summary())
