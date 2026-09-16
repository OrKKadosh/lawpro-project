"""Runs the controlled benchmark's judge calls and renders the final
scorecard (PLAN.md S9/S10/S14).

For each case: load the 8 pre-generated summaries (the controlled
benchmark itself, PLAN.md S8) and the frozen material_fact_set, run the
faithfulness+coverage+usefulness judge on each summary against the exact
benchmark timeline, run the pairwise-stability judge once per tool (run1 vs
run2), and score everything deterministically via scoring.py.
"""

from __future__ import annotations

import json
from pathlib import Path

from chronos import timeline as chronos_timeline
from evalkit.benchmark.controlled import group_by_tool, load_controlled_benchmark
from evalkit.budget import BudgetTracker
from evalkit.discover import Case, discover_cases
from evalkit.judge.faithfulness_coverage import judge_summary
from evalkit.judge.material_facts import load_frozen
from evalkit.judge.stability import judge_stability
from evalkit.scoring import aggregate_tool_scorecard, build_summary_scorecard, score_stability

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"


def run_controlled_benchmark_for_case(case: Case, tracker: BudgetTracker) -> dict:
    fact_set = load_frozen(case.case_id)
    material_facts = fact_set["material_facts"]
    benchmark_events = chronos_timeline.parse(case.reference_timeline_path().read_text(encoding="utf-8"))

    runs = load_controlled_benchmark(case)
    grouped = group_by_tool(runs)

    tool_scorecards = {}
    for tool, tool_runs in sorted(grouped.items()):
        run_scorecards = []
        judge_outputs = []
        for r in tool_runs:
            judged = judge_summary(
                tracker, case_id=case.case_id, tool=tool, run=r.run,
                summary_text=r.summary, timeline_events=benchmark_events, material_facts=material_facts,
            )
            judge_outputs.append(judged)
            scorecard = build_summary_scorecard(
                tool=tool, run=r.run, cost_usd=r.cost_usd,
                claims=judged["claims"], fact_coverage=judged["fact_coverage"],
                usefulness=judged["usefulness"], material_facts=material_facts,
                summary_text=r.summary,
            )
            run_scorecards.append(scorecard)

        stability = None
        if len(tool_runs) == 2:
            stability_raw = judge_stability(
                tracker, case_id=case.case_id, tool=tool,
                run1_summary=tool_runs[0].summary, run2_summary=tool_runs[1].summary,
            )
            stability = score_stability(stability_raw["claim_pairs"])
            stability["raw_claim_pairs"] = stability_raw["claim_pairs"]

        tool_scorecards[tool] = aggregate_tool_scorecard(run_scorecards, stability)
        tool_scorecards[tool]["judge_outputs"] = judge_outputs

    return {
        "case_id": case.case_id,
        "material_fact_set_path": str(Path("results/material_facts") / f"{case.case_id}.json"),
        "benchmark_event_count": len(benchmark_events),
        "tools": tool_scorecards,
    }


def render_final_report(all_case_results: dict[str, dict]) -> str:
    lines = ["# Final Scorecard — Controlled Summarizer Benchmark", ""]
    lines.append(
        "Every score below is indexed `(case_id, tool_letter)`. A/B/C/D are case-local identifiers, "
        "not stable backends across cases (PLAN.md §1) — this table is never read as \"tool X wins\" "
        "across both rows, only per case."
    )
    lines.append("")
    for case_id, result in all_case_results.items():
        lines.append(f"## {case_id}")
        lines.append("")
        lines.append("| Tool | Faithfulness | Ship-eligible | Coverage | Usefulness | Shared-topic agreement | Content-overlap stability | Critical cross-run conflicts | Mean cost/summary |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for tool, tc in sorted(result["tools"].items()):
            stab = tc.get("stability") or {}
            lines.append(
                f"| {tool} | {tc['mean_faithfulness']} | {'yes' if tc['ship_eligible'] else '**NO**'} | "
                f"{tc['mean_coverage']} | {tc['mean_usefulness']} | "
                f"{stab.get('shared_topic_agreement_rate')} | {stab.get('content_overlap_stability_rate')} | "
                f"{stab.get('critical_cross_run_conflict_count')} | "
                f"${tc['mean_cost_usd']} |"
            )
        lines.append("")
        lines.append(
            "*Shared-topic agreement* = agree / (agree + disagree) across material facts BOTH runs mention -- "
            "silent on content only one run mentions. *Content-overlap stability* = agree / (agree + disagree + "
            "run1-only + run2-only) -- the number that actually catches a run silently dropping or adding a large "
            "chunk of material content (FINDINGS.md: shared-topic agreement alone can show 1.0 even when one run "
            "omits most of the other's material facts -- never read that number alone as \"stability\")."
        )
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    tracker = BudgetTracker()
    all_results = {}
    for case in discover_cases():
        print(f"=== controlled benchmark: {case.case_id} ===")
        result = run_controlled_benchmark_for_case(case, tracker)
        all_results[case.case_id] = result
        out_path = RESULTS_DIR / f"controlled_benchmark_{case.case_id}.json"
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"  written to {out_path}")

    report = render_final_report(all_results)
    (RESULTS_DIR / "final_scorecard.md").write_text(report, encoding="utf-8")
    print()
    print(report)
    print()
    print(tracker.summary())
