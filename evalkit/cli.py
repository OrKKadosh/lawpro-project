"""Thin CLI over already-working, already-tested evalkit modules (PLAN.md
§13). Every subcommand is a few lines wrapping a function that already has
its own unit tests and has already been run for real earlier in this
project -- this file adds no new evaluation logic, only a command-line
entry point, so a reviewer can drive the whole pipeline themselves.

    python -m evalkit.cli list-cases
    python -m evalkit.cli extract <case_id>
    python -m evalkit.cli evaluate-timeline <case_id>
    python -m evalkit.cli summarize <case_id> <tool>
    python -m evalkit.cli evaluate <case_id> <summary_path> [--tool TOOL]
    python -m evalkit.cli run <case_id> [--tool TOOL]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from chronos import client
from chronos import timeline as chronos_timeline
from evalkit.budget import BudgetTracker
from evalkit.discover import discover_cases, get_case
from evalkit.extraction.prepare import run_full_extraction
from evalkit.judge.faithfulness_coverage import judge_summary
from evalkit.judge.material_facts import get_or_build_material_facts
from evalkit.reference.compare import stage0_evaluate
from evalkit.report_readable import render_judge_output
from evalkit.scoring import build_summary_scorecard

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
CANDIDATE_TIMELINES_DIR = ROOT / "runs" / "candidate_timelines"


def _load_candidate_timeline(case_id: str) -> list[dict]:
    path = CANDIDATE_TIMELINES_DIR / f"{case_id}.json"
    if not path.is_file():
        print(f"no extracted timeline found for {case_id} -- run `extract {case_id}` first", file=sys.stderr)
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))["timeline"]["events"]


def cmd_list_cases(args: argparse.Namespace) -> None:
    for case in discover_cases():
        pages = sum(d.pages for d in case.documents)
        print(f"{case.case_id}: {len(case.documents)} documents, {pages} pages")


def prompt_choose_case(cases: list, input_fn=input):
    """Show every case discovered under data/ and prompt for one -- the
    interactive "pick a case" entry point the brief asks for. Accepts
    either the case's number in the printed list or its case_id directly.
    `input_fn` is swappable for testing without real stdin."""
    if not cases:
        print("No cases found under data/ -- nothing to run.", file=sys.stderr)
        sys.exit(1)
    print(f"{len(cases)} case(s) detected under data/:")
    for i, case in enumerate(cases, 1):
        pages = sum(d.pages for d in case.documents)
        print(f"  {i}. {case.case_id} -- {case.label} ({len(case.documents)} documents, {pages} pages)")
    while True:
        choice = input_fn(f"Pick a case (1-{len(cases)}, or type its id): ").strip()
        for case in cases:
            if choice == case.case_id:
                return case
        if choice.isdigit() and 1 <= int(choice) <= len(cases):
            return cases[int(choice) - 1]
        print(f"  '{choice}' isn't a valid choice -- enter a number 1-{len(cases)} or a case id.")


def cmd_extract(args: argparse.Namespace) -> None:
    case = get_case(args.case_id)
    tracker = BudgetTracker()
    result = run_full_extraction(case, tracker)
    CANDIDATE_TIMELINES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = CANDIDATE_TIMELINES_DIR / f"{case.case_id}.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"{case.case_id}: {result['timeline_event_count']} timeline events, "
          f"{len(result['validation_problems'])} schema-validation problems")
    print(f"written to {out_path}")
    print(tracker.summary())


def cmd_evaluate_timeline(args: argparse.Namespace) -> None:
    case = get_case(args.case_id)
    timeline_events = _load_candidate_timeline(case.case_id)
    tracker = BudgetTracker()
    result = stage0_evaluate(case, timeline_events, tracker)
    out_path = RESULTS_DIR / "timeline_eval" / f"{case.case_id}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    es = result["extraction_score"]
    print(f"extraction_score composite={es['composite']} has_confirmed_fabrication={es['has_confirmed_fabrication']}")
    print(f"source_grounded_precision={result['source_grounded_precision']}")
    print(f"written to {out_path}")
    print(tracker.summary())


def cmd_summarize(args: argparse.Namespace) -> None:
    case = get_case(args.case_id)
    timeline_events = _load_candidate_timeline(case.case_id)
    # Non-negotiable per CLAUDE.md: validate before ever calling /v1/summarize.
    chronos_timeline.parse({"events": timeline_events})
    tracker = BudgetTracker()
    response = client.summarize(args.tool, case_id=case.case_id, timeline=timeline_events)
    tracker.record("cli_summarize", response)
    print(json.dumps(response, indent=2))
    print(tracker.summary())


def cmd_evaluate(args: argparse.Namespace) -> None:
    case = get_case(args.case_id)
    summary_text = Path(args.summary_path).read_text(encoding="utf-8")
    timeline_events = _load_candidate_timeline(case.case_id)
    tracker = BudgetTracker()
    fact_set = get_or_build_material_facts(case, tracker)
    material_facts = fact_set["material_facts"]
    tool = args.tool or "unknown"
    judged = judge_summary(
        tracker, case_id=case.case_id, tool=tool, run=args.run,
        summary_text=summary_text, timeline_events=timeline_events, material_facts=material_facts,
    )
    scorecard = build_summary_scorecard(
        tool=tool, run=args.run, cost_usd=0.0, claims=judged["claims"],
        fact_coverage=judged["fact_coverage"], usefulness=judged["usefulness"], material_facts=material_facts,
    )
    print()
    print(render_judge_output(case.case_id, tool, judged, scorecard))
    print()
    out_path = ROOT / "runs" / "cli_evaluations" / f"{case.case_id}_{tool}_run{args.run}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"scorecard": scorecard, "judge_output": judged}, indent=2), encoding="utf-8")
    print(f"Full detail (every claim's evidence, reasoning, and the raw judge output) saved to {out_path}")
    print()
    print(tracker.summary())


def cmd_run(args: argparse.Namespace) -> None:
    """Full pipeline for one case: extract (if needed) -> evaluate-timeline
    -> summarize -> evaluate. Uses the case's ship-eligible tool with the
    highest mean_faithfulness, read dynamically from its own controlled-
    benchmark result (never hardcoded), unless --tool overrides it. This
    is the uncontrolled end-to-end demo path (evalkit/benchmark/
    pipeline_demo.py) -- never the source of the shipping recommendation,
    which lives in results/final_scorecard.md / WRITEUP.md.

    If no case_id is given, this is the interactive entry point: every
    case detected under data/ is listed and the reviewer picks one --
    "pick a case -> generate a timeline -> generate a summary -> evaluate
    it -> inspect the details" as one walkthrough, not five commands they
    have to already know the names of."""
    from evalkit.benchmark.pipeline_demo import choose_tool_for_case, run_pipeline_demo_for_case

    if args.case_id:
        case = get_case(args.case_id)
    else:
        case = prompt_choose_case(discover_cases())
        print(f"\n-> Running the full pipeline for {case.case_id}\n")
    tracker = BudgetTracker()

    print(f"=== Step 1 of 4: read the case's OCR'd documents and build a structured timeline ===")
    candidate_path = CANDIDATE_TIMELINES_DIR / f"{case.case_id}.json"
    if not candidate_path.is_file():
        result = run_full_extraction(case, tracker)
        CANDIDATE_TIMELINES_DIR.mkdir(parents=True, exist_ok=True)
        candidate_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"-> extracted {result['timeline_event_count']} timeline events, saved to {candidate_path}")
    else:
        print(f"-> already have an extracted timeline for this case at {candidate_path} (reusing it)")

    print()
    print("=== Step 2 of 4: check the extracted timeline for accuracy ===")
    timeline_events = _load_candidate_timeline(case.case_id)
    try:
        eval_result = stage0_evaluate(case, timeline_events, tracker)
        es = eval_result["extraction_score"]
        print(f"-> accuracy score: {es['composite']} (1.0 = perfect). "
              f"Possible fabrication found: {'yes -- see details below' if es['has_confirmed_fabrication'] else 'no'}")
    except FileNotFoundError:
        print("-> this case has no reference timeline supplied, so there's nothing to check the "
              "extraction's accuracy against -- skipping this step (the timeline itself is still used below).")

    print()
    print("=== Step 3 of 4: generate a narrative summary from the timeline ===")
    tool = args.tool or choose_tool_for_case(case.case_id)
    if not tool:
        print(f"No tool was specified, and this case has no prior benchmark result to pick one from "
              f"automatically. Re-run with --tool <letter> to choose one yourself.", file=sys.stderr)
        sys.exit(1)
    print(f"-> using tool {tool}")

    print()
    print("=== Step 4 of 4: fact-check the summary and score it ===")
    demo_result = run_pipeline_demo_for_case(case, tracker, tool=tool)
    print()
    print(render_judge_output(case.case_id, tool, demo_result["judge_output"], demo_result["scorecard"]))

    out_path = RESULTS_DIR / f"pipeline_demo_{case.case_id}.json" if case.case_id in ("case-vance", "case-davis") \
        else ROOT / "runs" / "cli_evaluations" / f"{case.case_id}_{tool}_run.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(demo_result, indent=2), encoding="utf-8")
    print()
    print(f"Full detail saved to {out_path}")
    print()
    print(tracker.summary())


COMMANDS = {
    "list-cases": cmd_list_cases,
    "extract": cmd_extract,
    "evaluate-timeline": cmd_evaluate_timeline,
    "summarize": cmd_summarize,
    "evaluate": cmd_evaluate,
    "run": cmd_run,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="evalkit", description="Chronos timeline extraction + summarizer evaluation. "
        "Run with no arguments for an interactive walkthrough: pick a case, generate a timeline, "
        "generate a summary, evaluate it, see the results.",
    )
    sub = parser.add_subparsers(dest="command", required=False)

    sub.add_parser("list-cases", help="List cases discovered under data/")

    p = sub.add_parser("extract", help="Run the extraction pipeline for one case (costs real API calls)")
    p.add_argument("case_id")

    p = sub.add_parser("evaluate-timeline", help="Score an already-extracted timeline against its reference (costs real API calls)")
    p.add_argument("case_id")

    p = sub.add_parser("summarize", help="Call /v1/summarize with an already-extracted timeline (costs real API calls)")
    p.add_argument("case_id")
    p.add_argument("tool")

    p = sub.add_parser("evaluate", help="Judge a summary file against a case's frozen material facts (costs real API calls)")
    p.add_argument("case_id")
    p.add_argument("summary_path")
    p.add_argument("--tool", default=None)
    p.add_argument("--run", type=int, default=1, help="Run number to label this judging as (default 1)")

    p = sub.add_parser("run", help="Full pipeline: extract -> evaluate-timeline -> summarize -> evaluate (costs real API calls)")
    p.add_argument("case_id", nargs="?", default=None, help="Omit to pick interactively from all detected cases")
    p.add_argument("--tool", default=None, help="Override the case's default (already-identified) tool")

    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command is None:
        # No subcommand at all -- the interactive entry point: `python -m evalkit.cli`
        # alone walks a reviewer through the whole pipeline from a clean checkout.
        args = argparse.Namespace(command="run", case_id=None, tool=None)
    COMMANDS[args.command](args)


if __name__ == "__main__":
    main()
