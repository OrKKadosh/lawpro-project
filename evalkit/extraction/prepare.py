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


MAX_TRUNCATION_SPLIT_DEPTH = 2  # bounds worst-case cost: original chunk + up to 2 halving levels (4 sub-chunks)


def _extract_chunk_with_split_on_truncation(
    case: Case, tracker: BudgetTracker, doc_id: str, start: int, end: int, category: str,
    incomplete_ranges: list[tuple[str, int, int]], depth: int = 0,
) -> list[dict]:
    """Extract one page range; if the response comes back truncated
    (FINDINGS.md: a max_tokens-cut-off response must never be silently
    accepted as a complete extraction), split the range in half and retry
    each half, rather than keeping only the partial salvage. Bounded by
    MAX_TRUNCATION_SPLIT_DEPTH -- if a chunk is STILL truncated once it
    can't usefully be split further (a single page, or the depth cap is
    hit), its partial candidates are kept (recall-oriented: partial data
    beats none) but the range is recorded in `incomplete_ranges` so the
    final extraction result can say plainly that this part of the document
    was not fully extracted, instead of silently looking complete."""
    chunk_text = slice_text(case, doc_id, start, end)
    candidates, incomplete = extract_candidates(tracker, doc_id=doc_id, chunk_text=chunk_text, category=category)
    if not incomplete:
        return candidates
    if end > start and depth < MAX_TRUNCATION_SPLIT_DEPTH:
        mid = (start + end) // 2
        left = _extract_chunk_with_split_on_truncation(case, tracker, doc_id, start, mid, category, incomplete_ranges, depth + 1)
        right = _extract_chunk_with_split_on_truncation(case, tracker, doc_id, mid + 1, end, category, incomplete_ranges, depth + 1)
        return left + right
    incomplete_ranges.append((doc_id, start, end))
    return candidates


def extract_all_candidates(
    case: Case, tracker: BudgetTracker, category: str = "extraction"
) -> tuple[list[dict], list[tuple[str, int, int]]]:
    """Recall-oriented candidate extraction across every document in the case,
    using the frozen chunk config. Returns (candidates, incomplete_ranges) --
    incomplete_ranges lists every (doc_id, start_page, end_page) that was
    STILL truncated after automatic splitting, so a caller can never
    mistake a partial extraction for a complete one. A chunk whose response
    is truncated by max_tokens is automatically split and re-extracted
    rather than silently accepted as complete -- see
    _extract_chunk_with_split_on_truncation()."""
    all_candidates: list[dict] = []
    incomplete_ranges: list[tuple[str, int, int]] = []
    for doc in case.documents:
        for start, end in chunk_ranges(1, doc.pages):
            raw = _extract_chunk_with_split_on_truncation(
                case, tracker, doc.doc_id, start, end, category, incomplete_ranges
            )
            all_candidates.extend(raw)
    return all_candidates, incomplete_ranges


def run_full_extraction(case: Case, tracker: BudgetTracker) -> dict:
    """The whole pipeline: candidates -> normalize -> cluster -> conflict ->
    hitl -> canonicalize -> salience -> project -> schema validation.

    Returns a dict with the final timeline events plus every intermediate
    artifact (candidates, clusters, conflicts, hitl queue, canonical events,
    validation problems) so the whole chain stays inspectable.
    """
    raw_candidates, incomplete_ranges = extract_all_candidates(case, tracker)
    candidates = normalize_candidates(raw_candidates)

    clusters = cluster_candidates(candidates, id_prefix=case.case_id)
    conflicts = detect_conflicts(clusters, candidates)
    hitl_queue = build_hitl_queue(clusters, candidates, conflicts)
    canonical_events = canonicalize_clusters(clusters, candidates, conflicts)
    material_events = select_material_timeline_events(canonical_events)
    timeline_events, problems = project_events(material_events)

    # A page range still truncated after automatic splitting is a real gap in this
    # extraction, not a normal validation nit -- surfaced the same way schema
    # validation problems are, never silently absorbed (FINDINGS.md).
    problems = list(problems) + [
        f"INCOMPLETE EXTRACTION: {doc_id} pages {start}-{end} were still truncated by max_tokens "
        f"after automatic chunk-splitting -- candidates from this range may be a partial, not "
        f"complete, set of the real events in it."
        for doc_id, start, end in incomplete_ranges
    ]

    return {
        "case_id": case.case_id,
        "candidate_count": len(candidates),
        "cluster_count": len(clusters),
        "conflict_count": len(conflicts),
        "hitl_queue_count": len(hitl_queue),
        "canonical_event_count": len(canonical_events),
        "material_event_count": len(material_events),
        "timeline_event_count": len(timeline_events),
        "incomplete_extraction_ranges": [
            {"doc_id": doc_id, "start_page": start, "end_page": end} for doc_id, start, end in incomplete_ranges
        ],
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
