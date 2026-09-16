"""Deterministic extraction-pipeline tests (PLAN.md S15). No live API calls --
candidate dicts are constructed directly, the way extract_candidates() would
return them after an LLM call, to exercise normalize -> cluster -> conflict
-> canonicalize -> salience -> project end to end.
"""

from __future__ import annotations

from evalkit.extraction.canonicalize import CanonicalEvent, canonicalize_clusters
from evalkit.extraction.cluster import cluster_candidates
from evalkit.extraction.conflict import detect_conflicts
from evalkit.extraction.hitl import build_hitl_queue
from evalkit.extraction.normalize import normalize_candidates
from evalkit.extraction.project import _compose_detail, project_events
from evalkit.extraction.salience import select_material_timeline_events


def _candidate(**overrides):
    base = {
        "source_doc_id": "doc", "source_page": 1, "evidence_text": "evidence",
        "raw_date": "01/01/2024", "normalized_date": "2024-01-01",
        "date_basis": "explicit_event_date", "date_confidence": 0.9,
        "event_type_candidate": "encounter", "status": "performed",
        "attribution": {"asserted_by": "clinician_observed", "provider": "Dr. X", "certainty": "confirmed"},
        "temporal_relation_to_incident": "index-incident", "materiality_hint": "relevant",
        "extraction_confidence": 0.9, "clinical_facts": {}, "raw_summary": "summary",
    }
    base.update(overrides)
    return base


def _run_pipeline(raw_candidates: list[dict]):
    candidates = normalize_candidates(raw_candidates)
    clusters = cluster_candidates(candidates, id_prefix="test")
    conflicts = detect_conflicts(clusters, candidates)
    hitl_queue = build_hitl_queue(clusters, candidates, conflicts)
    canonical = canonicalize_clusters(clusters, candidates, conflicts)
    material = select_material_timeline_events(canonical)
    events, problems = project_events(material)
    return candidates, clusters, conflicts, hitl_queue, canonical, events, problems


def test_billing_vs_operative_date_trap_resolves_to_authoritative_source():
    """The billing form's date must lose to the operative report's explicit
    date, and the final `source` must cite the evidence that actually backs
    the resolved date/provider -- not just the first-seen mention."""
    raw = [
        _candidate(
            source_doc_id="08_billing", source_page=1,
            evidence_text="PRINCIPAL PROCEDURE DATE 09/04/2023 ORIF",
            normalized_date="2023-09-04", date_basis="billing_service_date", date_confidence=0.7,
            event_type_candidate="procedure",
            attribution={"asserted_by": "billing_system", "provider": "Dr. Foster", "certainty": "confirmed"},
            materiality_hint="high", extraction_confidence=0.7,
            clinical_facts={"procedure": "ORIF left humerus and radius", "body_site": "humerus", "laterality": "left"},
        ),
        _candidate(
            source_doc_id="02_hospitalization", source_page=4,
            evidence_text="Date of Surgery: 2023-09-07, ORIF humerus and radius",
            normalized_date="2023-09-07", date_basis="explicit_event_date", date_confidence=0.95,
            event_type_candidate="procedure",
            attribution={"asserted_by": "clinician_observed", "provider": "Dr. Myrtle Turner", "certainty": "confirmed"},
            materiality_hint="high", extraction_confidence=0.95,
            clinical_facts={"procedure": "ORIF left humerus and radius", "body_site": "humerus", "laterality": "left"},
        ),
    ]
    _, clusters, conflicts, _, _, events, problems = _run_pipeline(raw)

    assert len(clusters) == 1, "the two ORIF mentions should cluster into one event"
    date_conflict = next(c for c in conflicts if c.field == "normalized_date")
    assert date_conflict.suggested_resolution == "2023-09-07"
    assert date_conflict.needs_review is False

    assert problems == []
    assert len(events) == 1
    assert events[0]["date"] == "2023-09-07"
    assert "Turner" in events[0]["detail"]
    assert events[0]["source"] == "02_hospitalization p4", (
        "source must cite the evidence backing the resolved value, not the losing billing-form mention"
    )


