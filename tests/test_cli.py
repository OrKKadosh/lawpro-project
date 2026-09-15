"""CLI tests -- the interactive case picker and argument wiring. No live
API calls, no real file writes: prompt_choose_case takes fake in-memory
Case objects and a swappable input function, never touches real data/ or
runs/.
"""

from __future__ import annotations

import pytest

from evalkit.cli import build_parser, prompt_choose_case
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
