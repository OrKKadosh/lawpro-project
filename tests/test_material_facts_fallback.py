"""get_or_build_material_facts tests -- the timeline-bound material-fact set
used to grade a candidate-extraction-generated summary's coverage (PLAN.md
S9/S10; FINDINGS.md: a real, confirmed bug -- this function used to reuse
the case's BENCHMARK-derived frozen fact set unconditionally, so a summary
generated from our own (differently-sized) candidate timeline was graded
against facts derived from a timeline it never saw). No live API calls --
call_json is monkeypatched.
"""

from __future__ import annotations

import json

import pytest

import evalkit.judge.material_facts as mf


class _FakeCase:
    case_id = "case-x"


def _fake_material_facts_response(prompt, **_):
    return {"material_facts": [{"fact_id": "f1", "category": "major injury", "description": "x",
                                 "materiality_weight": 2, "supporting_event_ids": [0]}]}


def _write_candidate_timeline(tmp_path, case_id, events):
    (tmp_path / f"{case_id}.json").write_text(
        json.dumps({"timeline": {"events": events}}), encoding="utf-8",
    )


def test_builds_from_the_candidate_timeline_never_the_benchmark_frozen_file(monkeypatch, tmp_path):
    """The core fix: even if a benchmark-derived frozen file exists for this
    case_id (load_frozen would happily return it), get_or_build_material_facts
    must never call it -- only the actual candidate timeline matters."""
    def boom(case_id):
        raise AssertionError("load_frozen (benchmark-derived facts) must never be consulted here")
    monkeypatch.setattr(mf, "load_frozen", boom)
    monkeypatch.setattr(mf, "call_json", lambda tracker, category, *, prompt, system, max_tokens: _fake_material_facts_response(prompt))
    monkeypatch.setattr(mf, "CANDIDATE_TIMELINES_DIR", tmp_path)
    monkeypatch.setattr(mf, "CANDIDATE_FACTS_DIR", tmp_path / "candidate_facts")

    _write_candidate_timeline(tmp_path, "case-x", [{"date": "2024-01-01", "type": "diagnosis", "detail": "test event"}])

    result = mf.get_or_build_material_facts(_FakeCase(), tracker=None)
    assert result["material_facts"][0]["fact_id"] == "f1"
    assert result["timeline_source"] == "candidate_extraction"
    assert "our own extraction" in result["benchmark_timeline_path"]
    assert result["human_spot_checked"] is False


def test_caches_by_timeline_hash_and_reuses_without_rebuilding(monkeypatch, tmp_path):
    monkeypatch.setattr(mf, "CANDIDATE_TIMELINES_DIR", tmp_path)
    facts_dir = tmp_path / "candidate_facts"
    monkeypatch.setattr(mf, "CANDIDATE_FACTS_DIR", facts_dir)

    events = [{"date": "2024-01-01", "type": "diagnosis", "detail": "test event"}]
    _write_candidate_timeline(tmp_path, "case-x", events)
    h = mf.timeline_hash(events)
    facts_dir.mkdir(parents=True)
    (facts_dir / f"case-x-{h[:16]}.json").write_text(
        json.dumps({"case_id": "case-x", "timeline_hash": h, "material_facts": ["already-cached"]}),
        encoding="utf-8",
    )

    def boom(*a, **k):
        raise AssertionError("must not rebuild when a hash-matching cache file already exists")
    monkeypatch.setattr(mf, "call_json", boom)

    result = mf.get_or_build_material_facts(_FakeCase(), tracker=None)
    assert result["material_facts"] == ["already-cached"]


