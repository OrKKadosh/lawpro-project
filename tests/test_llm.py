"""Regression tests for the truncated-JSON-response bug (FINDINGS.md): a
response cut off by max_tokens mid-array used to be silently indistinguishable
from a genuinely complete response -- a 16000-token-capped extraction call
salvaging 37 of 60 real events looked identical to a normal 37-event
response, with nothing anywhere recording that truncation happened.

No live API calls -- chronos.client.generate is monkeypatched throughout.
"""

from __future__ import annotations

import pytest

import evalkit.llm as llm
from evalkit.budget import BudgetTracker


def _fake_response(text: str, cost: float = 0.01) -> dict:
    return {"text": text, "cost_usd": cost, "budget": {"remaining_usd": 10.0}}


COMPLETE_JSON = '{"candidates": [{"id": 1}, {"id": 2}]}'
# Cut off mid-object -- the array never closes, the outer object never closes.
TRUNCATED_JSON = '{"candidates": [{"id": 1}, {"id": 2}, {"id": 3, "detail": "cut off here'


def test_clean_complete_response_parses_normally(monkeypatch):
    monkeypatch.setattr(llm.client, "generate", lambda *a, **k: _fake_response(COMPLETE_JSON))
    tracker = BudgetTracker()
    result = llm.call_json(tracker, "cat", prompt="p")
    assert result == {"candidates": [{"id": 1}, {"id": 2}]}
    assert "_incomplete_salvaged_response" not in result


def test_truncated_response_raises_instead_of_silently_returning_partial_data(monkeypatch):
    """Default behavior (allow_salvage=False, every judge call site): a
    truncated response must never be treated as an ordinary success, even
    though the salvaged partial JSON is technically valid-looking."""
    monkeypatch.setattr(llm.client, "generate", lambda *a, **k: _fake_response(TRUNCATED_JSON))
    tracker = BudgetTracker()
    with pytest.raises(llm.TruncatedResponseError):
        llm.call_json(tracker, "cat", prompt="p")


def test_truncated_response_recovers_via_a_clean_retry(monkeypatch):
    """If the repair retry comes back complete, that's a normal success --
    truncation on the FIRST attempt alone must not be treated as fatal."""
    calls = iter([_fake_response(TRUNCATED_JSON), _fake_response(COMPLETE_JSON)])
    monkeypatch.setattr(llm.client, "generate", lambda *a, **k: next(calls))
    tracker = BudgetTracker()
    result = llm.call_json(tracker, "cat", prompt="p")
    assert result == {"candidates": [{"id": 1}, {"id": 2}]}


def test_allow_salvage_true_returns_partial_data_explicitly_flagged(monkeypatch):
    """Extraction's opt-in path: partial data is kept (recall-oriented), but
    the caller MUST be able to see it was incomplete -- never silent."""
    monkeypatch.setattr(llm.client, "generate", lambda *a, **k: _fake_response(TRUNCATED_JSON))
    tracker = BudgetTracker()
    result = llm.call_json(tracker, "cat", prompt="p", allow_salvage=True)
    assert result["_incomplete_salvaged_response"] is True
    assert result["candidates"] == [{"id": 1}, {"id": 2}]  # the 3rd, cut-off object is correctly dropped


def test_double_truncation_keeps_the_salvage_with_more_recovered_objects(monkeypatch):
    """Regression (code-reviewer nit): if BOTH attempts truncate, the repair
    retry isn't guaranteed to recover more than the first attempt did (it
    echoes the whole original prompt plus new instructions, so it can
    plausibly truncate EARLIER). Blindly preferring "whichever ran second"
    could silently discard a strictly better partial result -- working
    against extraction's whole reason for using allow_salvage in the first
    place (partial data beats none, but MORE partial data beats less)."""
    small_salvage = '{"candidates": [{"id": 1}]}extra-cut-off-junk-that-is-not-valid-json'
    responses = iter([
        _fake_response(TRUNCATED_JSON),   # first attempt: 2 recovered objects
        _fake_response(small_salvage),    # repair retry: only 1 recovered object -- worse
    ])
    monkeypatch.setattr(llm.client, "generate", lambda *a, **k: next(responses))
    tracker = BudgetTracker()
    result = llm.call_json(tracker, "cat", prompt="p", allow_salvage=True)
    assert result["_incomplete_salvaged_response"] is True
    assert result["candidates"] == [{"id": 1}, {"id": 2}], "must keep the FIRST attempt's larger salvage, not the second's smaller one"


def test_extract_candidates_surfaces_incomplete_flag(monkeypatch):
    import evalkit.extraction.candidates as candidates_mod
    monkeypatch.setattr(llm.client, "generate", lambda *a, **k: _fake_response(TRUNCATED_JSON))
    tracker = BudgetTracker()
    candidates, incomplete = candidates_mod.extract_candidates(tracker, doc_id="doc1", chunk_text="text")
    assert incomplete is True
    assert len(candidates) == 2
    assert all(c["source_doc_id"] == "doc1" for c in candidates)


