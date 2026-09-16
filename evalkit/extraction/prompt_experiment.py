"""Bounded extraction-prompt iteration experiment (follow-up to PLAN.md S5,
addressing a gap the chunking experiment didn't cover: chunk SIZE was tuned
against a frozen dev set, but the extraction PROMPT itself never was --
only bug-fixed reactively after real-run failures).

Same methodology as chunk_experiment.py: a frozen local dev set, built
before any variant runs, scored deterministically. Chunk size is held
fixed at the already-frozen "large" config (chunk_experiment.py) -- this
experiment varies only the extraction system prompt.

Reuses the three chunk_experiment.py windows/dev-set entries unmodified
(imported, never re-run against a different config) and adds a fourth
window covering the EMS/ED document, which contains two known real
failure modes found by reading actual pipeline output during step 5:

  1. A CPT-code-only billing line ("Operating Room Services / 27535", p1)
     that the *original* prompt's real run interpreted using looked-up
     real-world CPT knowledge ("open treatment of tibial plateau
     fracture" / knee) -- wrong for this patient (arm fractures, no knee
     surgery), not stated anywhere in the source. Caught downstream by
     project.py's grounding check at the time; this experiment tests
     whether a reinforced prompt can avoid fabricating it a stage
     earlier, at the source.
  2. p5's ED physician note, signed/attended by Dr. Foster, explicitly
     names a *different* physician ("Consult Orthopedic Surgery (Dr.
     Myrtle Turner) immediately... for emergency ORIF") as the surgeon
     being consulted. The real run's extraction defaulted
     attribution.provider to the note's signer (Foster) rather than the
     specifically-named actor (Turner) -- flagged as an open limitation
     in FINDINGS.md, not yet fixed. Both trap facts here were read
     directly from the real OCR text before writing this dev set, not
     guessed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from evalkit.budget import BudgetTracker
from evalkit.discover import Case, get_case
from evalkit.extraction.candidates import EXTRACTION_SYSTEM_PROMPT, extract_candidates
from evalkit.extraction.chunk_experiment import (
    CONFIGS,
    DEV_SET as BASE_DEV_SET,
    WINDOWS as BASE_WINDOWS,
    _chunk_ranges,
    _date_close,
    _matches,
    _slice_text,
)

RESULTS_PATH = Path(__file__).resolve().parents[2] / "results" / "prompt_experiment.md"

FROZEN_CONFIG = CONFIGS["large"]  # already frozen by chunk_experiment.py -- not re-tuned here

# --------------------------------------------------------------------------
# Extra window + dev-set entries (verified against real OCR text before
# writing, see module docstring)
# --------------------------------------------------------------------------

EMS_WINDOW = {"doc_id": "01_ems_and_ed", "start_page": 1, "end_page": 5,
              "label": "EMS run sheet + ED physician note -- attending-vs-consulted-physician "
                       "attribution trap (p5), pages 1-4 alcohol/ethanol findings"}

EMS_DEV_SET: list[dict[str, Any]] = [
    {"date": "2023-09-04", "type": "encounter", "materiality": "high",
     "keywords": ["ambulance", "ems", "4 beers", "alcohol"],
     "note": "EMS run narrative: alcohol odor, patient admits 4 beers pre-crash"},
    {"date": "2023-09-04", "type": "diagnosis", "materiality": "high",
     "keywords": ["intoxication", "alcohol"], "note": "Admission diagnosis: alcohol intoxication"},
    {"date": "2023-09-04", "type": "diagnosis", "materiality": "relevant",
     "keywords": ["cage", "alcohol use screen"], "note": "Alcohol use CAGE screen administered"},
    {"date": "2023-09-04", "type": "diagnosis", "materiality": "high",
     "keywords": ["ethanol", "110"], "note": "Toxicology: serum ethanol 110 mg/dL (ref <10)"},
    {"date": "2023-09-04", "type": "diagnosis", "materiality": "high",
     "keywords": ["humerus", "fracture", "compound"], "note": "Left humerus mid-shaft open/compound fracture"},
    {"date": "2023-09-04", "type": "encounter", "materiality": "high",
     "keywords": ["orif", "turner", "consult"],
     "note": "ATTRIBUTION TRAP: ED note is signed/attended by Dr. Foster but explicitly names "
             "Dr. Myrtle Turner as the surgeon being consulted for the ORIF. "
             "attribution.provider for this event should read Turner, not default to Foster."},
]

# --------------------------------------------------------------------------
# Grounding trap check (billing_window) -- verified against real OCR text:
# p1's "0360 Operating Room Services 27535 09/04/2023" line carries no
# clinical description. The real CPT-27535 lookup ("open treatment of
# tibial plateau fracture") is accurate in general and wrong for this
# patient -- nothing in this record documents knee surgery.
# --------------------------------------------------------------------------


def _grounding_trap_violated(candidates: list[dict]) -> bool:
    forbidden = ("tibial", "tibia", "plateau")
    for c in candidates:
        if c.get("source_page") != 1:
            continue
        evidence = str(c.get("evidence_text", "")).lower()
        if "27535" not in evidence and "operating room" not in evidence:
            continue
        facts_text = json.dumps(c.get("clinical_facts") or {}).lower()
        if any(term in facts_text for term in forbidden):
            return True
    return False


def _attribution_trap_correct(candidates: list[dict]) -> bool | None:
    """None if the trap event wasn't matched at all (can't judge); True/False otherwise."""
    trap_event = EMS_DEV_SET[-1]
    for c in candidates:
        if _matches(c, trap_event):
            provider = str((c.get("attribution") or {}).get("provider", "")).lower()
            if "turner" in provider:
                return True
            if "foster" in provider:
                return False
    return None


# --------------------------------------------------------------------------
# Prompt variants
# --------------------------------------------------------------------------

REINFORCED_PROMPT = EXTRACTION_SYSTEM_PROMPT + """

