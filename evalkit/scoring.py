"""Deterministic scoring from judge annotations (PLAN.md S9/S10).

Every judge produces evidence (claims, fact-coverage verdicts, usefulness
ratings) -- this module is the only place a composite number or a gate
decision gets computed. Weights and the gate condition are frozen in
DECISIONS.md before this runs against any controlled-benchmark summary.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Optional

SEVERITY_WEIGHTS = {"critical": 5, "major": 2, "minor": 1}
GATE_TRIGGER_STATUSES = {"unsupported", "contradicted", "overclaimed"}
REFLECTED_SCORE = {"yes": 1.0, "partial": 0.5, "no": 0.0}


def score_faithfulness(claims: list[dict[str, Any]]) -> dict[str, Any]:
    total_weight = sum(SEVERITY_WEIGHTS.get(c.get("materiality"), 1) for c in claims)
    flawed = [c for c in claims if c.get("status") != "supported"]
    flawed_weight = sum(SEVERITY_WEIGHTS.get(c.get("materiality"), 1) for c in flawed)
    composite = 1.0 - (flawed_weight / total_weight) if total_weight else None

    gate_triggers = [
        c for c in claims
        if c.get("materiality") == "critical" and c.get("status") in GATE_TRIGGER_STATUSES
    ]

    return {
        "composite": round(composite, 3) if composite is not None else None,
        "ship_eligible": len(gate_triggers) == 0,
        "gate_triggering_claims": gate_triggers,
        "claim_count": len(claims),
        "flawed_claim_count": len(flawed),
        "claim_counts_by_status": dict(Counter(c.get("status") for c in claims)),
        "claim_counts_by_materiality": dict(Counter(c.get("materiality") for c in claims)),
    }


def score_coverage(fact_coverage: list[dict[str, Any]], material_facts: list[dict[str, Any]]) -> dict[str, Any]:
    weight_by_id = {f["fact_id"]: f.get("materiality_weight", 1) for f in material_facts}
    total_weight = sum(weight_by_id.values())
    coverage_by_id = {fc["fact_id"]: fc.get("reflected") for fc in fact_coverage}
    achieved = sum(
        weight_by_id.get(fact_id, 0) * REFLECTED_SCORE.get(coverage_by_id.get(fact_id), 0.0)
        for fact_id in weight_by_id
    )
    rate = achieved / total_weight if total_weight else None
    missing = [
        fact_id for fact_id, w in weight_by_id.items()
        if coverage_by_id.get(fact_id) == "no"
    ]
    return {
        "weighted_coverage_rate": round(rate, 3) if rate is not None else None,
        "facts_total": len(weight_by_id),
        "facts_missing": missing,
        "coverage_by_fact_id": coverage_by_id,
    }


def score_usefulness(usefulness: dict[str, Any]) -> dict[str, Any]:
    values = [v for v in usefulness.values() if isinstance(v, (int, float))]
    mean = sum(values) / len(values) if values else None
    return {"mean": round(mean, 2) if mean is not None else None, "by_dimension": usefulness}


def score_stability(claim_pairs: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(p.get("relation") for p in claim_pairs)
    agree, disagree = counts.get("agree", 0), counts.get("disagree", 0)
    aligned = agree + disagree
    overlap_rate = agree / aligned if aligned else None
    critical_conflicts = sum(
        1 for p in claim_pairs if p.get("relation") == "disagree" and p.get("materiality") == "critical"
    )
    return {
        "material_fact_overlap_rate": round(overlap_rate, 3) if overlap_rate is not None else None,
        "critical_cross_run_conflict_count": critical_conflicts,
        "agree": agree, "disagree": disagree,
        "run1_only": counts.get("run1_only", 0), "run2_only": counts.get("run2_only", 0),
    }


def build_summary_scorecard(
    *, tool: str, run: int, cost_usd: float,
    claims: list[dict], fact_coverage: list[dict], usefulness: dict,
    material_facts: list[dict],
) -> dict[str, Any]:
    return {
        "tool": tool, "run": run, "cost_usd": cost_usd,
        "faithfulness": score_faithfulness(claims),
        "coverage": score_coverage(fact_coverage, material_facts),
        "usefulness": score_usefulness(usefulness),
    }


def aggregate_tool_scorecard(run_scorecards: list[dict[str, Any]], stability: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Combine both runs' per-summary scorecards for one tool into one
    tool-level entry, plus the pairwise-stability result between them."""
    if not run_scorecards:
        return {}
    tool = run_scorecards[0]["tool"]
    faithfulness_composites = [r["faithfulness"]["composite"] for r in run_scorecards if r["faithfulness"]["composite"] is not None]
    coverage_rates = [r["coverage"]["weighted_coverage_rate"] for r in run_scorecards if r["coverage"]["weighted_coverage_rate"] is not None]
    usefulness_means = [r["usefulness"]["mean"] for r in run_scorecards if r["usefulness"]["mean"] is not None]
    ship_eligible = all(r["faithfulness"]["ship_eligible"] for r in run_scorecards)
    total_cost = sum(r["cost_usd"] for r in run_scorecards)

    return {
        "tool": tool,
        "runs": run_scorecards,
        "mean_faithfulness": round(sum(faithfulness_composites) / len(faithfulness_composites), 3) if faithfulness_composites else None,
        "mean_coverage": round(sum(coverage_rates) / len(coverage_rates), 3) if coverage_rates else None,
        "mean_usefulness": round(sum(usefulness_means) / len(usefulness_means), 2) if usefulness_means else None,
        "ship_eligible": ship_eligible,
        "total_cost_usd": round(total_cost, 4),
        "mean_cost_usd": round(total_cost / len(run_scorecards), 4) if run_scorecards else None,
        "stability": stability,
    }
