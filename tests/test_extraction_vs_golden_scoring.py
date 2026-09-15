"""Severity-tiered extraction-vs-golden scoring tests (PLAN.md, DECISIONS.md
"golden-as-ground-truth pivot"). No live API calls -- _score_items is pure,
and _check_matched_pairs is monkeypatched where its call-batching
behavior matters.
"""

from __future__ import annotations

from evalkit.reference.compare import FLAWED_STATUSES, _score_items, _check_matched_pairs, align_events


def _item(status, severity, **extra):
    return {"status": status, "severity": severity, **extra}


def test_clean_match_scores_one_and_no_fabrication():
    items = [_item("matched_agree", "major") for _ in range(5)]
    result = _score_items(items)
    assert result["composite"] == 1.0
    assert result["has_confirmed_fabrication"] is False
    assert result["counts"] == {"matched_agree": 5}


def test_missing_fact_is_penalized_as_major():
    items = [_item("matched_agree", "major") for _ in range(4)] + [_item("missing", "major")]
    result = _score_items(items)
    # 1 flawed (weight 2) out of 5 total (weight 10) -> composite 0.8
    assert result["composite"] == 0.8


def test_contradicted_fact_is_penalized_more_than_a_missing_one():
    missing_only = _score_items([_item("matched_agree", "major")] * 4 + [_item("missing", "major")])
    contradicted_only = _score_items([_item("matched_agree", "major")] * 4 + [_item("matched_contradicted", "critical")])
    assert contradicted_only["composite"] < missing_only["composite"], (
        "a matched-but-wrong fact must hurt the score more than a missed fact -- "
        "the exact ordering the user asked for"
    )


def test_extra_grounded_fact_is_penalized_less_than_missing_or_contradicted():
    base = [_item("matched_agree", "major")] * 4
    extra_grounded = _score_items(base + [_item("extra_grounded", "minor")])
    missing = _score_items(base + [_item("missing", "major")])
    contradicted = _score_items(base + [_item("matched_contradicted", "critical")])
    assert extra_grounded["composite"] > missing["composite"] > contradicted["composite"], (
        "ordering requested: extra-but-correct < missing < wrong, in badness"
    )


def test_extra_ungrounded_fact_triggers_fabrication_flag():
    items = [_item("matched_agree", "major")] * 5 + [_item("extra_ungrounded", "critical")]
    result = _score_items(items)
    assert result["has_confirmed_fabrication"] is True


def test_unaudited_extra_is_reported_but_not_scored():
    """An extra candidate event we simply never checked (outside the
    risk-based audit's coverage) must not be silently penalized -- 'never
    guess' applies to scoring omissions too, not just factual claims."""
    items = [_item("matched_agree", "major")] * 3 + [_item("extra_unaudited", None)]
    result = _score_items(items)
    assert result["composite"] == 1.0, "an unaudited extra must not affect the composite either way"
    assert result["counts"]["extra_unaudited"] == 1, "but it must still be visible in the counts"


def test_flawed_statuses_set_matches_what_score_items_actually_penalizes():
    assert FLAWED_STATUSES == {"missing", "matched_contradicted", "extra_ungrounded"}


def test_check_matched_pairs_skips_the_call_entirely_when_nothing_is_ambiguous():
    """No ambiguous pairs -> zero calls, zero cost -- the budget-conscious
    design point explicitly: a confident match must never cost anything."""
    result = _check_matched_pairs(tracker=None, case_id="case-x", pairs=[])
    assert result == {}


def test_check_matched_pairs_parses_real_call_json_shape(monkeypatch):
    """Monkeypatch call_json (no live call) to verify the pair_id -> relation
    mapping is built correctly from a realistically-shaped judge response."""
    import evalkit.reference.compare as compare_module

    def fake_call_json(tracker, category, *, prompt, system, max_tokens):
        assert category == "extraction_agreement_check"
        return {"pairs": [
            {"pair_id": "3", "relation": "same_event_contradicts", "reason": "wrong provider"},
            {"pair_id": "7", "relation": "same_event_agrees", "reason": "same fact, different wording"},
        ]}

    monkeypatch.setattr(compare_module, "call_json", fake_call_json)
    result = _check_matched_pairs(
        tracker=None, case_id="case-x",
        pairs=[("3", "ref detail", "cand detail"), ("7", "ref detail 2", "cand detail 2")],
    )
    assert result == {"3": "same_event_contradicts", "7": "same_event_agrees"}


def test_score_extraction_against_golden_reclassifies_different_events_instead_of_contradicting():
    """Regression on a real false-positive found in production: a low
    text-overlap match between two genuinely UNRELATED events (e.g. an
    Acetaminophen entry weakly aligned to an unrelated IV-antibiotics-order
    entry just because nothing better existed within the date/type window)
    must NOT be scored as a critical fabrication. The judge correctly says
    "different_events" for this case; scoring must turn that into a missed
    reference fact + a separately-tiered extra, never matched_contradicted."""
    import evalkit.reference.compare as compare_module
    from evalkit.reference.audit import AuditReport

    def fake_check(tracker, case_id, pairs):
        return {pid: "different_events" for pid, _, _ in pairs}

    compare_module._check_matched_pairs = fake_check

    class FakeCase:
        case_id = "case-x"

    reference_events = [{"date": "2023-09-06", "type": "medication", "detail": "Acetaminophen for pain"}]
    candidate_events = [{"date": "2023-09-04", "type": "medication", "detail": "IV antibiotics ordered"}]
    audit = AuditReport(case_id="case-x", reference_path="")
    audit.source_support_by_index[0] = "yes"

    result = compare_module.score_extraction_against_golden(
        case=FakeCase(), candidate_events=candidate_events, reference_events=reference_events,
        ref_to_cand={0: 0}, unmatched_cand=set(), ref_scores={0: 0.15},
        candidate_audit=audit, tracker=None,
    )
    statuses = {it["status"] for it in result["items"]}
    assert "matched_contradicted" not in statuses
    assert statuses == {"missing", "extra_grounded"}