def test_distinct_repetitive_events_stay_separate_not_merged():
    """Two real, genuinely distinct routine visits close in date and sharing
    templated boilerplate text must NOT be merged into one cluster/event --
    this regressed once already (near-date clustering pass was too broad for
    routine/therapy types)."""
    raw = [
        _candidate(
            source_doc_id="05_pt", source_page=2, evidence_text="Visit 1 therapeutic exercise",
            normalized_date="2023-09-18", event_type_candidate="therapy",
            materiality_hint="routine", clinical_facts={"concept": "PT session"},
        ),
        _candidate(
            source_doc_id="05_pt", source_page=3, evidence_text="Visit 2 therapeutic exercise",
            normalized_date="2023-09-20", event_type_candidate="therapy",
            materiality_hint="routine", clinical_facts={"concept": "PT session"},
        ),
    ]
    _, clusters, _, _, _, events, problems = _run_pipeline(raw)

    assert len(clusters) == 2, f"expected 2 separate clusters, got {len(clusters)}"
    assert problems == []
    dates = sorted(e["date"] for e in events)
    assert dates == ["2023-09-18", "2023-09-20"]


def test_distinct_same_day_medications_are_not_merged_by_shared_boilerplate():
    """Regression: found in the real case-davis extraction run -- four
    genuinely distinct medications given the same day (Hydromorphone PCA,
    Gabapentin, Cefazolin, Oxycodone) shared enough templated
    administration-note wording ("mg PO", dosing/route language, repeated
    dates) to clear Pass 1's exact-date-blocking Jaccard bar, even though
    each candidate carried a clean, populated, mutually-exclusive
    clinical_facts.medication name that clustering wasn't checking. A
    populated name field with zero shared words must block the merge
    regardless of surrounding text similarity (DECISIONS.md)."""
    raw = [
        _candidate(
            source_doc_id="02_inpatient", source_page=3, evidence_text="Hydromorphone (Dilaudid) PCA administration",
            normalized_date="2024-01-08", event_type_candidate="medication",
            clinical_facts={"medication": "Hydromorphone (Dilaudid) PCA", "concept": "pain management medication administration"},
        ),
        _candidate(
            source_doc_id="02_inpatient", source_page=3, evidence_text="Gabapentin 300mg PO administration",
            normalized_date="2024-01-08", event_type_candidate="medication",
            clinical_facts={"medication": "Gabapentin", "concept": "neuropathic pain medication administration"},
        ),
        _candidate(
            source_doc_id="02_inpatient", source_page=3, evidence_text="Ancef (Cefazolin) 1g IV administration",
            normalized_date="2024-01-08", event_type_candidate="medication",
            clinical_facts={"medication": "Cefazolin (Ancef)", "concept": "prophylactic antibiotic administration"},
        ),
    ]
    candidates, clusters, conflicts, _, _, events, problems = _run_pipeline(raw)

    assert len(clusters) == 3, f"expected 3 separate medication events, got {len(clusters)}"
    assert not any(c.field == "medication" for c in conflicts), "distinct medication names must never register as a conflict"
    assert problems == []
    assert len(events) == 3


def test_same_medication_reworded_across_sources_still_merges():
    """The distinct-named-facts guard must not become a blanket ban on
    merging -- two mentions of the SAME medication (near-identical name,
    real word overlap) on the same date should still cluster together."""
    raw = [
        _candidate(
            source_doc_id="a", source_page=1, evidence_text="Cefazolin 1g IV given",
            normalized_date="2024-01-08", event_type_candidate="medication",
            clinical_facts={"medication": "Cefazolin 1g IV"},
        ),
        _candidate(
            source_doc_id="b", source_page=1, evidence_text="Cefazolin (Ancef) 1g IV administered per MAR",
            normalized_date="2024-01-08", event_type_candidate="medication",
            clinical_facts={"medication": "Cefazolin (Ancef) 1g IV"},
        ),
    ]
    _, clusters, _, _, _, _, _ = _run_pipeline(raw)
    assert len(clusters) == 1, "same medication restated across two sources should still merge into one event"


