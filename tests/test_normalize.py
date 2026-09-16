"""Regression tests for source_page normalization (FINDINGS.md): raw
candidate extraction output sometimes gives source_page as a string like
"p1" rather than an int, which -- uncoerced -- produced "document pp1" in
the final projected timeline's `source` field (confirmed for real: 75/140
of case-davis's committed final events), which the source-audit parser then
silently failed to match and dropped with zero record."""

from __future__ import annotations

from evalkit.extraction.normalize import _normalize_page, normalize_candidate


def _raw(**overrides):
    base = {
        "source_doc_id": "doc1", "source_page": 1, "evidence_text": "x",
        "raw_date": "01/01/2024", "normalized_date": "2024-01-01",
        "date_basis": "explicit_event_date", "date_confidence": 0.9,
        "event_type_candidate": "encounter", "status": "performed",
        "attribution": {"asserted_by": "clinician_observed", "provider": "Dr. X", "certainty": "confirmed"},
        "temporal_relation_to_incident": "index-incident", "materiality_hint": "relevant",
        "extraction_confidence": 0.9, "clinical_facts": {},
    }
    base.update(overrides)
    return base


def test_normalize_page_accepts_int():
    assert _normalize_page(1) == 1
    assert _normalize_page(42) == 42


def test_normalize_page_accepts_numeric_string():
    assert _normalize_page("1") == 1
    assert _normalize_page("42") == 42


def test_normalize_page_accepts_p_prefixed_string():
    assert _normalize_page("p1") == 1
    assert _normalize_page("p42") == 42


def test_normalize_page_accepts_page_word_prefix():
    assert _normalize_page("page 1") == 1
    assert _normalize_page("Page 7") == 7


def test_normalize_page_rejects_malformed_values():
    assert _normalize_page("") is None
    assert _normalize_page(None) is None
    assert _normalize_page("no page number here") is None
    assert _normalize_page(True) is None  # bool is technically an int subclass -- must not silently pass as a page
    assert _normalize_page([1, 2]) is None


def test_normalize_candidate_coerces_source_page_to_int():
    for raw_value in (1, "1", "p1", "page 1"):
        result = normalize_candidate(_raw(source_page=raw_value))
        assert result["source_page"] == 1, f"raw source_page={raw_value!r} must normalize to int 1"
        assert isinstance(result["source_page"], int)


def test_normalize_candidate_never_produces_a_string_page():
    result = normalize_candidate(_raw(source_page="garbage"))
    assert result["source_page"] is None, "a malformed page must become None, never propagate as a string"
