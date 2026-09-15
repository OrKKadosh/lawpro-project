"""Deterministic scoring tests (PLAN.md S15). No live API calls."""

from __future__ import annotations

from evalkit.scoring import score_coverage, score_faithfulness, score_stability, score_usefulness


def test_one_critical_claim_gates_regardless_of_many_correct_minor_claims():
    """The whole point of the gate: a critical fabrication must not disappear
    inside a large denominator of harmless correct claims (DECISIONS.md)."""
    claims = [{"status": "supported", "materiality": "minor"} for _ in range(20)]
    claims.append({"status": "contradicted", "materiality": "critical"})
    result = score_faithfulness(claims)
    assert result["ship_eligible"] is False
    assert len(result["gate_triggering_claims"]) == 1
    # composite should still be high-ish (20 correct minors vs 1 critical), but that's irrelevant to the gate
    assert result["composite"] > 0.5


def test_no_flawed_claims_is_fully_ship_eligible_with_composite_one():
    claims = [{"status": "supported", "materiality": "major"} for _ in range(5)]
    result = score_faithfulness(claims)
    assert result["ship_eligible"] is True
    assert result["composite"] == 1.0
    assert result["gate_triggering_claims"] == []


def test_overclaimed_critical_claim_gates_the_same_as_contradicted():
    """The Foster/Turner failure mode specifically: a hedged finding turned
    into unqualified certainty is "overclaimed", not "contradicted" -- must
    still gate."""
    claims = [{"status": "overclaimed", "materiality": "critical"}]
    result = score_faithfulness(claims)
    assert result["ship_eligible"] is False


def test_weighted_coverage_rate_respects_materiality_weight():
    material_facts = [
        {"fact_id": "a", "materiality_weight": 3},
        {"fact_id": "b", "materiality_weight": 1},
    ]
    # the weight-3 fact is missed, the weight-1 fact is fully covered
    fact_coverage = [{"fact_id": "a", "reflected": "no"}, {"fact_id": "b", "reflected": "yes"}]
    result = score_coverage(fact_coverage, material_facts)
    # achieved = 3*0 + 1*1 = 1; total = 4 -> rate = 0.25
    assert result["weighted_coverage_rate"] == 0.25
    assert result["facts_missing"] == ["a"]


def test_partial_coverage_counts_as_half():
    material_facts = [{"fact_id": "a", "materiality_weight": 2}]
    fact_coverage = [{"fact_id": "a", "reflected": "partial"}]
    result = score_coverage(fact_coverage, material_facts)
    assert result["weighted_coverage_rate"] == 0.5


def test_usefulness_mean_averages_all_dimensions():
    usefulness = {"chronological_clarity": 5, "concision": 3, "organization": 4}
    result = score_usefulness(usefulness)
    assert result["mean"] == 4.0


def test_stability_overlap_rate_excludes_run_only_claims_from_denominator():
    claim_pairs = [
        {"relation": "agree", "materiality": "minor"},
        {"relation": "agree", "materiality": "major"},
        {"relation": "disagree", "materiality": "critical"},
        {"relation": "run1_only", "materiality": "minor"},
        {"relation": "run2_only", "materiality": "minor"},
    ]
    result = score_stability(claim_pairs)
    # overlap rate = agree / (agree+disagree) = 2/3, run-only claims don't affect it
    # (score_stability rounds to 3dp by design, so compare with a tolerance that respects that)
    assert abs(result["material_fact_overlap_rate"] - (2 / 3)) < 1e-3
    assert result["critical_cross_run_conflict_count"] == 1
    assert result["run1_only"] == 1
    assert result["run2_only"] == 1
