"""Material-fact-set construction (PLAN.md S9/S10).

Runs once per case, on the BENCHMARK timeline only -- golden for Vance,
input_timeline.json for Davis (PLAN.md S8: the confirmed exact input behind
each case's 8 supplied summaries) -- never on our own richer candidate
extraction. This distinction is load-bearing, not incidental: a summarizer
never sees anything beyond the benchmark timeline it was handed, so a fact
our extraction finds but the benchmark timeline doesn't contain (e.g.
Vance's alcohol finding, absent from golden) must never enter the fact set
used to grade that summarizer -- that's the coverage-boundary rule
(PLAN.md S7) enforced structurally here, not just by policy.

Frozen after a human spot-check (me, this build) before any summary is
judged -- see freeze_material_facts()/save_frozen(). Once frozen, the same
fact set is reused for every tool scored against that benchmark timeline.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from chronos import timeline as chronos_timeline
from evalkit.budget import BudgetTracker
from evalkit.discover import Case
from evalkit.llm import call_json

MATERIAL_FACT_SYSTEM_PROMPT = """You are building the fixed set of material facts a clinical timeline \
implies -- the facts a good attorney-facing summary of THIS TIMELINE should reflect. You will see only \
the timeline, exactly as a summarization tool would; do not assume any fact beyond what's in it.

Only include facts in these categories: incident/mechanism, major injury, major diagnosis, major \
imaging finding, surgery/procedure, relevant pre-existing condition, causation opinion, treatment \
course (as one compressed fact per course, e.g. "physical therapy course from X to Y addressing Z" -- \
never one fact per individual session), material complication, treatment gap/compliance issue, \
functional limitation, prognosis/MMI.

Do NOT create a separate fact for every individual routine visit in a repetitive series (e.g. dozens \
of physical therapy sessions) -- represent that as one treatment-course fact citing the relevant event \
indices. Do NOT invent a fact not actually supported by specific events in the timeline below.

For each fact, give: a short id, its category (from the list above), a one-sentence description, a \
materiality_weight (1=minor but still worth noting, 2=materially relevant, 3=critical -- e.g. the \
injury mechanism, a surgery, a causation opinion, a permanent functional limitation), and \
supporting_event_ids: the exact integer indices (from the numbered list below) of the timeline events \
that support this fact.

Respond with ONLY this JSON structure, no other text, no markdown fences:
{"material_facts": [
  {"fact_id": "<short id>", "category": "<one of the categories above>",
   "description": "<one sentence>", "materiality_weight": 1|2|3,
   "supporting_event_ids": [<int>, ...]}
]}"""


def _format_events(events: list[dict]) -> str:
    lines = []
    for i, e in enumerate(events):
        lines.append(f"[{i}] {e.get('date') or 'undated'} | {e.get('type')} | {e.get('detail')}")
    return "\n".join(lines)


def build_material_fact_set(
    case: Case, tracker: BudgetTracker, *, events: Optional[list[dict]] = None, source_label: Optional[str] = None,
) -> dict[str, Any]:
    """Runs the construction judge against a timeline for `case`. By
    default (events=None) uses the case's BENCHMARK timeline (golden /
    input_timeline -- see module docstring) -- this is what the controlled-
    benchmark methodology requires, and case-vance/case-davis's existing
    frozen fact sets were built this way; unchanged for them.

    For a case with no benchmark reference at all -- a genuinely new case
    run through the application for the first time, which only has OCR
    input and our own extraction, no externally-supplied golden/
    input_timeline (CLAUDE.md's dynamic-case-discovery requirement extends
    to this: `evaluate` needs SOMETHING to check coverage against for any
    case, not just the two with a known reference) -- pass `events`
    explicitly (our own extracted candidate timeline) and a `source_label`
    describing where it came from. The coverage-boundary principle still
    holds in spirit: the fact set is scoped to whatever timeline is passed
    in, never to a fact the summarizer wasn't actually given.
    """
    if events is None:
        ref_path = case.reference_timeline_path()
        events = chronos_timeline.parse(ref_path.read_text(encoding="utf-8"))
        source_label = str(ref_path)
    prompt = f"""Benchmark timeline for case `{case.case_id}` ({len(events)} events):

{_format_events(events)}

---

Build the material fact set per the instructions above."""
    result = call_json(
        tracker, "material_facts", prompt=prompt, system=MATERIAL_FACT_SYSTEM_PROMPT, max_tokens=4096
    )
    return {
        "case_id": case.case_id,
        "benchmark_timeline_path": source_label,
        "benchmark_event_count": len(events),
        "material_facts": result.get("material_facts", []),
    }


FROZEN_DIR = Path(__file__).resolve().parents[2] / "results" / "material_facts"


def save_frozen(case_id: str, fact_set: dict[str, Any]) -> Path:
    """Write the human-spot-checked fact set as the frozen artifact every
    downstream judge call reuses. Once written, this file is the fact set --
    it does not get regenerated or edited after any summary has been read."""
    FROZEN_DIR.mkdir(parents=True, exist_ok=True)
    path = FROZEN_DIR / f"{case_id}.json"
    path.write_text(json.dumps(fact_set, indent=2), encoding="utf-8")
    return path


def load_frozen(case_id: str) -> dict[str, Any]:
    path = FROZEN_DIR / f"{case_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


CANDIDATE_TIMELINES_DIR = Path(__file__).resolve().parents[2] / "runs" / "candidate_timelines"


def get_or_build_material_facts(case: Case, tracker: BudgetTracker) -> dict[str, Any]:
    """The material fact set to grade a summary's coverage against, for ANY
    case -- not just the two with a frozen, human-spot-checked file.

    1. Reuse the frozen file if one exists (case-vance/case-davis: built
       from their confirmed benchmark timeline, human-spot-checked before
       freezing -- PLAN.md S9/S10. Never rebuilt once frozen; unaffected.)
    2. Otherwise, build one now: from the case's benchmark reference if it
       has one (golden/input_timeline), else from our own extracted
       candidate timeline -- the only thing available for a genuinely new
       case with no externally-supplied reference (CLAUDE.md's dynamic-
       case-discovery requirement, extended to this step: a case dropped
       into data/ with only OCR input must still be evaluable end to end).
       Freezes the result so a later run reuses it instead of re-spending.
    """
    try:
        return load_frozen(case.case_id)
    except FileNotFoundError:
        pass

    try:
        fact_set = build_material_fact_set(case, tracker)
    except FileNotFoundError:
        candidate_path = CANDIDATE_TIMELINES_DIR / f"{case.case_id}.json"
        if not candidate_path.is_file():
            raise FileNotFoundError(
                f"No benchmark reference (golden/input_timeline) and no extracted timeline found "
                f"for {case.case_id} -- run `extract {case.case_id}` first."
            )
        events = json.loads(candidate_path.read_text(encoding="utf-8"))["timeline"]["events"]
        fact_set = build_material_fact_set(
            case, tracker, events=events, source_label=f"our own extraction: {candidate_path}"
        )

    save_frozen(case.case_id, fact_set)
    return fact_set