def test_a_changed_candidate_timeline_never_reuses_the_old_cached_fact_set(monkeypatch, tmp_path):
    """The exact scenario the reviewer specified: benchmark timeline has
    facts A, B, C; candidate timeline has A, B, D. A stale cache entry for
    the OLD candidate timeline must never be served for the NEW one -- the
    hash changes, so a fresh build is triggered instead."""
    monkeypatch.setattr(mf, "CANDIDATE_TIMELINES_DIR", tmp_path)
    facts_dir = tmp_path / "candidate_facts"
    monkeypatch.setattr(mf, "CANDIDATE_FACTS_DIR", facts_dir)

    old_events = [{"date": "2024-01-01", "type": "diagnosis", "detail": "fact A"}]
    old_hash = mf.timeline_hash(old_events)
    facts_dir.mkdir(parents=True)
    (facts_dir / f"case-x-{old_hash[:16]}.json").write_text(
        json.dumps({"case_id": "case-x", "timeline_hash": old_hash, "material_facts": ["stale-from-old-timeline"]}),
        encoding="utf-8",
    )

    new_events = [
        {"date": "2024-01-01", "type": "diagnosis", "detail": "fact A"},
        {"date": "2024-01-02", "type": "diagnosis", "detail": "fact D -- new, not in the old timeline"},
    ]
    _write_candidate_timeline(tmp_path, "case-x", new_events)
    monkeypatch.setattr(mf, "call_json", lambda tracker, category, *, prompt, system, max_tokens: _fake_material_facts_response(prompt))

    result = mf.get_or_build_material_facts(_FakeCase(), tracker=None)
    assert result["material_facts"] != ["stale-from-old-timeline"]
    assert result["material_facts"][0]["fact_id"] == "f1"
    assert result["timeline_hash"] == mf.timeline_hash(new_events)


def test_raises_clearly_when_no_candidate_timeline_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(mf, "CANDIDATE_TIMELINES_DIR", tmp_path)  # empty -- no case-x.json in it
    with pytest.raises(FileNotFoundError, match="run `extract"):
        mf.get_or_build_material_facts(_FakeCase(), tracker=None)


def test_a_fact_absent_from_the_candidate_timeline_can_never_reduce_coverage(monkeypatch, tmp_path):
    """The other half of the reviewer's spec, exercised end to end: build a
    fact set from a candidate timeline that has facts A and D (not the
    benchmark's A, B, C), then score coverage for a summary against it --
    only A and D can ever appear as scoreable facts; B (benchmark-only,
    absent from the candidate timeline) structurally cannot reduce coverage
    because it was never in the fact set to begin with."""
    from evalkit.scoring import score_coverage

    monkeypatch.setattr(mf, "CANDIDATE_TIMELINES_DIR", tmp_path)
    monkeypatch.setattr(mf, "CANDIDATE_FACTS_DIR", tmp_path / "candidate_facts")

    def fake_response(prompt, **_):
        return {"material_facts": [
            {"fact_id": "fact-a", "category": "major injury", "description": "A", "materiality_weight": 2, "supporting_event_ids": [0]},
            {"fact_id": "fact-d", "category": "major injury", "description": "D", "materiality_weight": 1, "supporting_event_ids": [1]},
        ]}
    monkeypatch.setattr(mf, "call_json", lambda tracker, category, *, prompt, system, max_tokens: fake_response(prompt))

    candidate_events = [
        {"date": "2024-01-01", "type": "diagnosis", "detail": "fact A"},
        {"date": "2024-01-02", "type": "diagnosis", "detail": "fact D"},
    ]
    _write_candidate_timeline(tmp_path, "case-x", candidate_events)

    fact_set = mf.get_or_build_material_facts(_FakeCase(), tracker=None)
    fact_ids = {f["fact_id"] for f in fact_set["material_facts"]}
    assert fact_ids == {"fact-a", "fact-d"}, "benchmark-only fact B must never appear -- it was never in the candidate timeline"

    # A summary reflecting both A and D scores full coverage -- there is no "fact-b" the
    # summary could ever be marked as missing, because it's structurally not in the fact set.
    coverage = score_coverage(
        fact_coverage=[{"fact_id": "fact-a", "reflected": "yes"}, {"fact_id": "fact-d", "reflected": "yes"}],
        material_facts=fact_set["material_facts"],
    )
    assert coverage["weighted_coverage_rate"] == 1.0
    assert coverage["facts_missing"] == []
