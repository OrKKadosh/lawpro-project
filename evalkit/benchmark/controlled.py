"""Controlled summarizer benchmark (PLAN.md S8).

Both cases have a confirmed exact input behind their 8 pre-generated
summaries -- golden for Vance (confirmed via the hiring contact), the
shipped input_timeline.json for Davis. With input identity established for
both, each case's 8 supplied summaries ARE the controlled benchmark
directly: loaded and validated here, not regenerated with fresh
/v1/summarize calls (PLAN.md S8: optional symmetry/sanity-check only, not
methodologically required for either case now that identity is confirmed).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from evalkit.discover import Case


@dataclass
class SummaryRun:
    tool: str
    run: int
    case_id: str
    summary: str
    cost_usd: float
    path: str


def load_controlled_benchmark(case: Case) -> list[SummaryRun]:
    """The case's 8 pre-generated summaries -- the controlled benchmark
    itself (PLAN.md S8), not diagnostic-only data. Raises if any file is
    missing an expected field rather than silently loading a partial run."""
    runs = []
    for path in case.pregenerated_summary_paths():
        data = json.loads(path.read_text(encoding="utf-8"))
        for field_name in ("tool", "run", "case_id", "summary"):
            if field_name not in data:
                raise ValueError(f"{path}: missing required field {field_name!r}")
        runs.append(
            SummaryRun(
                tool=data["tool"], run=data["run"], case_id=data["case_id"],
                summary=data["summary"], cost_usd=data.get("cost_usd", 0.0), path=str(path),
            )
        )
    return runs


def group_by_tool(runs: list[SummaryRun]) -> dict[str, list[SummaryRun]]:
    grouped: dict[str, list[SummaryRun]] = {}
    for r in runs:
        grouped.setdefault(r.tool, []).append(r)
    for tool_runs in grouped.values():
        tool_runs.sort(key=lambda r: r.run)
    return grouped
