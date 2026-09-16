"""Regression tests for the three real bugs found by the code-reviewer and
eval-reviewer subagents (CLAUDE.md's mandatory post-change review pass).
No live API calls -- everything is monkeypatched.
"""

from __future__ import annotations

import pytest

import evalkit.cli as cli
import evalkit.benchmark.pipeline_demo as pipeline_demo
import evalkit.reference.audit as audit
from evalkit.budget import BudgetExceeded, BudgetTracker


class _FakeCase:
    case_id = "case-no-ref"


def test_cmd_evaluate_timeline_degrades_gracefully_with_no_reference(monkeypatch, capsys):
    """Regression: the standalone `evaluate-timeline` subcommand used to
    crash uncaught on any case with no reference timeline, even though
    `cmd_run`'s inline call to the same function was already fixed --
    PROGRESS.md claimed this was handled everywhere; it wasn't."""
    monkeypatch.setattr(cli, "_resolve_case", lambda case_id: _FakeCase())
    monkeypatch.setattr(cli, "_load_candidate_timeline", lambda case_id: [{"date": "2024-01-01", "type": "diagnosis", "detail": "x"}])

    def fake_stage0_evaluate(case, events, tracker):
        raise FileNotFoundError("no reference timeline")
    monkeypatch.setattr(cli, "stage0_evaluate", fake_stage0_evaluate)

    args = cli.build_parser().parse_args(["evaluate-timeline", "case-no-ref"])
    cli.cmd_evaluate_timeline(args)  # must not raise
    assert "no reference timeline" in capsys.readouterr().out.lower()


def test_cli_summarize_checks_budget_floor_before_the_paid_call(monkeypatch):
    """Regression: /v1/summarize calls in cli.py and pipeline_demo.py never
    consulted the budget floor -- check_floor() was only ever called by
    call_json (used for /v1/generate), leaving the single most expensive
    call in the pipeline with no floor protection at all."""
    monkeypatch.setattr(cli, "_resolve_case", lambda case_id: _FakeCase())
    monkeypatch.setattr(cli, "_load_candidate_timeline", lambda case_id: [{"date": "2024-01-01", "type": "diagnosis", "detail": "x"}])
    monkeypatch.setattr(cli.chronos_timeline, "parse", lambda x: x)

    def refuse(self):
        raise BudgetExceeded("floor hit")
    monkeypatch.setattr(BudgetTracker, "check_floor", refuse)

    def boom(*a, **k):
        raise AssertionError("client.summarize must never be reached once the floor check refuses")
    monkeypatch.setattr(cli.client, "summarize", boom)

    args = cli.build_parser().parse_args(["summarize", "case-no-ref", "D"])
    with pytest.raises(BudgetExceeded):
        cli.cmd_summarize(args)


def test_pipeline_demo_checks_budget_floor_before_the_paid_call(monkeypatch, tmp_path):
    import json
    candidate_path = tmp_path / "case-no-ref.json"
    candidate_path.write_text(json.dumps({"timeline": {"events": [{"date": "2024-01-01", "type": "diagnosis", "detail": "x"}]}}), encoding="utf-8")
    monkeypatch.setattr(pipeline_demo, "CANDIDATE_TIMELINES_DIR", tmp_path)
    monkeypatch.setattr(pipeline_demo.chronos_timeline, "parse", lambda x: x)

    tracker = BudgetTracker()
    def refuse():
        raise BudgetExceeded("floor hit")
    monkeypatch.setattr(tracker, "check_floor", refuse)

    def boom(*a, **k):
        raise AssertionError("client.summarize must never be reached once the floor check refuses")
    monkeypatch.setattr(pipeline_demo.client, "summarize", boom)

    with pytest.raises(BudgetExceeded):
        pipeline_demo.run_pipeline_demo_for_case(_FakeCase(), tracker, tool="D")


def test_audit_events_reraises_budget_exceeded_instead_of_swallowing_it(monkeypatch, tmp_path):
    """Regression: a bare `except Exception` around the per-document judge
    call swallowed BudgetExceeded exactly like an ordinary bad-OCR failure,
    letting the loop keep iterating (re-hitting and re-swallowing it on
    every remaining document) and scoring source_grounded_precision from
    a silently-incomplete sample."""
    class FakeCase:
        case_id = "case-x"
        def ocr_pages(self, doc_id):
            return ["page 1 text"]
        def ocr_text(self, doc_id):
            return "some ocr text"

    def raise_budget_exceeded(*a, **k):
        raise BudgetExceeded("floor hit")
    monkeypatch.setattr(audit, "call_json", raise_budget_exceeded)

    events = [{"date": "2024-01-01", "type": "procedure", "detail": "x", "source": "doc1 p1"}]
    with pytest.raises(BudgetExceeded):
        audit.audit_events(FakeCase(), events, tracker=None)


def test_audit_events_still_tolerates_an_ordinary_judge_failure(monkeypatch):
    """The fix must not turn BudgetExceeded-handling into "stop tolerating
    anything" -- an ordinary malformed-JSON/LLMCallError must still be
    recorded and skipped, not propagated."""
    class FakeCase:
        case_id = "case-x"
        def ocr_pages(self, doc_id):
            return ["page 1 text"]
        def ocr_text(self, doc_id):
            return "some ocr text"

    def raise_ordinary_error(*a, **k):
        raise RuntimeError("malformed JSON")
    monkeypatch.setattr(audit, "call_json", raise_ordinary_error)

    events = [{"date": "2024-01-01", "type": "procedure", "detail": "x", "source": "doc1 p1"}]
    report = audit.audit_events(FakeCase(), events, tracker=None)  # must not raise
    assert len(report.judge_call_failures) == 1