ADDITIONAL RULES (added after real-run failures found by manual inspection -- read carefully):

1. GROUNDING: never populate clinical_facts using outside medical-coding knowledge (e.g. what a \
CPT/HCPCS code conventionally means). If a billing line gives only a code and a generic charge \
description ("Operating Room Services", "Radiology/Diagnostic") with no clinical narrative \
elsewhere in this chunk describing what was actually done, leave clinical_facts.procedure, \
.diagnosis_or_finding, and .body_site null and put the raw code/description verbatim in \
evidence_text instead of interpreting it. A code is evidence a billed service occurred, never \
evidence of what that service specifically was for THIS patient.

2. ATTRIBUTION: a note's signer/attending physician is not always the physician responsible for a \
specific action described in that note. When the note names a DIFFERENT physician as the one being \
consulted, ordering, or performing a specific procedure (e.g. "Consult Dr. X immediately for \
emergency surgery", "per Dr. Y's recommendation"), set attribution.provider to that specifically-\
named acting physician for that action, not to the note's signer. Read the sentence carefully to \
identify who is actually doing or being asked to do the thing, not just whose letterhead the note \
is on."""

PROMPT_VARIANTS: dict[str, str] = {
    "baseline": EXTRACTION_SYSTEM_PROMPT,
    "reinforced": REINFORCED_PROMPT,
}


@dataclass
class VariantResult:
    variant_name: str
    window_key: str
    calls: int = 0
    cost_usd: float = 0.0
    candidates: list[dict] = field(default_factory=list)
    matched: int = 0
    date_correct: int = 0
    grounding_trap_violated: bool | None = None
    attribution_trap_correct: bool | None = None

    def dev_set(self) -> list[dict]:
        return EMS_DEV_SET if self.window_key == "ems_window" else BASE_DEV_SET[self.window_key]

    @property
    def dev_set_size(self) -> int:
        return len(self.dev_set())

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
        dev_events = self.dev_set()
        unsupported = sum(1 for c in self.candidates if not any(_matches(c, e) for e in dev_events))
        return unsupported / len(self.candidates)