def test_clearly_distinct_blocks_on_any_disagreeing_field_regardless_of_order():
    """Characterizes the current, deliberately-kept-simple behavior after
    two different "smarter" replacements were each tried and reverted this
    session (full account in FINDINGS.md/DECISIONS.md, both found unsafe
    via real-data testing, not just a hypothetical concern):

    1. "Decide on the single most-specific field both candidates populate,
       stop there" -- looked like it would fix the Harrison/X-ray
       case-vance fabrication below, but silently dropped a
       materiality="high" billing event (Anesthesia CPT 01402) from
       case-vance's real final timeline, because a shared boilerplate
       token ("CPT") made two DIFFERENT billed procedures' `procedure`
       fields register as "agreeing" and the genuinely-disagreeing
       `diagnosis_or_finding`/`concept` fields were never even checked.
    2. "Field agreement forces a merge" -- collapsed case-vance's final
       timeline from 202 to 137 events for the same underlying reason.

    So `facts_clearly_distinct()` stays a simple existence check: does ANY
    populated field pair disagree, checked in full regardless of order.
    This correctly blocks the CPT-boilerplate case (a real regression
    caught in review, reproduced here) and, as a KNOWN, DISCLOSED, still-
    open limitation, also still blocks the Harrison/X-ray merge that a
    smarter check could in principle allow (not asserted as desired
    behavior -- see FINDINGS.md for why a real fix needs boilerplate-token
    filtering, not just field reordering)."""
    from evalkit.extraction.cluster import facts_clearly_distinct

    # Regression catch: two DIFFERENT billed procedures on the same visit must
    # stay distinct even though their procedure fields share the boilerplate
    # token "CPT" -- the exact real-data shape that broke the reverted fix.
    or_services = {"concept": "surgical procedure", "procedure": "Operating Room Services, CPT 27535"}
    anesthesia = {"concept": "anesthesia", "procedure": "Anesthesia, CPT 01402"}
    assert facts_clearly_distinct(or_services, anesthesia), (
        "two different billed procedures sharing only the boilerplate token 'CPT' "
        "must still be flagged clearly distinct, not silently merged"
    )

    # Known, disclosed, still-open limitation (not desired behavior, just the
    # current reality): concept disagreeing still blocks this merge even
    # though procedure agrees -- see the Harrison/X-ray fabrication in
    # FINDINGS.md. This assertion exists so a future attempt to fix it
    # changes this test deliberately, not by silent side effect.
    finch = {"concept": "imaging study", "procedure": "X-ray cervical spine, three-view series"}
    harrison = {"concept": "X-ray cervical spine (prior)", "procedure": "X-ray"}
    assert facts_clearly_distinct(finch, harrison), (
        "documents the known-open Harrison/X-ray limitation -- concept disagreement still "
        "blocks this merge under the current, deliberately-simple, safe implementation"
    )


