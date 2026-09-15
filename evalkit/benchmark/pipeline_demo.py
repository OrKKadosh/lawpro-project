"""End-to-end pipeline demo (PLAN.md S11 experiment matrix, S16 step 10).

Our own final extracted timeline -> a real /v1/summarize call through the
tool the controlled benchmark (results/final_scorecard.md) identified as
strongest for that case -> judged the same way the controlled benchmark's
summaries were judged. This demonstrates the whole pipeline working
end-to-end, but it is explicitly NOT part of the shipping evidence: our own
extraction quality is now in the loop, which the controlled benchmark
deliberately keeps out (PLAN.md S2's separation). Results are written to a
visibly separate path (results/pipeline_demo_<case>.json) so a reviewer can
never mistake this for a controlled-benchmark number.
"""

from __future__ import annotations

import json
from pathlib import Path

from chronos import client
from chronos import timeline as chronos_timeline
from evalkit.budget import BudgetTracker
from evalkit.discover import Case, discover_cases
from evalkit.judge.faithfulness_coverage import judge_summary
from evalkit.judge.material_facts import get_or_build_material_facts
from evalkit.scoring import build_summary_scorecard

RESULTS_DIR = Path(__file__).resolve().parents[2] / "results"
CANDIDATE_TIMELINES_DIR = Path(__file__).resolve().parents[2] / "runs" / "candidate_timelines"


def choose_tool_for_case(case_id: str) -> str | None:
    """The tool to demo for a case: read dynamically off that case's own
    already-computed controlled-benchmark result (results/controlled_
    benchmark_<case>.json), never hardcoded per case -- CLAUDE.md's
    non-negotiable "no hardcoding to specific cases" rule applies here too,
    not just to document/case discovery (an earlier version of this file
    hardcoded {"case-vance": "D", "case-davis": "A"}, a real violation
    caught in the adversarial review pass, PROGRESS.md).

    Among ship-eligible tools, picks the highest mean_faithfulness (ties
    broken by mean_coverage). Returns None if the case has no controlled-
    benchmark result yet, or no tool passed the gate at all -- callers
    must handle that rather than silently picking an unsafe tool."""
    path = RESULTS_DIR / f"controlled_benchmark_{case_id}.json"
    if not path.is_file():
        return None
    tools = json.loads(path.read_text(encoding="utf-8")).get("tools", {})
    eligible = [(t, tc) for t, tc in tools.items() if tc.get("ship_eligible")]
    if not eligible:
        return None
    eligible.sort(key=lambda tc: (tc[1].get("mean_faithfulness", 0), tc[1].get("mean_coverage", 0)), reverse=True)
    return eligible[0][0]


def run_pipeline_demo_for_case(case: Case, tracker: BudgetTracker, tool: str | None = None) -> dict:
    candidate_path = CANDIDATE_TIMELINES_DIR / f"{case.case_id}.json"
    timeline_events = json.loads(candidate_path.read_text(encoding="utf-8"))["timeline"]["events"]

    # Non-negotiable per CLAUDE.md: validate before ever calling /v1/summarize.
    chronos_timeline.parse({"events": timeline_events})

    tool = tool or choose_tool_for_case(case.case_id)
    if tool is None:
        raise ValueError(
            f"no ship-eligible tool found for {case.case_id} in results/controlled_benchmark_{case.case_id}.json "
            "-- run the controlled benchmark (evalkit/report.py) first, or pass tool= explicitly"
        )
    response = client.summarize(tool, case_id=case.case_id, timeline=timeline_events)
    tracker.record("pipeline_demo_summarize", response)
    summary_text = response["summary"]
    cost_usd = response.get("cost_usd", 0.0)

    fact_set = get_or_build_material_facts(case, tracker)
    material_facts = fact_set["material_facts"]
    judged = judge_summary(
        tracker, case_id=case.case_id, tool=tool, run=1,
        summary_text=summary_text, timeline_events=timeline_events, material_facts=material_facts,
        category="pipeline_demo_judge",
    )
    scorecard = build_summary_scorecard(
        tool=tool, run=1, cost_usd=cost_usd, claims=judged["claims"],
        fact_coverage=judged["fact_coverage"], usefulness=judged["usefulness"], material_facts=material_facts,
    )

    return {
        "case_id": case.case_id,
        "note": "END-TO-END PIPELINE DEMO -- uncontrolled (our own extraction quality is in the loop). "
                "Never cited for the shipping recommendation; see results/final_scorecard.md for that.",
        "chosen_tool": tool,
        "chosen_tool_rationale": f"highest mean_faithfulness among ship-eligible tools in "
                                  f"results/controlled_benchmark_{case.case_id}.json (computed dynamically, not hardcoded)",
        "timeline_event_count": len(timeline_events),
        "summarize_cost_usd": cost_usd,
        "summary_text": summary_text,
        "scorecard": scorecard,
        "judge_output": judged,
    }


if __name__ == "__main__":
    tracker = BudgetTracker()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    for case in discover_cases():
        tool = choose_tool_for_case(case.case_id)
        if tool is None:
            print(f"{case.case_id}: no ship-eligible tool found in its controlled-benchmark result, skipping")
            continue
        print(f"=== pipeline demo: {case.case_id} -> tool {tool} ===")
        result = run_pipeline_demo_for_case(case, tracker, tool=tool)
        out_path = RESULTS_DIR / f"pipeline_demo_{case.case_id}.json"
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        sc = result["scorecard"]
        print(f"  faithfulness={sc['faithfulness']['composite']} ship_eligible={sc['faithfulness']['ship_eligible']} "
              f"coverage={sc['coverage']['weighted_coverage_rate']} usefulness={sc['usefulness']['mean']}")
        print(f"  written to {out_path}")
    print()
    print(tracker.summary())