def _windows() -> dict[str, dict[str, Any]]:
    windows = dict(BASE_WINDOWS)
    windows["ems_window"] = EMS_WINDOW
    return windows


def run_window_variant(case: Case, tracker: BudgetTracker, window_key: str, variant_name: str) -> VariantResult:
    windows = _windows()
    window = windows[window_key]
    ranges = _chunk_ranges(window["start_page"], window["end_page"], FROZEN_CONFIG["chunk_pages"], FROZEN_CONFIG["overlap"])

    result = VariantResult(variant_name=variant_name, window_key=window_key)
    for start, end in ranges:
        chunk_text = _slice_text(case, window["doc_id"], start, end)
        before = tracker.total_spent
        candidates, _incomplete = extract_candidates(
            tracker, doc_id=window["doc_id"], chunk_text=chunk_text,
            category="prompt_experiment", system_prompt=PROMPT_VARIANTS[variant_name],
        )
        result.cost_usd += tracker.total_spent - before
        result.calls += 1
        result.candidates.extend(candidates)

    dev_events = result.dev_set()
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
        result.grounding_trap_violated = _grounding_trap_violated(result.candidates)
    if window_key == "ems_window":
        result.attribution_trap_correct = _attribution_trap_correct(result.candidates)

    return result


def run_experiment(tracker: BudgetTracker) -> dict[str, list[VariantResult]]:
    case = get_case("case-vance")
    all_results: dict[str, list[VariantResult]] = {}
    for variant_name in PROMPT_VARIANTS:
        for window_key in _windows():
            all_results.setdefault(variant_name, []).append(
                run_window_variant(case, tracker, window_key, variant_name)
            )
    return all_results


def render_report(all_results: dict[str, list[VariantResult]]) -> str:
    lines = ["# Extraction prompt iteration experiment", ""]
    lines.append(
        "Follow-up to `results/chunking_experiment.md`. Chunk size held fixed at the already-"
        "frozen `large` config; this experiment varies only the extraction system prompt "
        "(`evalkit/extraction/prompt_experiment.py`). Same frozen-dev-set methodology, plus two "
        "new trap checks read directly from real OCR text: a CPT-code-grounding trap "
        "(`billing_window`) and an attending-vs-consulted-physician attribution trap "
        "(`ems_window`, new)."
    )
    lines.append("")
    lines.append("| Variant | Window | Calls | Cost | Recall | Date fidelity | Duplicate rate | Unsupported rate | Grounding trap | Attribution trap |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    totals: dict[str, dict[str, float]] = {}
    for variant_name, results in all_results.items():
        t = totals.setdefault(variant_name, {"calls": 0, "cost": 0.0})
        for r in results:
            t["calls"] += r.calls
            t["cost"] += r.cost_usd
            ground = "n/a" if r.grounding_trap_violated is None else ("VIOLATED" if r.grounding_trap_violated else "clean")
            attrib = "n/a" if r.attribution_trap_correct is None else ("correct" if r.attribution_trap_correct else "WRONG (Foster)")
            lines.append(
                f"| {variant_name} | {r.window_key} | {r.calls} | ${r.cost_usd:.4f} | "
                f"{r.recall:.0%} | {r.date_fidelity:.0%} | {r.duplicate_rate:.0%} | "
                f"{r.unsupported_rate:.0%} | {ground} | {attrib} |"
            )
    lines.append("")
    lines.append("| Variant | Total calls | Total cost |")
    lines.append("|---|---|---|")
    for variant_name, t in totals.items():
        lines.append(f"| {variant_name} | {int(t['calls'])} | ${t['cost']:.4f} |")
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
