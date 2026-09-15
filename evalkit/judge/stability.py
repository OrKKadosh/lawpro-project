"""Pairwise run-stability judge (PLAN.md S9/S10).

Aligns claims between two same-tool runs against the same benchmark
timeline. Not "consistency" -- only 2 runs exist per tool/case, so this
never claims statistical stability, only pairwise agreement on this
specific pair.
"""

from __future__ import annotations

from typing import Any

from evalkit.budget import BudgetTracker
from evalkit.judge.schemas import validate_stability_output
from evalkit.llm import call_json

SYSTEM_PROMPT = """You are comparing two summaries written by the SAME tool, from the SAME timeline, on \
two separate runs. Identify every topic where the two summaries make a factual claim (a date, a finding, \
an attribution, a causal statement) and align them into pairs.

For each aligned topic:
- relation:
  - "agree": both runs state the same fact
  - "disagree": the two runs state different or incompatible facts about the same topic -- a real \
inconsistency, not just different wording
  - "run1_only": run 1 makes a claim on this topic that run 2 doesn't mention at all
  - "run2_only": the reverse
- materiality: critical|major|minor, same definitions as faithfulness judging (critical = e.g. a \
causal/attribution claim; major = e.g. a material date/finding; minor = stylistic)
- reason: one sentence

Respond with ONLY this JSON, no other text, no markdown fences:
{"claim_pairs": [
  {"topic": "<short label>", "run1_claim": "<claim or null if run1_only doesn't apply>",
   "run2_claim": "<claim or null>", "relation": "agree|disagree|run1_only|run2_only",
   "materiality": "critical|major|minor", "reason": "<one sentence>"}
]}"""


def judge_stability(
    tracker: BudgetTracker,
    *,
    case_id: str,
    tool: str,
    run1_summary: str,
    run2_summary: str,
    category: str = "stability",
) -> dict[str, Any]:
    prompt = f"""Case: {case_id}, tool: {tool}

Run 1 summary:
\"\"\"
{run1_summary}
\"\"\"

Run 2 summary:
\"\"\"
{run2_summary}
\"\"\"

Align and compare per the instructions above."""
    result = call_json(tracker, category, prompt=prompt, system=SYSTEM_PROMPT, max_tokens=6000)
    validate_stability_output(result)
    return result
