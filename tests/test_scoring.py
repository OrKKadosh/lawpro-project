"""Deterministic scoring tests (PLAN.md S15). No live API calls."""

from __future__ import annotations

from evalkit.scoring import (
    build_summary_scorecard, is_omission_shaped_claim, is_untraceable_claim,
    score_coverage, score_faithfulness, score_stability, score_usefulness,
)


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


def test_stability_shared_topic_agreement_ignores_run_only_claims():
    """shared_topic_agreement_rate is explicitly SUPPOSED to ignore
    run1_only/run2_only -- it answers "when both runs discuss the same
    topic, do they agree?", nothing more. This is not the bug; conflating
    this number with overall stability (below) was."""
    claim_pairs = [
        {"relation": "agree", "materiality": "minor"},
        {"relation": "agree", "materiality": "major"},
        {"relation": "disagree", "materiality": "critical"},
        {"relation": "run1_only", "materiality": "minor"},
        {"relation": "run2_only", "materiality": "minor"},
    ]
    result = score_stability(claim_pairs)
    assert abs(result["shared_topic_agreement_rate"] - (2 / 3)) < 1e-3
    assert result["critical_cross_run_conflict_count"] == 1
    assert result["run1_only"] == 1
    assert result["run2_only"] == 1


def test_stability_case1_all_shared_and_agreeing_both_metrics_are_perfect():
    """Case 1 (reviewer spec): 3 shared agreeing topics, no unique topics --
    both metrics should read 1.0."""
    claim_pairs = [{"relation": "agree", "materiality": "major"} for _ in range(3)]
    result = score_stability(claim_pairs)
    assert result["shared_topic_agreement_rate"] == 1.0
    assert result["content_overlap_stability_rate"] == 1.0


def test_stability_case2_run_only_content_drags_down_overlap_not_agreement():
    """Case 2 (reviewer spec), and the exact real-world bug this fix closes:
    3 shared agreeing topics + 7 run1-only topics. shared_topic_agreement_rate
    may still read 1.0 (the 3 shared topics really do agree) but
    content_overlap_stability_rate MUST be substantially below 1.0, since 7
    of the 10 total topics never even appear in run2. The pre-fix single
    "material_fact_overlap_rate" would have reported this pair as a perfect
    1.0 -- exactly the misleadingly-high-stability failure mode reported
    for real in results/controlled_benchmark_case-vance.json (FINDINGS.md)."""
    claim_pairs = (
        [{"relation": "agree", "materiality": "major"} for _ in range(3)]
        + [{"relation": "run1_only", "materiality": "major"} for _ in range(7)]
    )
    result = score_stability(claim_pairs)
    assert result["shared_topic_agreement_rate"] == 1.0
    # 3 agree / 10 total topics = 0.3
    assert abs(result["content_overlap_stability_rate"] - 0.3) < 1e-3
    assert result["content_overlap_stability_rate"] < 0.5, (
        "one run dropping 7 of 10 material topics must not read as anywhere near stable"
    )


def test_stability_case3_shared_disagreement_lowers_both_metrics():
    """Case 3 (reviewer spec): a shared disagreement should be reflected in
    both metrics, not hidden by either."""
    claim_pairs = [
        {"relation": "agree", "materiality": "major"},
        {"relation": "disagree", "materiality": "critical"},
    ]
    result = score_stability(claim_pairs)
    assert result["shared_topic_agreement_rate"] == 0.5
    assert result["content_overlap_stability_rate"] == 0.5
    assert result["critical_cross_run_conflict_count"] == 1


# --- Faithfulness/coverage conflation fix (FINDINGS.md: a real, pervasive bug --
# omission-shaped "claims" like "No mention of X" were tagged status=unsupported
# and lowered faithfulness for content the summary never asserted) ---

MATERIAL_FACTS = [
    {"fact_id": "f1", "materiality_weight": 3, "description": "prior shoulder injury"},
]


def test_summary_omitting_a_material_fact_loses_coverage_not_faithfulness():
    """Test 1+2 (reviewer spec): an omitted material fact must reduce
    coverage, and must NOT lower faithfulness -- these are the two halves
    of the same requirement, checked together since they're the same
    scenario scored two different ways."""
    claims = [
        {"claim_id": "c1", "text": "Patient was discharged home in stable condition.",
         "status": "supported", "materiality": "minor", "summary_quote": "discharged home in stable condition"},
    ]
    fact_coverage = [{"fact_id": "f1", "reflected": "no"}]
    faithfulness = score_faithfulness(claims)
    coverage = score_coverage(fact_coverage, MATERIAL_FACTS)
    assert faithfulness["composite"] == 1.0, "an omission must never appear as a flawed claim"
    assert coverage["weighted_coverage_rate"] == 0.0, "the omitted fact must still reduce coverage"
    assert coverage["facts_missing"] == ["f1"]