def test_salience_compression_does_not_merge_distinct_routine_medications():
    """Regression: found in the real case-davis extraction run (after the
    prompt/clustering fixes) -- 36 routine medication events shared no
    attributed provider (attribution.provider: None), so salience.py's
    (type, provider) grouping put every distinct drug into ONE compression
    bucket and collapsed the whole set to essentially first+last,
    discarding real, distinct medications (Hydromorphone, Gabapentin,
    Cefazolin, Oxycodone...) as if they were repeat mentions of the same
    thing. Each drug given >=4 times across a real course should compress
    on its OWN course (first+last+flagged of THAT drug), not get folded
    into an unrelated drug's course."""
    from evalkit.extraction.canonicalize import CanonicalEvent

    def _med_event(date: str, medication: str) -> CanonicalEvent:
        return CanonicalEvent(
            canonical_id=f"{medication}-{date}", member_candidate_ids=[0],
            date=date, date_basis="explicit_event_date", type="medication", status="performed",
            clinical_facts={"concept": None, "body_site": None, "laterality": None,
                             "diagnosis_or_finding": None, "procedure": None,
                             "medication": medication, "dose": None},
            attribution={"provider": None, "asserted_by": "clinician_observed", "certainty": "confirmed"},
            materiality="routine", confidence=0.8, conflict_group_id=None, needs_review=False,
            evidence=[{"doc": "d", "page": 1, "snippet": f"{medication} administered"}],
        )

    events = []
    for i, date in enumerate(["2024-01-08", "2024-01-09", "2024-01-10", "2024-01-11", "2024-01-12"]):
        events.append(_med_event(date, "Hydromorphone (Dilaudid)"))
        events.append(_med_event(date, "Gabapentin"))
        if i < 4:
            events.append(_med_event(date, "Cefazolin (Ancef)"))

    kept = select_material_timeline_events(events)
    kept_meds = {(e.date, (e.clinical_facts or {}).get("medication")) for e in kept}

    assert any(m == "Hydromorphone (Dilaudid)" for _, m in kept_meds), "Hydromorphone course must survive compression"
    assert any(m == "Gabapentin" for _, m in kept_meds), "Gabapentin course must survive compression"
    assert any(m == "Cefazolin (Ancef)" for _, m in kept_meds), "Cefazolin course must survive compression"
    # each drug's course should independently keep its own first+last (at least 2 events per drug)
    from collections import Counter
    counts = Counter(m for _, m in kept_meds)
    assert counts["Hydromorphone (Dilaudid)"] >= 2
    assert counts["Gabapentin"] >= 2
    assert counts["Cefazolin (Ancef)"] >= 2


def test_salience_compression_ignores_a_compound_mention_as_a_bridge():
    """Regression on the regression: the FIRST fix for the bug above used a
    single fuzzy pairwise "shares no word on any field" veto with plain
    union-find. That's not transitive, and a real compound "transitioned
    to Oxycodone and Gabapentin" candidate -- sharing one word with every
    pure-Oxycodone event and a different word with every pure-Gabapentin
    event -- chained the two drugs (and, in the real run, several more)
    into one 26-member group despite any direct pair being clearly
    distinct. This must not happen: a compound mention should end up in
    its own small group (or merge only with identical compound mentions),
    never bridge two single-drug groups together."""
    from evalkit.extraction.canonicalize import CanonicalEvent

    def _med_event(date: str, medication: str) -> CanonicalEvent:
        return CanonicalEvent(
            canonical_id=f"{medication}-{date}", member_candidate_ids=[0],
            date=date, date_basis="explicit_event_date", type="medication", status="performed",
            clinical_facts={"concept": None, "body_site": None, "laterality": None,
                             "diagnosis_or_finding": None, "procedure": None,
                             "medication": medication, "dose": None},
            attribution={"provider": None, "asserted_by": "clinician_observed", "certainty": "confirmed"},
            materiality="routine", confidence=0.8, conflict_group_id=None, needs_review=False,
            evidence=[{"doc": "d", "page": 1, "snippet": f"{medication} administered"}],
        )

    events = []
    for date in ["2024-01-08", "2024-01-09", "2024-01-10", "2024-01-11"]:
        events.append(_med_event(date, "Oxycodone"))
        events.append(_med_event(date, "Gabapentin"))
    events.append(_med_event("2024-01-15", "Oxycodone, Gabapentin"))  # the compound bridge risk

    from evalkit.extraction.salience import _sub_cluster_by_name
    groups = _sub_cluster_by_name(events)
    for group in groups:
        meds = {(e.clinical_facts or {}).get("medication") for e in group}
        assert not ({"Oxycodone", "Gabapentin"} <= meds), (
            f"a compound mention must never bridge two distinct single-drug groups together: {meds}"
        )


