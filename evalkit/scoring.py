"""Deterministic scoring from judge annotations (PLAN.md S9/S10).

Every judge produces evidence (claims, fact-coverage verdicts, usefulness
ratings) -- this module is the only place a composite number or a gate
decision gets computed. Weights and the gate condition are frozen in
DECISIONS.md before this runs against any controlled-benchmark summary.
"""

from __future__ import annotations

import re

from collections import Counter
from typing import Any, Optional

SEVERITY_WEIGHTS = {"critical": 5, "major": 2, "minor": 1}
GATE_TRIGGER_STATUSES = {"unsupported", "contradicted", "overclaimed"}
REFLECTED_SCORE = {"yes": 1.0, "partial": 0.5, "no": 0.0}

# LEGACY / DIAGNOSTIC-ONLY FALLBACK -- NOT the primary safeguard against
# omission-shaped claims anymore. That job now belongs structurally to
# evalkit/judge/schemas.py's validate_faithfulness_coverage_output(), which
# REQUIRES every claim to carry a non-empty summary_quote that's an actual
# substring of the summary, with a mandatory repair-retry and a hard
# JudgeOutputInvalid failure if it still isn't -- checked BEFORE a judge
# result is ever handed to this scoring layer (evalkit/judge/faithfulness_
# coverage.py's judge_summary()). Every controlled-benchmark run scored
# after that fix was introduced has real, validated summary_quotes on
# every claim, so this regex heuristic never fires for them (the `if quote:
# return False` line below always short-circuits first).
#
# This heuristic exists ONLY for claims with no summary_quote at all --
# i.e. judge output collected before the schema-validation fix existed.
# FOUND, THE HARD WAY, TO BE UNSAFE AS A GENERAL-PURPOSE CLASSIFIER
# (FINDINGS.md): checked against the real pre-fix committed benchmark data,
# it wrongly matched genuine unsupported factual assertions whose `reason`
# field happened to contain phrasing like "does not state" (e.g. "The
# rehabilitation delay was caused by insurer authorization" -- a real,
# major-materiality unsupported claim -- was at risk of being excluded
# because its reason said "...timeline does not state this delay as the
# actual explanation..."). Do NOT rely on this path for the primary
# controlled benchmark; it is retained only so a caller that somehow still
# has old, quote-less judge JSON on hand (a historical diagnostic run, not
# the controlled benchmark) doesn't crash outright -- never trust its
# output as authoritative, and never use it in place of a real re-judge.
_OMISSION_CLAIM_RE = re.compile(
    r"\bno mention\b|\bnot mention(ed)?\b|\bomit(s|ted|ting)?\b|"
    r"\bmissing from (the )?summary\b|\babsent from (the )?summary\b|"
    r"\b(does not|doesn't|fails? to) (state|mention|include|discuss|cover|address)\b|"
    r"\bnot (discussed|covered|addressed|included) (in|by) the summary\b",
    re.IGNORECASE,
)


def is_omission_shaped_claim(claim: dict[str, Any]) -> bool:
    """LEGACY-ONLY fallback -- see the module-level comment above
    _OMISSION_CLAIM_RE for the full rationale and its known false-positive
    risk. True if this claims[] entry describes an OMISSION (content the
    summary doesn't contain) rather than a factual assertion the summary
    actually makes. A claim with a real `summary_quote` (verbatim text from
    the summary, now REQUIRED and validated upstream for any current judge
    run) is never omission-shaped by construction -- it's anchored to
    something the summary really says, and this function returns False for
    it immediately without ever consulting the unsafe regex heuristic."""
    quote = (claim.get("summary_quote") or "").strip()
    if quote:
        return False
    text = f"{claim.get('text') or ''} {claim.get('reason') or ''}"
    return bool(_OMISSION_CLAIM_RE.search(text))


def _normalize_for_substring_check(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def is_untraceable_claim(claim: dict[str, Any], summary_text: Optional[str]) -> bool:
    """True if this claim carries a `summary_quote` that does NOT actually
    appear in the summary text -- a hallucinated or fabricated provenance
    anchor, which is exactly what the summary_quote safeguard exists to
    catch (PLAN.md S10's "the judge proposes evidence, code decides"
    principle: a claimed quote is evidence to verify, not to trust as-is).
    Only checked when `summary_text` is actually available and the claim
    has a non-empty quote -- an empty quote is handled by
    is_omission_shaped_claim() instead, not here."""
    if not summary_text:
        return False
    quote = (claim.get("summary_quote") or "").strip()
    if not quote:
        return False
    return _normalize_for_substring_check(quote) not in _normalize_for_substring_check(summary_text)


def score_faithfulness(claims: list[dict[str, Any]], summary_text: Optional[str] = None) -> dict[str, Any]:
    omitted = [c for c in claims if is_omission_shaped_claim(c)]
    untraceable = [c for c in claims if c not in omitted and is_untraceable_claim(c, summary_text)]
    excluded = omitted + untraceable
    claims = [c for c in claims if c not in excluded]

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
        "omission_shaped_claims_excluded": len(omitted),
        "untraceable_claims_excluded": len(untraceable),
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
    """Two deliberately separate numbers, not one "stability" score --
    conflating them was a real bug (FINDINGS.md): a run pair where run2
    drops most of run1's material content but never outright CONTRADICTS
    what little it does share could previously report a misleadingly
    perfect 1.0, because `run1_only`/`run2_only` topics were counted but
    silently excluded from the metric's denominator.

    - `shared_topic_agreement_rate`: agree / (agree + disagree). Answers
      "when both runs discuss the same topic, do they agree?" -- silent on
      content either run drops or adds entirely.
    - `content_overlap_stability_rate`: agree / (agree + disagree +
      run1_only + run2_only). Answers "how much of the combined material
      content is actually stable across both runs?" -- this is the number
      that catches a run silently dropping most of its content, and is the
      one that should be read as the headline "stability" figure if only
      one number is shown.
    Never label `shared_topic_agreement_rate` alone as "stability" --
    it can't detect the exact failure mode stability is meant to catch."""
    counts = Counter(p.get("relation") for p in claim_pairs)
    agree, disagree = counts.get("agree", 0), counts.get("disagree", 0)
    run1_only, run2_only = counts.get("run1_only", 0), counts.get("run2_only", 0)
    aligned = agree + disagree
    all_topics = aligned + run1_only + run2_only
    shared_topic_agreement_rate = agree / aligned if aligned else None
    content_overlap_stability_rate = agree / all_topics if all_topics else None
    critical_conflicts = sum(
        1 for p in claim_pairs if p.get("relation") == "disagree" and p.get("materiality") == "critical"
    )
    return {
        "shared_topic_agreement_rate": round(shared_topic_agreement_rate, 3) if shared_topic_agreement_rate is not None else None,
        "content_overlap_stability_rate": round(content_overlap_stability_rate, 3) if content_overlap_stability_rate is not None else None,
        "critical_cross_run_conflict_count": critical_conflicts,
        "agree": agree, "disagree": disagree,
        "run1_only": run1_only, "run2_only": run2_only,
    }


def build_summary_scorecard(
    *, tool: str, run: int, cost_usd: float,
    claims: list[dict], fact_coverage: list[dict], usefulness: dict,
    material_facts: list[dict], summary_text: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "tool": tool, "run": run, "cost_usd": cost_usd,
        "faithfulness": score_faithfulness(claims, summary_text),
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
