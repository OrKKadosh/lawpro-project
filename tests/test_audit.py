"""Regression tests for source-audit completion accounting (FINDINGS.md): an
event whose `source` string couldn't be parsed used to be silently dropped
from the audit with zero record anywhere, which could make audit completion
look far higher than it really was, and a flat source_grounded_precision
number was reported with no indication of how incomplete the audited sample
actually was. No live API calls -- call_json is monkeypatched.
"""

from __future__ import annotations

import evalkit.reference.audit as audit


class _FakeCase:
    case_id = "case-x"

    def ocr_pages(self, doc_id):
        return ["page 1 text", "page 2 text", "page 3 text"]

    def ocr_text(self, doc_id):
        return "some OCR text"


def _event(index, date, type_, detail, source):
    return {"index": index, "date": date, "type": type_, "detail": detail, "source": source, "materiality": "high"}


def test_unparseable_source_is_recorded_not_silently_dropped(monkeypatch):
    events = [
        {"date": "2024-01-01", "type": "procedure", "detail": "a real procedure", "source": "doc1 p1"},
        {"date": "2024-01-02", "type": "procedure", "detail": "an event with a garbage source", "source": "completely unparseable garbage"},
    ]

    def fake_call_json(tracker, category, *, prompt, system, max_tokens):
        return {"event_audits": [{"index": 0, "source_supports": "yes", "issue": "none", "explanation": "ok", "confidence": 0.9}], "notable_omissions": []}
    monkeypatch.setattr(audit, "call_json", fake_call_json)

    report = audit.audit_events(_FakeCase(), events, tracker=None)
    d = report.to_dict()

    assert len(report.unparseable_sources) == 1
    assert report.unparseable_sources[0]["raw_source"] == "completely unparseable garbage"
    assert d["coverage"]["unparseable_sources_count"] == 1
    assert d["coverage"]["events_selected_for_audit"] == 2
    assert d["coverage"]["events_with_a_verdict"] == 1, "only the one parseable event should get a verdict"


def test_audit_completion_rate_distinguishes_selected_from_completed(monkeypatch):
    """The exact scenario from the reviewer's spec: selected=2, one document's
    call fails (a judge_call_failures entry), so completed=1 -- completion
    rate must be 0.5, and precision must be computed only over the 1
    completed verdict, never silently presented as if both were audited."""
    events = [
        {"date": "2024-01-01", "type": "procedure", "detail": "event A", "source": "doc1 p1"},
        {"date": "2024-01-02", "type": "procedure", "detail": "event B", "source": "doc2 p1"},
    ]

    def fake_call_json(tracker, category, *, prompt, system, max_tokens):
        if "doc2" in prompt:
            raise RuntimeError("malformed judge response for doc2")
        return {"event_audits": [{"index": 0, "source_supports": "yes", "issue": "none", "explanation": "ok", "confidence": 0.9}], "notable_omissions": []}
    monkeypatch.setattr(audit, "call_json", fake_call_json)

    report = audit.audit_events(_FakeCase(), events, tracker=None)
    d = report.to_dict()

    assert d["coverage"]["events_selected_for_audit"] == 2
    assert d["coverage"]["events_with_a_verdict"] == 1
    assert d["coverage"]["audit_completion_rate"] == 0.5
    assert d["coverage"]["source_grounded_precision_among_completed"] == 1.0
    assert len(report.judge_call_failures) == 1


def test_defense_in_depth_parser_still_recovers_a_malformed_pp_source(monkeypatch):
    """The upstream fix (normalize.py) prevents NEW extractions from ever
    producing a "pp1"-style source, but an older already-committed candidate
    timeline (extracted before that fix) can still have one -- the parser
    must recover it via the p+ regex, not drop it."""
    events = [
        {"date": "2024-01-01", "type": "procedure", "detail": "event A", "source": "doc1 pp1"},
    ]

    def fake_call_json(tracker, category, *, prompt, system, max_tokens):
        return {"event_audits": [{"index": 0, "source_supports": "yes", "issue": "none", "explanation": "ok", "confidence": 0.9}], "notable_omissions": []}
    monkeypatch.setattr(audit, "call_json", fake_call_json)

    report = audit.audit_events(_FakeCase(), events, tracker=None)
    assert report.unparseable_sources == []
    assert report.to_dict()["coverage"]["events_with_a_verdict"] == 1


def test_parse_source_accepts_both_single_and_double_p():
    assert audit._parse_source("doc1 p8") == ("doc1", 8)
    assert audit._parse_source("doc1 pp8") == ("doc1", 8)
    assert audit._parse_source("completely unparseable") is None


# --- page-scoped audit (FINDINGS.md: the judge used to receive the WHOLE
# document, so it could never tell "supported on the cited page" apart from
# "exists somewhere else in the document" -- both passed as full support) ---

def test_windowed_ocr_text_only_includes_cited_pages_and_their_neighbors():
    pages = [f"page {i} text" for i in range(1, 11)]
    text = audit._windowed_ocr_text(pages, cited_pages=[5], window=1)
    assert "[p4]" in text and "[p5]" in text and "[p6]" in text
    assert "[p1]" not in text and "[p10]" not in text and "[p3]" not in text and "[p7]" not in text


def test_windowed_ocr_text_stays_within_bounds_at_document_edges():
    pages = ["page 1", "page 2", "page 3"]
    text = audit._windowed_ocr_text(pages, cited_pages=[1], window=1)
    assert "[p1]" in text and "[p2]" in text
    assert "[p0]" not in text  # no page 0 -- must not crash or fabricate an out-of-range page


def test_audit_does_not_grant_clean_support_when_fact_is_on_a_different_page_than_cited(monkeypatch):
    """Exact reviewer spec: a fact appears on page 3, the event cites page 1
    -- the audit must not return a clean, fully-supported verdict. Verified
    by checking the judge is shown ONLY the cited page's window (page 1,
    per PAGE_CONTEXT_WINDOW=1 that's pages 1-2), never page 3 where the
    fact actually lives -- so a judge acting in good faith on what it's
    given cannot claim full support for something it was never shown."""
    class FakeCase:
        case_id = "case-x"
        def ocr_pages(self, doc_id):
            return [
                "Page 1: patient intake, no procedure details here.",
                "Page 2: vitals and history.",
                "Page 3: ACTUAL PROCEDURE NOTE -- appendectomy performed here.",
            ]

    seen_prompts = []
    def fake_call_json(tracker, category, *, prompt, system, max_tokens):
        seen_prompts.append(prompt)
        return {"event_audits": [{"index": 0, "source_supports": "no", "issue": "wrong_attribution",
                                   "explanation": "not found on cited page 1", "confidence": 0.9}],
                "notable_omissions": []}
    monkeypatch.setattr(audit, "call_json", fake_call_json)

    events = [{"date": "2024-01-01", "type": "procedure", "detail": "appendectomy performed", "source": "doc1 p1"}]
    report = audit.audit_events(FakeCase(), events, tracker=None)

    assert "ACTUAL PROCEDURE NOTE" not in seen_prompts[0], "page 3's OCR text (where the fact actually lives) must not be shown to the judge at all"
    assert report.source_support_by_index[0] != "yes", "must not grant clean support for a fact never shown to the judge"
    assert report.issue_by_index[0] == "wrong_attribution"
