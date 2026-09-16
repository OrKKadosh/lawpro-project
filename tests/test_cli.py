"""CLI tests -- the interactive case picker and argument wiring. No live
API calls, no real file writes: prompt_choose_case takes fake in-memory
Case objects and a swappable input function, never touches real data/ or
runs/.
"""

from __future__ import annotations

import sys

import pytest

from evalkit.cli import build_parser, prompt_choose_case, prompt_choose_tool
from evalkit.discover import Case, CaseDoc


def _case(case_id: str, label: str, pages: int) -> Case:
    return Case(case_id=case_id, label=label, documents=[CaseDoc("d1", "Doc 1", pages)],
                ocr_dir=None, pdf_dir=None, summaries_dir=None, manifest_path=None)


FAKE_CASES = [_case("case-alpha", "Alpha", 3), _case("case-beta", "Beta", 5)]


def test_prompt_choose_case_by_number():
    picked = prompt_choose_case(FAKE_CASES, input_fn=lambda prompt: "2")
    assert picked.case_id == "case-beta"


def test_prompt_choose_case_by_id():
    picked = prompt_choose_case(FAKE_CASES, input_fn=lambda prompt: "case-alpha")
    assert picked.case_id == "case-alpha"


def test_prompt_choose_case_reprompts_on_invalid_input():
    inputs = iter(["not-a-real-case", "99", "1"])
    picked = prompt_choose_case(FAKE_CASES, input_fn=lambda prompt: next(inputs))
    assert picked.case_id == "case-alpha"


def test_prompt_choose_case_exits_when_no_cases_found():
    with pytest.raises(SystemExit):
        prompt_choose_case([], input_fn=lambda prompt: "1")


def test_run_command_case_id_is_optional_for_interactive_mode():
    args = build_parser().parse_args(["run"])
    assert args.case_id is None


def test_no_subcommand_at_all_defaults_to_run_via_main(monkeypatch):
    """`python -m evalkit.cli` with zero arguments must behave like `run`
    with no case_id (the interactive entry point) -- verified by checking
    which command dispatches, not by actually running the pipeline."""
    import evalkit.cli as cli
    seen = {}
    monkeypatch.setitem(cli.COMMANDS, "run", lambda args: seen.update(command="run", case_id=args.case_id))
    cli.main([])
    assert seen == {"command": "run", "case_id": None}


def test_other_subcommands_still_require_their_case_id():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["extract"])


def test_prompt_choose_tool_accepts_a_valid_letter():
    assert prompt_choose_tool("case-x", input_fn=lambda prompt: "b") == "B"


def test_prompt_choose_tool_reprompts_on_invalid_letter():
    inputs = iter(["Z", "not a letter", "C"])
    assert prompt_choose_tool("case-x", input_fn=lambda prompt: next(inputs)) == "C"


def test_cmd_run_prompts_for_a_tool_interactively_when_no_benchmark_exists(monkeypatch, tmp_path, capsys):
    """Regression: a case with no prior controlled-benchmark result (e.g. a
    genuinely new case) used to hard-exit telling the reviewer to re-run
    with --tool, even in an interactive session where prompting is the
    obvious, friendlier thing to do. Only checked when stdin is a real
    terminal (sys.stdin.isatty()) -- a non-interactive/scripted invocation
    must keep the old hard-error behavior, so scriptability is preserved."""
    import json
    import evalkit.cli as cli

    class _FakeCase:
        case_id = "case-new"

    candidate_path = tmp_path / "case-new.json"
    candidate_path.write_text(json.dumps({"timeline": {"events": [
        {"date": "2024-01-01", "type": "diagnosis", "detail": "x"}
    ]}}), encoding="utf-8")
    monkeypatch.setattr(cli, "CANDIDATE_TIMELINES_DIR", tmp_path)
    monkeypatch.setattr(cli, "_resolve_case", lambda raw: _FakeCase())
    monkeypatch.setattr("evalkit.benchmark.pipeline_demo.choose_tool_for_case", lambda case_id: None)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(cli, "prompt_choose_tool", lambda case_id, input_fn=input: "D")
    monkeypatch.setattr(cli, "stage0_evaluate", lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError()))

    import evalkit.benchmark.pipeline_demo as pipeline_demo
    monkeypatch.setattr(pipeline_demo, "run_pipeline_demo_for_case", lambda case, tracker, tool=None: {
        "case_id": case.case_id, "chosen_tool": tool, "judge_output": {"claims": [], "fact_coverage": [], "usefulness": {}},
        "scorecard": {
            "faithfulness": {"ship_eligible": True, "composite": 1.0, "gate_triggering_claims": []},
            "coverage": {"weighted_coverage_rate": 1.0, "facts_missing": [], "coverage_by_fact_id": {}},
            "usefulness": {"mean": 5.0, "by_dimension": {}},
        },
    })

    args = cli.build_parser().parse_args(["run", "case-new"])
    cli.cmd_run(args)
    out = capsys.readouterr().out
    assert "using tool D" in out


def test_cmd_run_still_hard_errors_when_stdin_is_not_interactive(monkeypatch, tmp_path, capsys):
    """Scriptability preserved: a non-interactive invocation (piped/redirected
    stdin, e.g. CI) must keep demanding --tool explicitly rather than
    silently blocking on a prompt() call that would hang forever."""
    import json
    import evalkit.cli as cli

    class _FakeCase:
        case_id = "case-new"

    candidate_path = tmp_path / "case-new.json"
    candidate_path.write_text(json.dumps({"timeline": {"events": [
        {"date": "2024-01-01", "type": "diagnosis", "detail": "x"}
    ]}}), encoding="utf-8")
    monkeypatch.setattr(cli, "CANDIDATE_TIMELINES_DIR", tmp_path)
    monkeypatch.setattr(cli, "_resolve_case", lambda raw: _FakeCase())
    monkeypatch.setattr("evalkit.benchmark.pipeline_demo.choose_tool_for_case", lambda case_id: None)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

    def must_not_be_called(case_id, input_fn=input):
        raise AssertionError("prompt_choose_tool must never be called when stdin is not interactive")
    monkeypatch.setattr(cli, "prompt_choose_tool", must_not_be_called)
    monkeypatch.setattr(cli, "stage0_evaluate", lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError()))

    args = cli.build_parser().parse_args(["run", "case-new"])
    with pytest.raises(SystemExit):
        cli.cmd_run(args)
    assert "Re-run with --tool" in capsys.readouterr().err