def test_align_events_matches_an_undated_reference_event_on_strong_content_overlap():
    """Regression: found in real Vance output -- golden's two most material
    facts (the Foster/Turner pre-existing-condition findings) are BOTH
    undated in golden. The plain date-tolerance check could never match an
    undated reference event to anything, guaranteeing "missing" by
    construction regardless of content -- even though the same real facts,
    correctly dated, existed in our candidate timeline all along."""
    reference_events = [{"date": None, "type": "diagnosis",
                          "detail": "Pre-existing 4mm posterior disc bulge at C5-C6 documented prior to the incident"}]
    candidate_events = [{"date": "2023-12-01", "type": "diagnosis",
                          "detail": "Cervical spine C5-C6 progression of disc bulge from 4mm to 6mm, pre-existing"}]
    ref_to_cand, matched_cand, unmatched_cand, ref_scores = align_events(candidate_events, reference_events)
    assert ref_to_cand == {0: 0}, "an undated reference event with strong content overlap must still match"


def test_align_events_rejects_undated_match_with_weak_content_overlap():
    """The relaxation must not become a free pass -- an undated reference
    event with only weak, generic overlap should not be force-matched."""
    reference_events = [{"date": None, "type": "diagnosis", "detail": "Left knee contusion noted"}]
    candidate_events = [{"date": "2023-12-01", "type": "diagnosis", "detail": "Right elbow fracture noted, unrelated"}]
    ref_to_cand, *_ = align_events(candidate_events, reference_events)
    assert ref_to_cand == {}, "weak overlap on an undated pair must not be treated as a match"


def test_align_events_matches_across_types_on_strong_content_overlap():
    """Regression: found in real Vance output -- the same real ORIF-consult
    fact is typed 'encounter' in golden and 'procedure' in our own
    extraction (a legitimate classification difference for the same real
    event, not a different event). A strict type-equality requirement
    blocked this from ever matching."""
    reference_events = [{"date": "2023-09-04", "type": "encounter",
                          "detail": "Immediate consultation with orthopedic surgery for emergency open reduction internal fixation Turner"}]
    candidate_events = [{"date": "2023-09-04", "type": "procedure",
                          "detail": "Left humerus open reduction internal fixation ORIF ordered Turner"}]
    ref_to_cand, *_ = align_events(candidate_events, reference_events)
    assert ref_to_cand == {0: 0}, "a real type-classification difference on the same fact must still allow a match"


def test_tier_extra_treats_a_flagged_issue_as_ungrounded_even_with_partial_support():
    """Regression: found in real Vance output -- the audit correctly flagged
    a real misattribution as source_supports='partial' + issue=
    'wrong_attribution' (confidence 0.85, matching a manually-verified real
    fabrication). The old tiering only checked support in ('yes','partial')
    and missed the flagged issue entirely, silently bucketing a confirmed
    problem as 'extra_grounded' / minor."""
    import evalkit.reference.compare as compare_module
    from evalkit.reference.audit import AuditReport

    audit = AuditReport(case_id="case-x", reference_path="")
    audit.source_support_by_index[5] = "partial"
    audit.issue_by_index[5] = "wrong_attribution"

    class FakeCase:
        case_id = "case-x"

    candidate_events = [{}] * 5 + [{"date": "2022-09-15", "type": "imaging", "detail": "X-ray"}]
    result = compare_module.score_extraction_against_golden(
        case=FakeCase(), candidate_events=candidate_events, reference_events=[],
        ref_to_cand={}, unmatched_cand={5}, ref_scores={},
        candidate_audit=audit, tracker=None,
    )
    item = result["items"][0]
    assert item["status"] == "extra_ungrounded"
    assert item["severity"] == "critical"


def test_align_events_combined_undated_and_cross_type_uses_the_lower_threshold():
    """Regression: found in real Vance output -- golden's OTHER undated
    Foster/Turner fact is undated AND type-mismatched at once (diagnosis
    vs imaging) against its real, manually-verified match. A first version
    of this fix required clearing BOTH relaxation thresholds (an AND),
    which wrongly excluded a real match that cleared the undated bar
    (0.2) but not the stricter cross-type bar (0.3) on its own. Each
    relaxation must be an independent, sufficient justification -- the
    lower of the two applicable thresholds is what should apply."""
    reference_events = [{"date": None, "type": "diagnosis",
                          "detail": "C5-C6 disc narrowing and bulge of unclear onset possibly preexisting condition"}]
    candidate_events = [{"date": "2023-09-04", "type": "imaging",
                          "detail": "Cervical spine C5-C6 disc narrowing 6mm disc bulge mild retrolisthesis onset date inconclusive"}]
    ref_to_cand, *_ = align_events(candidate_events, reference_events)
    assert ref_to_cand == {0: 0}


def test_align_events_rejects_cross_type_match_with_weak_content_overlap():
    """The cross-type relaxation must not become a free pass either -- two
    different-typed, topically-unrelated events sharing only generic words
    should not be force-matched."""
    reference_events = [{"date": "2023-09-04", "type": "encounter", "detail": "Routine vital signs check"}]
    candidate_events = [{"date": "2023-09-04", "type": "procedure", "detail": "Left arm splinting applied"}]
    ref_to_cand, *_ = align_events(candidate_events, reference_events)
    assert ref_to_cand == {}, "weak cross-type overlap must not be treated as a match"