def test_judge_inventing_an_omission_claim_is_excluded_from_faithfulness():
    """The actual bug, reproduced: a judge that (despite instructions) still
    emits an omission-shaped 'claim' with status=unsupported must not have
    it counted against faithfulness -- it gets excluded, not scored."""
    claims = [
        {"claim_id": "c1", "text": "No mention of prior 2022 shoulder injury history",
         "status": "unsupported", "materiality": "major", "reason": "summary omits this"},
    ]
    result = score_faithfulness(claims)
    assert result["claim_count"] == 0, "the omission-shaped claim must be excluded entirely, not scored"
    assert result["omission_shaped_claims_excluded"] == 1
    assert result["composite"] is None or result["composite"] == 1.0


def test_explicit_unsupported_fact_still_lowers_faithfulness():
    """Test 3 (reviewer spec): a summary that EXPLICITLY STATES an
    unsupported fact (not an omission -- an actual assertion) must still
    lower faithfulness. The fix must not become a blanket immunity for
    every unsupported-status claim."""
    claims = [
        {"claim_id": "c1", "text": "Patient underwent emergency surgery on the left knee.",
         "status": "unsupported", "materiality": "major", "summary_quote": "emergency surgery on the left knee"},
    ]
    result = score_faithfulness(claims)
    assert result["claim_count"] == 1, "a genuine fabricated assertion must not be excluded"
    assert result["omission_shaped_claims_excluded"] == 0
    assert result["composite"] < 1.0


def test_overclaim_present_in_summary_text_still_scored():
    """Test 4 (reviewer spec): a genuine overclaim (hedged timeline finding
    flattened into certainty), anchored by a real summary_quote, must still
    be scored as an overclaim -- not swept up by the omission filter just
    because it involves the judge describing a gap between what the
    timeline says and what the summary says."""
    claims = [
        {"claim_id": "c1", "text": "States the fracture as a settled fact rather than a possible finding.",
         "status": "overclaimed", "materiality": "critical", "summary_quote": "the fracture was present"},
    ]
    result = score_faithfulness(claims)
    assert result["claim_count"] == 1
    assert result["ship_eligible"] is False, "a critical overclaim must still gate"


def test_omission_cannot_double_penalize_via_both_coverage_and_faithfulness():
    """Test 5 (reviewer spec): the same omission must be penalized exactly
    once (via coverage), never twice. Build a full scorecard combining a
    real omission-shaped judge claim (which must be excluded from
    faithfulness) with the corresponding fact_coverage miss (which must
    still reduce coverage) -- faithfulness must come out perfect while
    coverage takes the hit, not both dinged for the same underlying gap."""
    claims = [
        {"claim_id": "c1", "text": "No mention of prior shoulder injury.",
         "status": "unsupported", "materiality": "major"},
    ]
    fact_coverage = [{"fact_id": "f1", "reflected": "no"}]
    scorecard = build_summary_scorecard(
        tool="A", run=1, cost_usd=0.1, claims=claims, fact_coverage=fact_coverage,
        usefulness={"concision": 4}, material_facts=MATERIAL_FACTS,
        summary_text="Patient was discharged home in stable condition.",
    )
    assert scorecard["faithfulness"]["composite"] in (None, 1.0), "no real claims left to penalize -- must not be flawed"
    assert scorecard["coverage"]["weighted_coverage_rate"] == 0.0


def test_is_omission_shaped_claim_detects_common_phrasings():
    assert is_omission_shaped_claim({"text": "No mention of prior injury"})
    assert is_omission_shaped_claim({"text": "Summary omits the discharge date"})
    assert is_omission_shaped_claim({"reason": "This finding is missing from summary"})
    assert not is_omission_shaped_claim({"text": "States the injury occurred on 2024-01-08", "summary_quote": "injury occurred on 2024-01-08"})
    assert not is_omission_shaped_claim({"text": "Patient was discharged home"})


def test_is_untraceable_claim_catches_a_hallucinated_quote():
    summary = "The patient was discharged home in stable condition."
    real = {"summary_quote": "discharged home in stable condition"}
    fake = {"summary_quote": "underwent emergency amputation surgery"}
    assert not is_untraceable_claim(real, summary)
    assert is_untraceable_claim(fake, summary)
    # No summary_text available (e.g. old code paths) -- never penalize, can't check.
    assert not is_untraceable_claim(fake, None)
