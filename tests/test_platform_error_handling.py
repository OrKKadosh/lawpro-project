"""Regression tests for two real bugs found while manually testing the CLI
against a synthetic case with no platform-side registration:

1. Every subcommand taking a case_id required the exact string -- typing the
   number shown by `list-cases`/the interactive picker (a completely natural
   thing to do, since that's the number just printed on screen) crashed with
   an uncaught KeyError.
2. `/v1/summarize`'s "not_found" PlatformError is shared between "unknown
   case_id" and "unknown tool letter" -- an early fix assumed it always meant
   an unregistered case, which misreported a bad tool letter (e.g. `summarize
   case-vance ZZZ`, a perfectly valid case) as "the platform doesn't
   recognize case_id 'case-vance'", which is false.

No live API calls -- chronos.client.summarize/cases are monkeypatched.
"""

from __future__ import annotations

import pytest

import evalkit.cli as cli
import evalkit.benchmark.pipeline_demo as pipeline_demo
from chronos.client import PlatformError


def _not_found(message: str, detail: dict) -> PlatformError:
    return PlatformError(404, {"error": {"type": "not_found", "message": message, "detail": detail}})


class _FakeCase:
    case_id = "case-vance"


def test_resolve_case_accepts_numeric_index(monkeypatch):
    class A:
        case_id = "case-a"
    class B:
        case_id = "case-b"
    monkeypatch.setattr(cli, "discover_cases", lambda: [A(), B()])
    assert cli._resolve_case("2").case_id == "case-b"
    assert cli._resolve_case("case-a").case_id == "case-a"


def test_resolve_case_reports_known_cases_on_bad_input(monkeypatch, capsys):
    class A:
        case_id = "case-a"
    monkeypatch.setattr(cli, "discover_cases", lambda: [A()])
    with pytest.raises(SystemExit):
        cli._resolve_case("99")
    assert "case-a" in capsys.readouterr().err


def test_cmd_summarize_reports_bad_tool_not_bad_case(monkeypatch, capsys):
    """Regression: this exact scenario (`summarize case-vance ZZZ`) used to
    print 'doesn't recognize case_id case-vance' -- false, since case-vance
    is registered; the real problem was the tool letter."""
    monkeypatch.setattr(cli, "_resolve_case", lambda raw: _FakeCase())
    monkeypatch.setattr(cli, "_load_candidate_timeline", lambda case_id: [{"date": "2024-01-01", "type": "diagnosis", "detail": "x"}])
    monkeypatch.setattr(cli.chronos_timeline, "parse", lambda x: x)

    def boom(*a, **k):
        raise _not_found("No summarisation tool named 'ZZZ'.", {"available_tools": ["A", "B", "C", "D"]})
    monkeypatch.setattr(cli.client, "summarize", boom)

    args = cli.build_parser().parse_args(["summarize", "case-vance", "ZZZ"])
    with pytest.raises(SystemExit):
        cli.cmd_summarize(args)
    err = capsys.readouterr().err
    assert "ZZZ" in err
    assert "available" in err.lower()
    assert "doesn't recognize case_id" not in err


def test_cmd_summarize_reports_unregistered_case_not_bad_tool(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_resolve_case", lambda raw: _FakeCase())
    monkeypatch.setattr(cli, "_load_candidate_timeline", lambda case_id: [{"date": "2024-01-01", "type": "diagnosis", "detail": "x"}])
    monkeypatch.setattr(cli.chronos_timeline, "parse", lambda x: x)

    def boom(*a, **k):
        raise _not_found("No case 'case-vance'.", {})
    monkeypatch.setattr(cli.client, "summarize", boom)
    monkeypatch.setattr(cli.client, "cases", lambda: {"cases": [{"case_id": "case-davis"}]})

    args = cli.build_parser().parse_args(["summarize", "case-vance", "A"])
    with pytest.raises(SystemExit):
        cli.cmd_summarize(args)
    err = capsys.readouterr().err
    assert "doesn't recognize case_id 'case-vance'" in err
    assert "case-davis" in err


def test_pipeline_demo_disambiguates_bad_tool_from_unregistered_case(monkeypatch, tmp_path):
    import json
    candidate_path = tmp_path / "case-vance.json"
    candidate_path.write_text(json.dumps({"timeline": {"events": [{"date": "2024-01-01", "type": "diagnosis", "detail": "x"}]}}), encoding="utf-8")
    monkeypatch.setattr(pipeline_demo, "CANDIDATE_TIMELINES_DIR", tmp_path)
    monkeypatch.setattr(pipeline_demo.chronos_timeline, "parse", lambda x: x)

    from evalkit.budget import BudgetTracker
    tracker = BudgetTracker()

    def boom_tool(*a, **k):
        raise _not_found("No summarisation tool named 'ZZZ'.", {"available_tools": ["A", "B", "C", "D"]})
    monkeypatch.setattr(pipeline_demo.client, "summarize", boom_tool)
    with pytest.raises(RuntimeError, match="No summarization tool 'ZZZ'"):
        pipeline_demo.run_pipeline_demo_for_case(_FakeCase(), tracker, tool="ZZZ")

    def boom_case(*a, **k):
        raise _not_found("No case 'case-vance'.", {})
    monkeypatch.setattr(pipeline_demo.client, "summarize", boom_case)
    with pytest.raises(RuntimeError, match="doesn't recognize case_id 'case-vance'"):
        pipeline_demo.run_pipeline_demo_for_case(_FakeCase(), tracker, tool="A")
