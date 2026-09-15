"""Combined faithfulness + coverage + usefulness judge (PLAN.md S9/S10).

One call per summary. Structured JSON out: atomic claims with a status and
materiality tier each, fact-by-fact coverage against the frozen
material_fact_set, and usefulness scored on separate style dimensions. The
judge never emits a final score -- scoring.py computes every composite from
these annotations deterministically (PLAN.md S10: the judge proposes
evidence, code decides the number).
"""

from __future__ import annotations

from typing import Any

from evalkit.budget import BudgetTracker
from evalkit.judge.schemas import validate_faithfulness_coverage_output
from evalkit.llm import call_json

SYSTEM_PROMPT = """You are fact-checking one attorney-facing clinical summary against the exact \
timeline it was generated from. The summary was written by a tool that saw ONLY this timeline -- it \
never had access to the original medical records, so it can only be right or wrong relative to what \
the timeline actually says.

STEP 1 -- ATOMIC CLAIMS. Decompose the summary into atomic factual claims. A single sentence often \
contains several (a date, a finding, an attribution, a causal statement -- each is its own claim). \
For each claim, determine:

- status:
  - "supported": the timeline states this, and the summary states it accurately
  - "unsupported": nothing in the timeline supports this claim (it may be plausible, that doesn't matter)
  - "contradicted": the timeline states something different or incompatible
  - "overclaimed": the timeline hedges this (e.g. "possibly", "inconclusive", "unclear onset") but the \
summary states it as settled fact -- this is its own category, distinct from "unsupported", because the \
underlying fact is real but the CONFIDENCE was fabricated
- materiality:
  - "critical": fabricated procedure/diagnosis/mechanism; overclaims a hedged finding into certainty; \
wrong body level/laterality; false causal attribution; misattributes one physician's opinion or finding \
to a different physician
  - "major": wrong/unsupported date, provider, or finding on a clinically material event; wrong sequencing
  - "minor": unsupported narrative flourish, nothing independently checkable
- evidence_event_ids: the timeline event index/indices (from the numbered list below) this claim relates to
- reason: one sentence explaining the verdict, citing the specific timeline content

STEP 2 -- MATERIAL FACT COVERAGE. You are given a fixed list of material facts derived from this same \
timeline. For each one, does the summary reflect it -- "yes" (clearly stated), "partial" (touched on but \
incomplete or vague), or "no" (absent)? Judge only whether the fact is REFLECTED, not whether it's stated \
in the same words.

STEP 3 -- USEFULNESS. Rate 1-5 (5 = best) on each dimension, independent of factual accuracy: \
chronological_clarity, concision, organization, preserves_uncertainty (does it keep hedged findings \
hedged, rather than flattening them), separates_pre_existing_vs_post (does it clearly distinguish \
pre-incident history from post-incident treatment), emphasis_on_material_facts (does it lead with what \
matters, not bury it), avoids_repetitive_clutter (does it compress routine repeated visits sensibly).

Respond with ONLY this JSON, no other text, no markdown fences:
{
  "claims": [{"claim_id": "<c1>", "text": "<the claim, in your own words>",
              "status": "supported|unsupported|contradicted|overclaimed",
              "materiality": "critical|major|minor", "evidence_event_ids": [<int>, ...],
              "reason": "<one sentence>"}],
  "fact_coverage": [{"fact_id": "<from the material fact list>", "reflected": "yes|no|partial",
                      "notes": "<one sentence>"}],
  "usefulness": {"chronological_clarity": <1-5>, "concision": <1-5>, "organization": <1-5>,
                  "preserves_uncertainty": <1-5>, "separates_pre_existing_vs_post": <1-5>,
                  "emphasis_on_material_facts": <1-5>, "avoids_repetitive_clutter": <1-5>}
}"""


def _format_events(events: list[dict]) -> str:
    return "\n".join(f"[{i}] {e.get('date') or 'undated'} | {e.get('type')} | {e.get('detail')}" for i, e in enumerate(events))


def _format_facts(material_facts: list[dict]) -> str:
    return "\n".join(
        f"- {f['fact_id']} (weight {f['materiality_weight']}): {f['description']}" for f in material_facts
    )


def judge_summary(
    tracker: BudgetTracker,
    *,
    case_id: str,
    tool: str,
    run: int,
    summary_text: str,
    timeline_events: list[dict],
    material_facts: list[dict],
    category: str = "faithfulness_coverage",
) -> dict[str, Any]:
    prompt = f"""Case: {case_id}, tool: {tool}, run: {run}

Timeline the summarizer was given ({len(timeline_events)} events):
{_format_events(timeline_events)}

Material facts to check coverage against:
{_format_facts(material_facts)}

Summary to fact-check:
\"\"\"
{summary_text}
\"\"\"

Fact-check this summary per the instructions above."""
    result = call_json(tracker, category, prompt=prompt, system=SYSTEM_PROMPT, max_tokens=8000)
    validate_faithfulness_coverage_output(result)
    return result
