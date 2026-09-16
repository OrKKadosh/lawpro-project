"""Bounded chunking experiment (PLAN.md S5).

Three representative Vance page windows, three chunk configurations, one
frozen local dev set per window (built before any configuration runs, not
derived from golden or a case-wide material-fact set). Metrics: material-
event recall, date fidelity, duplicate-candidate rate, unsupported-event
rate (approximate), trap awareness, cost. Not a hyperparameter search --
run once, compared, one config frozen.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from evalkit.budget import BudgetTracker
from evalkit.discover import Case, get_case
from evalkit.extraction.candidates import extract_candidates

RESULTS_PATH = Path(__file__).resolve().parents[2] / "results" / "chunking_experiment.md"

# --------------------------------------------------------------------------
# Windows (bounded, not whole documents -- PLAN.md S5)
# --------------------------------------------------------------------------

WINDOWS: dict[str, dict[str, Any]] = {
    "billing_window": {"doc_id": "08_billing_and_claims", "start_page": 1, "end_page": 12,
                        "label": "dense hospital/billing record (18pp doc, 12pp window)"},
    "prior_records": {"doc_id": "03_prior_records", "start_page": 1, "end_page": 5,
                       "label": "date/pre-existing-condition-ambiguity document (5pp, whole doc)"},
    "therapy_window": {"doc_id": "05_pt_lang_weimann", "start_page": 1, "end_page": 12,
                        "label": "repetitive-therapy document (33pp doc, 12pp window)"},
}

# --------------------------------------------------------------------------
# Frozen local dev set -- built once, before any configuration is run.
# Not golden, not the case-wide material-fact set (PLAN.md S9/SF) built later.
# --------------------------------------------------------------------------

DEV_SET: dict[str, list[dict[str, Any]]] = {
    "billing_window": [
        {"date": "2023-09-04", "type": "encounter", "materiality": "high",
         "keywords": ["admission", "admit"], "note": "Hospital admission, Littel Inc Emergency Hospital"},
        {"date": "2023-09-04", "type": "encounter", "materiality": "high",
         "keywords": ["ambulance", "ems", "vance"], "note": "EMS ambulance transport, Paramedic James Vance"},
        {"date": "2023-09-07", "type": "procedure", "materiality": "high",
         "keywords": ["24515", "25607", "orif", "turner"],
         "note": "TRAP: ORIF humerus+radius by Dr. Turner -- UB-04 (p1) lists 09-04 as the "
                 "'principal procedure date', but Turner's own professional claim (p5) dates the "
                 "CPT codes 09-07, matching the true operative-report date. Correct = 09-07."},
        {"date": "2022-09-12", "type": "encounter", "materiality": "high",
         "keywords": ["finch", "99203"], "note": "Dr. Finch office visit"},
        {"date": "2022-09-15", "type": "imaging", "materiality": "high",
         "keywords": ["finch", "72040", "cervical"], "note": "Cervical X-ray billed by Dr. Finch"},
        {"date": "2023-12-18", "type": "imaging", "materiality": "high",
         "keywords": ["harrison", "72141", "mri"], "note": "Cervical MRI by Dr. Harrison"},
        {"date": "2023-09-15", "type": "encounter", "materiality": "high",
         "keywords": ["stewart", "97161", "initial"], "note": "Initial PT evaluation by Robert Stewart"},
        {"date": "2024-01-08", "type": "encounter", "materiality": "high",
         "keywords": ["gregory", "97162", "re-eval", "reeval"],
         "note": "PT re-evaluation / transition of care to Amanda Gregory"},
    ],
    "prior_records": [
        {"date": "2022-09-10", "type": "encounter", "materiality": "high",
         "keywords": ["intake", "last week"], "note": "New patient intake, patient reports neck pain since gym injury 'last week'"},
        {"date": "2022-09-12", "type": "diagnosis", "materiality": "high",
         "keywords": ["cervical strain", "finch", "herniation"],
         "note": "Dr. Finch: acute cervical strain / possible disc herniation"},
        {"date": "2022-09-15", "type": "imaging", "materiality": "high",
         "keywords": ["4mm", "disc bulge", "c5-c6", "c5", "c6"],
         "note": "Cervical X-ray: 4mm C5-C6 posterior disc bulge"},
    ],
    "therapy_window": [
        {"date": "2023-09-15", "type": "encounter", "materiality": "high",
         "keywords": ["initial", "evaluation"], "note": "Initial PT evaluation"},
        {"date": "2023-09-18", "type": "therapy", "materiality": "routine", "keywords": ["visit 1"], "note": "Visit 1"},
        {"date": "2023-09-20", "type": "therapy", "materiality": "routine", "keywords": ["visit 2"], "note": "Visit 2"},
        {"date": "2023-09-22", "type": "therapy", "materiality": "routine", "keywords": ["visit 3"], "note": "Visit 3"},
        {"date": "2023-09-25", "type": "therapy", "materiality": "routine", "keywords": ["visit 4"], "note": "Visit 4"},
        {"date": "2023-09-27", "type": "therapy", "materiality": "routine", "keywords": ["visit 5"], "note": "Visit 5"},
        {"date": "2023-09-29", "type": "therapy", "materiality": "routine", "keywords": ["visit 6"], "note": "Visit 6"},
        {"date": "2023-10-02", "type": "therapy", "materiality": "routine", "keywords": ["visit 7"], "note": "Visit 7"},
        {"date": "2023-10-04", "type": "therapy", "materiality": "routine", "keywords": ["visit 8"], "note": "Visit 8"},
        {"date": "2023-10-06", "type": "therapy", "materiality": "routine", "keywords": ["visit 9"], "note": "Visit 9"},
        {"date": "2023-10-09", "type": "therapy", "materiality": "routine", "keywords": ["visit 10"], "note": "Visit 10"},
        {"date": "2023-10-11", "type": "therapy", "materiality": "routine", "keywords": ["visit 11"], "note": "Visit 11"},
    ],
}

NON_EVENTS: dict[str, list[str]] = {
    # Things present in the window that should NOT become their own clinical event.
    "billing_window": ["10/02/2023 Sentinel EOB payment posting (p12) -- administrative, not clinical"],
    "prior_records": ["p1 records-certification cover letter -- not a clinical event"],
    "therapy_window": [],
}

CONFIGS: dict[str, dict[str, int]] = {
    "small": {"chunk_pages": 3, "overlap": 1},
    "medium": {"chunk_pages": 5, "overlap": 1},
    "large": {"chunk_pages": 10, "overlap": 1},
}


def _chunk_ranges(start: int, end: int, chunk_pages: int, overlap: int) -> list[tuple[int, int]]:
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


def _slice_text(case: Case, doc_id: str, start_page: int, end_page: int) -> str:
    pages = case.ocr_pages(doc_id)
    selected = pages[start_page - 1 : end_page]
    return "\n\n".join(f"[p{start_page + i}]\n{page}" for i, page in enumerate(selected))


def _matches(candidate: dict, dev_event: dict) -> bool:
    text = " ".join(
        str(candidate.get(k, "")).lower()
        for k in ("evidence_text", "raw_summary", "clinical_facts")
    )
    return any(kw.lower() in text for kw in dev_event["keywords"])


def _date_close(a: str | None, b: str, tolerance_days: int = 3) -> bool:
    if not a:
        return False
    try:
        from datetime import date

        da = date.fromisoformat(a)
        db = date.fromisoformat(b)
        return abs((da - db).days) <= tolerance_days
    except ValueError:
        return False


@dataclass
class WindowResult:
    window_key: str
    config_name: str
    calls: int = 0
    cost_usd: float = 0.0
    candidates: list[dict] = field(default_factory=list)
    matched: int = 0
    date_correct: int = 0
    trap_aware: bool = False

    @property
    def dev_set_size(self) -> int:
        return len(DEV_SET[self.window_key])

    @property
    def recall(self) -> float:
        return self.matched / self.dev_set_size if self.dev_set_size else 0.0

    @property
    def date_fidelity(self) -> float:
        return self.date_correct / self.matched if self.matched else 0.0

    @property
    def duplicate_rate(self) -> float:
        pairs = [(c.get("normalized_date"), c.get("event_type_candidate")) for c in self.candidates]
        if not pairs:
            return 0.0
        unique = len(set(pairs))
        return (len(pairs) - unique) / len(pairs)

    @property
    def unsupported_rate(self) -> float:
        if not self.candidates:
            return 0.0
        dev_events = DEV_SET[self.window_key]
        unsupported = sum(
            1 for c in self.candidates if not any(_matches(c, e) for e in dev_events)
        )
        return unsupported / len(self.candidates)


def run_window_config(
    case: Case, tracker: BudgetTracker, window_key: str, config_name: str
) -> WindowResult:
    window = WINDOWS[window_key]
    config = CONFIGS[config_name]
    ranges = _chunk_ranges(window["start_page"], window["end_page"], config["chunk_pages"], config["overlap"])

    result = WindowResult(window_key=window_key, config_name=config_name)
    for start, end in ranges:
        chunk_text = _slice_text(case, window["doc_id"], start, end)
        before = tracker.total_spent
        candidates, _incomplete = extract_candidates(
            tracker, doc_id=window["doc_id"], chunk_text=chunk_text, category="chunk_experiment"
        )
        result.cost_usd += tracker.total_spent - before
        result.calls += 1
        result.candidates.extend(candidates)

    dev_events = DEV_SET[window_key]
    for event in dev_events:
        best = None
        for c in result.candidates:
            if _matches(c, event):
                if c.get("normalized_date") == event["date"]:
                    best = c
                    break
                if best is None and _date_close(c.get("normalized_date"), event["date"]):
                    best = c
        if best is not None:
            result.matched += 1
            if best.get("normalized_date") == event["date"]:
                result.date_correct += 1

    if window_key == "billing_window":
        for c in result.candidates:
            if _matches(c, dev_events[2]):  # the ORIF trap event
                evidence = str(c.get("evidence_text", "")).lower() + str(c.get("date_basis", "")).lower()
                if "billing_service_date" in evidence or "discrepan" in evidence or "09/04" in evidence or "09-04" in evidence:
                    result.trap_aware = True

    return result


def run_experiment(tracker: BudgetTracker) -> dict[str, list[WindowResult]]:
    case = get_case("case-vance")
    all_results: dict[str, list[WindowResult]] = {}
    for config_name in CONFIGS:
        for window_key in WINDOWS:
            all_results.setdefault(config_name, []).append(
                run_window_config(case, tracker, window_key, config_name)
            )
    return all_results


def render_report(all_results: dict[str, list[WindowResult]]) -> str:
    lines = ["# Chunking experiment (PLAN.md S5)", ""]
    lines.append(
        "Frozen local dev set built before any configuration ran (see `DEV_SET` in "
        "`evalkit/extraction/chunk_experiment.py`), scored with deterministic keyword+date "
        "matching -- not a semantic judge call, kept cheap and transparent. `unsupported_rate` is "
        "approximate (candidates not matching any dev-set keyword; for `billing_window` the dev "
        "set is not exhaustive of every line item, so this overstates true unsupported claims "
        "there -- `therapy_window`'s dev set IS exhaustive of its 12 real events, so its "
        "unsupported_rate is a cleaner signal)."
    )
    lines.append("")
    lines.append("| Config | Window | Calls | Cost | Recall | Date fidelity | Duplicate rate | Unsupported rate | Trap aware |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    totals: dict[str, dict[str, float]] = {}
    for config_name, results in all_results.items():
        t = totals.setdefault(config_name, {"calls": 0, "cost": 0.0})
        for r in results:
            t["calls"] += r.calls
            t["cost"] += r.cost_usd
            trap = "yes" if r.trap_aware else ("n/a" if r.window_key != "billing_window" else "no")
            lines.append(
                f"| {config_name} | {r.window_key} | {r.calls} | ${r.cost_usd:.4f} | "
                f"{r.recall:.0%} | {r.date_fidelity:.0%} | {r.duplicate_rate:.0%} | "
                f"{r.unsupported_rate:.0%} | {trap} |"
            )
    lines.append("")
    lines.append("| Config | Total calls | Total cost |")
    lines.append("|---|---|---|")
    for config_name, t in totals.items():
        lines.append(f"| {config_name} | {int(t['calls'])} | ${t['cost']:.4f} |")
    return "\n".join(lines)


if __name__ == "__main__":
    tracker = BudgetTracker()
    results = run_experiment(tracker)
    report = render_report(results)
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(report, encoding="utf-8")
    print(report)
    print()
    print(tracker.summary())
