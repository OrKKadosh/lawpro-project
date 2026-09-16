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
from evalkit.judge.schemas import SchemaError, validate_faithfulness_coverage_output
from evalkit.llm import call_json


class JudgeOutputInvalid(RuntimeError):
    """Raised when the judge's output still fails structural validation
    (most commonly: a claim with no summary_quote, or one that isn't an
    actual substring of the summary) after one repair retry. The caller
    MUST treat this run as invalid/not scored -- FINDINGS.md documents why
    this matters: the previous design silently excluded individual
    unvalidated claims via a text heuristic and scored a composite from
    whatever remained, which both dropped real claims from the denominator
    and, worse, demonstrably let a genuine major-materiality unsupported
    claim slip through uncounted in real committed data. An invalid judge
    RUN is now an explicit, visible failure -- never silently patched
    around at the claim level."""

SYSTEM_PROMPT = """You are fact-checking one attorney-facing clinical summary against the exact \
timeline it was generated from. The summary was written by a tool that saw ONLY this timeline -- it \
never had access to the original medical records, so it can only be right or wrong relative to what \
the timeline actually says.

STEP 1 -- ATOMIC CLAIMS. Decompose the summary into atomic factual claims -- ONLY things the summary \
text actually asserts. A single sentence often contains several (a date, a finding, an attribution, a \
causal statement -- each is its own claim). For each claim, determine:

CRITICAL RULE, do not violate it: a claim is something the summary SAYS, never something it DOESN'T \
say. If a material fact from the timeline is missing, vague, or under-explained in the summary, that is \
an OMISSION -- it belongs ONLY in Step 2 (material fact coverage) below, never as an entry in claims[]. \
Do NOT create a claim like "no mention of X" or "summary omits Y" -- there is no claim to fact-check \
when the summary says nothing. Putting an omission in claims[] would penalize FAITHFULNESS (does the \
summary only assert what's true) for something that is actually a COVERAGE problem (did the summary \
include everything material) -- these are deliberately separate dimensions and must never be conflated.

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
- summary_quote: the EXACT text from the summary (copy-pasted, not paraphrased) that makes this claim. \
Every claim must be traceable to real summary text this way -- if you cannot quote the summary text that \
asserts it, it is not a claim the summary actually makes, and you should not be creating it.

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
              "reason": "<one sentence>", "summary_quote": "<exact text from the summary>"}],
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
    try:
        validate_faithfulness_coverage_output(result, summary_text)
        return result
    except SchemaError as exc:
        repair_prompt = f"""{prompt}

---
Your previous response was INVALID: {exc}

Every entry in claims[] MUST include a non-empty "summary_quote" field that is the EXACT, \
verbatim text from the summary above (copy-pasted, not paraphrased, not summarized) -- it must \
appear in the summary text word-for-word. If you cannot find exact summary text supporting a \
claim, do not include that claim at all.

Respond again with ONLY the corrected, complete JSON, no other text, no markdown fences."""
        tracker.check_floor()
        result2 = call_json(tracker, category, prompt=repair_prompt, system=SYSTEM_PROMPT, max_tokens=8000)
        try:
            validate_faithfulness_coverage_output(result2, summary_text)
            return result2
        except SchemaError as exc2:
            raise JudgeOutputInvalid(
                f"case={case_id!r} tool={tool!r} run={run}: judge output still invalid after one repair "
                f"retry: {exc2}"
            ) from exc2