def test_extract_candidates_clean_response_is_not_flagged_incomplete(monkeypatch):
    import evalkit.extraction.candidates as candidates_mod
    monkeypatch.setattr(llm.client, "generate", lambda *a, **k: _fake_response(COMPLETE_JSON))
    tracker = BudgetTracker()
    candidates, incomplete = candidates_mod.extract_candidates(tracker, doc_id="doc1", chunk_text="text")
    assert incomplete is False
    assert len(candidates) == 2


def test_extract_all_candidates_splits_a_truncated_chunk_and_recovers_cleanly(monkeypatch, tmp_path):
    """A chunk that comes back truncated must be split and re-extracted, not
    silently accepted -- if the split sub-chunks come back clean, the final
    result has NO incomplete ranges and all real candidates are recovered."""
    import evalkit.extraction.prepare as prepare_mod
    from evalkit.discover import Case, CaseDoc

    ocr_dir = tmp_path / "ocr"
    ocr_dir.mkdir()
    (ocr_dir / "doc1.json").write_text(
        '{"doc_id": "doc1", "pages": ["page one text", "page two text"]}', encoding="utf-8"
    )
    case = Case(
        case_id="case-x", label="Case X", documents=[CaseDoc("doc1", "doc1.pdf", 2)],
        ocr_dir=ocr_dir, pdf_dir=tmp_path, summaries_dir=tmp_path, manifest_path=tmp_path / "manifest.json",
    )

    call_log = []

    def fake_generate(prompt, **kwargs):
        # The whole-2-page chunk stays truncated through BOTH of call_json's own
        # attempts (original + its internal repair retry) -- calls 1 and 2. Once
        # prepare.py splits it into single-page sub-chunks, each comes back clean
        # on its first attempt -- calls 3 and 4.
        call_log.append(prompt)
        return _fake_response(TRUNCATED_JSON) if len(call_log) <= 2 else _fake_response(COMPLETE_JSON)

    monkeypatch.setattr(llm.client, "generate", fake_generate)
    tracker = BudgetTracker()
    all_candidates, incomplete_ranges = prepare_mod.extract_all_candidates(case, tracker)

    assert incomplete_ranges == [], "sub-chunks came back clean -- nothing should be marked incomplete"
    assert len(call_log) == 4, "2 truncated attempts on the full chunk + 2 clean single-page split retries"
    assert len(all_candidates) == 4, "2 clean candidates from each of the 2 split single-page chunks"


def test_extract_all_candidates_records_incomplete_range_when_split_cannot_recover(monkeypatch, tmp_path):
    """If even a single page keeps coming back truncated (can't be split
    further), the range must be recorded as incomplete -- not silently
    dropped or silently treated as a successful complete extraction."""
    import evalkit.extraction.prepare as prepare_mod
    from evalkit.discover import Case, CaseDoc

    ocr_dir = tmp_path / "ocr"
    ocr_dir.mkdir()
    (ocr_dir / "doc1.json").write_text('{"doc_id": "doc1", "pages": ["page one text"]}', encoding="utf-8")
    case = Case(
        case_id="case-x", label="Case X", documents=[CaseDoc("doc1", "doc1.pdf", 1)],
        ocr_dir=ocr_dir, pdf_dir=tmp_path, summaries_dir=tmp_path, manifest_path=tmp_path / "manifest.json",
    )

    monkeypatch.setattr(llm.client, "generate", lambda *a, **k: _fake_response(TRUNCATED_JSON))
    tracker = BudgetTracker()
    all_candidates, incomplete_ranges = prepare_mod.extract_all_candidates(case, tracker)

    assert incomplete_ranges == [("doc1", 1, 1)]
    assert len(all_candidates) == 2, "the partial salvage is still kept -- recall-oriented, partial beats none"


def test_run_full_extraction_reports_incomplete_ranges_in_validation_problems(monkeypatch, tmp_path):
    import evalkit.extraction.prepare as prepare_mod
    from evalkit.discover import Case, CaseDoc

    ocr_dir = tmp_path / "ocr"
    ocr_dir.mkdir()
    (ocr_dir / "doc1.json").write_text('{"doc_id": "doc1", "pages": ["page one text"]}', encoding="utf-8")
    case = Case(
        case_id="case-x", label="Case X", documents=[CaseDoc("doc1", "doc1.pdf", 1)],
        ocr_dir=ocr_dir, pdf_dir=tmp_path, summaries_dir=tmp_path, manifest_path=tmp_path / "manifest.json",
    )

    monkeypatch.setattr(llm.client, "generate", lambda *a, **k: _fake_response(TRUNCATED_JSON))
    tracker = BudgetTracker()
    result = prepare_mod.run_full_extraction(case, tracker)

    assert result["incomplete_extraction_ranges"] == [{"doc_id": "doc1", "start_page": 1, "end_page": 1}]
    assert any("INCOMPLETE EXTRACTION" in p for p in result["validation_problems"])
