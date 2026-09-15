"""Budget tracking for the evalkit pipeline.

Wraps chronos.client calls to log cost_usd, accumulate spend by call
category (extraction / judge / summarize / experiment), print a running
total after every paid call, and refuse further paid calls once remaining
budget drops below a configurable floor.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from chronos import client

DEFAULT_FLOOR_USD = 1.0
LOG_PATH = Path(__file__).resolve().parents[1] / "runs" / "budget_log.jsonl"

# Plain-English labels for internal call categories, shown to a human
# running the CLI -- the raw category strings (unchanged, still the ones
# written to runs/budget_log.jsonl for anyone who wants the precise
# technical trail) aren't meaningful on their own to someone who didn't
# write this codebase. Falls back to the raw string for anything not
# listed here, so a new/unlisted category never breaks, just looks
# slightly less polished.
CATEGORY_LABELS = {
    "extraction": "reading clinical events out of the documents",
    "chunk_experiment": "chunking-size experiment",
    "prompt_experiment": "extraction-prompt comparison experiment",
    "source_audit": "checking the reference timeline against the source documents",
    "stage0_candidate_audit": "checking our extracted timeline against the source documents",
    "extraction_agreement_check": "checking whether two timeline events actually describe the same thing",
    "material_facts": "building the checklist of facts a good summary should cover",
    "faithfulness_coverage": "fact-checking a summary against the timeline",
    "stability": "comparing two runs of the same summarizer for consistency",
    "pipeline_demo_summarize": "generating a summary",
    "pipeline_demo_judge": "fact-checking the generated summary",
    "cli_summarize": "generating a summary",
}


def _label(category: str) -> str:
    return CATEGORY_LABELS.get(category, category)


class BudgetExceeded(RuntimeError):
    """Raised when a paid call would be attempted below the configured floor."""


@dataclass
class BudgetTracker:
    floor_usd: float = DEFAULT_FLOOR_USD
    log_path: Path = LOG_PATH
    spent_by_category: dict[str, float] = field(default_factory=dict)
    call_count_by_category: dict[str, int] = field(default_factory=dict)
    total_spent: float = 0.0
    remaining: Optional[float] = None

    def check_floor(self) -> None:
        if self.remaining is not None and self.remaining < self.floor_usd:
            raise BudgetExceeded(
                f"Remaining budget ${self.remaining:.4f} is below the floor "
                f"${self.floor_usd:.2f} -- refusing further paid calls."
            )

    def record(self, category: str, response: dict) -> None:
        cost = response.get("cost_usd", 0.0)
        budget = response.get("budget", {})
        if "remaining_usd" in budget:
            self.remaining = budget["remaining_usd"]
        self.total_spent += cost
        self.spent_by_category[category] = self.spent_by_category.get(category, 0.0) + cost
        self.call_count_by_category[category] = self.call_count_by_category.get(category, 0) + 1
        self._log(category, cost, budget)
        remaining_str = f"${self.remaining:.4f}" if self.remaining is not None else "unknown"
        print(
            f"  [{_label(category)}] +${cost:.4f} "
            f"(spent so far ${self.total_spent:.4f}, {remaining_str} left of the budget)"
        )

    def _log(self, category: str, cost: float, budget: dict) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": time.time(),
            "category": category,
            "cost_usd": cost,
            "session_total_usd": self.total_spent,
            "budget": budget,
        }
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def summary(self) -> str:
        lines = [f"Total spent this run: ${self.total_spent:.4f}"]
        for cat, amt in sorted(self.spent_by_category.items()):
            n = self.call_count_by_category[cat]
            lines.append(f"  {_label(cat)} ({cat}): ${amt:.4f}, {n} call{'s' if n != 1 else ''}")
        if self.remaining is not None:
            lines.append(f"Remaining in the shared budget: ${self.remaining:.4f}")
        return "\n".join(lines)


def check_live_budget() -> dict:
    """Free GET /v1/budget -- no cost, safe to call anytime."""
    return client.budget()