def test_high_materiality_unresolved_conflict_never_becomes_confident_fact():
    """An unresolved conflict on a field must not silently pick a value --
    PLAN.md S6's hard rule."""
    raw = [
        _candidate(
            source_doc_id="a", source_page=1, evidence_text="diagnosis A",
            normalized_date="2024-02-01", date_basis="relative_to_note_date", date_confidence=0.5,
            event_type_candidate="diagnosis",
            attribution={"asserted_by": "patient_reported", "provider": None, "certainty": "uncertain"},
            materiality_hint="high", extraction_confidence=0.6,
            clinical_facts={"diagnosis_or_finding": "cervical strain onset"},
        ),
        _candidate(
            source_doc_id="b", source_page=1, evidence_text="diagnosis A, different date",
            normalized_date="2024-02-05", date_basis="relative_to_note_date", date_confidence=0.5,
            event_type_candidate="diagnosis",
            attribution={"asserted_by": "patient_reported", "provider": None, "certainty": "uncertain"},
            materiality_hint="high", extraction_confidence=0.6,
            clinical_facts={"diagnosis_or_finding": "cervical strain onset"},
        ),
    ]
    _, _, conflicts, hitl_queue, canonical, events, problems = _run_pipeline(raw)

    date_conflict = next(c for c in conflicts if c.field == "normalized_date")
    assert date_conflict.needs_review is True, "two equally-weak-basis dates should not resolve confidently"
    assert any(c.needs_review for c in canonical), "canonical event should carry the unresolved flag"
    # high materiality + unresolved -> still projected, but with date left null, not guessed
    assert problems == []
    if events:
        assert events[0]["date"] is None
    assert any("SOURCE_CONFLICT" in it.reasons for it in hitl_queue)


def test_detail_composer_does_not_duplicate_laterality_already_in_body_site():
    """Regression: found in the real case-vance extraction run -- when
    body_site already embeds the laterality ("left humerus/radius") and
    laterality is separately "left", the composer must not prepend "left"
    again and produce "Left left humerus/radius..."."""
    event = CanonicalEvent(
        canonical_id="x", member_candidate_ids=[0],
        date="2024-01-08", date_basis="note_signing_date", type="diagnosis", status="reported_history",
        clinical_facts={
            "concept": "referring diagnosis", "body_site": "left humerus/radius; cervical spine",
            "laterality": "left",
            "diagnosis_or_finding": "status post ORIF left humerus/radius with muscle wasting",
            "procedure": "ORIF (prior)", "medication": None, "dose": None,
        },
        attribution={"provider": None, "asserted_by": "clinician_observed", "certainty": "confirmed"},
        materiality="high", confidence=0.8, conflict_group_id=None, needs_review=False,
        evidence=[{"doc": "06_pt_emory_sports", "page": 1,
                    "snippet": "Post-surgical left humerus/radius ORIF with persistent muscle wasting, chronic cervical disc bulge"}],
    )
    detail = _compose_detail(event)
    assert detail is not None
    assert "left left" not in detail.lower(), detail


def test_detail_composer_rejects_ungrounded_interpretation_of_a_billing_code():
    """Regression: found in the real case-vance run -- extraction populated
    clinical_facts.procedure with a real-world CPT-code lookup ("open
    treatment of tibial plateau fracture" / body_site "knee") for a billing
    line that only ever said "Operating Room Services, 27535" -- correct in
    general, wrong for this patient (arm fractures, not a knee), and not
    actually stated in the source. The composer must not use an interpreted
    clinical_facts value that shares no real (non-numeric) word with the
    cited evidence -- a shared billing code alone doesn't count as grounding
    a description of what that code means."""
    event = CanonicalEvent(
        canonical_id="x", member_candidate_ids=[0],
        date="2023-09-04", date_basis="billing_service_date", type="procedure", status="performed",
        clinical_facts={
            "concept": "surgery", "body_site": "knee", "laterality": None,
            "procedure": "CPT 27535 (open treatment of tibial plateau fracture)",
            "diagnosis_or_finding": "S42.302A", "medication": None, "dose": None,
        },
        attribution={"provider": "Dr. Elizabeth Foster, MD", "asserted_by": "billing_system", "certainty": "confirmed"},
        materiality="high", confidence=0.85, conflict_group_id=None, needs_review=False,
        evidence=[{"doc": "08_billing_and_claims", "page": 1,
                    "snippet": "Operating Room Services, 27535, 09/04/2023, 1 unit, $28,500.00"}],
    )
    detail = _compose_detail(event)
    assert detail is not None
    assert "knee" not in detail.lower(), detail
    assert "tibial" not in detail.lower(), detail
    assert "27535" in detail, "should fall back to the grounded raw snippet, not drop the content entirely"


