"""Deterministic tests for the controlled-benchmark loader (PLAN.md S15).
No live API calls -- reads the real pre-generated summary files on disk."""

from __future__ import annotations

from evalkit.benchmark.controlled import group_by_tool, load_controlled_benchmark
from evalkit.discover import discover_cases


def test_both_cases_have_exactly_four_tools_two_runs_each():
    cases = {c.case_id: c for c in discover_cases()}
    assert set(cases) == {"case-vance", "case-davis"}
    for case in cases.values():
        runs = load_controlled_benchmark(case)
        assert len(runs) == 8, f"{case.case_id}: expected 8 pre-generated summaries, got {len(runs)}"
        grouped = group_by_tool(runs)
        assert set(grouped) == {"A", "B", "C", "D"}
        for tool, tool_runs in grouped.items():
            assert [r.run for r in tool_runs] == [1, 2], f"{case.case_id}/{tool}: {tool_runs}"
            assert all(r.case_id == case.case_id for r in tool_runs)
            assert all(r.summary.strip() for r in tool_runs), "summary text must not be empty"