def test_detail_composer_rejects_ungrounded_body_site_and_laterality():
    """Regression: found in the real case-davis run -- `body_site` and
    `laterality` were appended to the composed sentence with NO grounding
    check at all (unlike procedure/diagnosis_or_finding/concept, which are
    checked), even when the model's own hedge said the value wasn't
    clinically confirmed (e.g. body_site="peripheral nerve (per CPT code
    convention, not clinically confirmed in text)" for a CMS-1500 form that
    only ever showed the raw code "64784", never the words "peripheral" or
    "nerve"). This is exactly how a decoded-from-a-billing-code body_site
    value reached a committed final timeline (FINDINGS.md)."""
    event = CanonicalEvent(
        canonical_id="x", member_candidate_ids=[0],
        date="2024-11-12", date_basis="billing_service_date", type="procedure", status="performed",
        clinical_facts={
            "concept": "nerve-related procedure billed under CPT 64784",
            "body_site": "peripheral nerve (per CPT code convention, not clinically confirmed in text)",
            "laterality": None,
            "procedure": None, "diagnosis_or_finding": "M96.5", "medication": None, "dose": None,
        },
        attribution={"provider": "Dr. Marcus Vance, MD, FACS", "asserted_by": "billing_system", "certainty": "confirmed"},
        materiality="high", confidence=0.5, conflict_group_id=None, needs_review=False,
        evidence=[{"doc": "06_Comprehensive_Billing_and_Financial_Audit", "page": 5,
                    "snippet": "64784, 11/12/2024, DX A, physician Dr. Marcus Vance, diagnosis M96.5"}],
    )
    detail = _compose_detail(event)
    assert detail is not None
    assert "peripheral" not in detail.lower(), detail
    assert "nerve" not in detail.lower(), (
        "the ungrounded, hedged body_site decode ('peripheral nerve...') must never reach the "
        f"final composed sentence: {detail!r}"
    )
    assert "M96.5" in detail, "the genuinely grounded diagnosis code must still come through"


def test_detail_composer_keeps_a_correct_body_site_even_without_verbatim_evidence_repetition():
    """Regression, the other direction: a body_site value with no self-
    disclosed hedge must NOT be dropped just because the ONE cited evidence
    snippet happens not to restate it word-for-word (real case-davis
    example: a follow-up note's own snippet just says "amputation", but
    body_site="left arm" is still true and correctly carried over from
    context elsewhere in the record). A full word-overlap grounding
    requirement here was tried and reverted after real-data testing found
    it stripped many genuinely correct body_site values across the corpus
    (FINDINGS.md/DECISIONS.md) -- only a self-hedged-decode phrase should
    ever remove one."""
    event = CanonicalEvent(
        canonical_id="x", member_candidate_ids=[0],
        date="2024-01-08", date_basis="explicit_event_date", type="procedure", status="performed",
        clinical_facts={
            "concept": "amputation", "body_site": "left arm", "laterality": "left",
            "procedure": "amputation", "diagnosis_or_finding": None, "medication": None, "dose": None,
        },
        attribution={"provider": None, "asserted_by": "patient_reported", "certainty": "confirmed"},
        materiality="high", confidence=0.75, conflict_group_id=None, needs_review=False,
        evidence=[{"doc": "04_prosthetic_fitting", "page": 2,
                    "snippet": "What treatments have you already tried? Amputation Jan 2024"}],
    )
    detail = _compose_detail(event)
    assert detail is not None
    assert "arm" in detail.lower(), f"a true, un-hedged body_site must survive even without verbatim evidence repetition: {detail!r}"
