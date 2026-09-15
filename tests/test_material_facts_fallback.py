"""get_or_build_material_facts tests -- the fallback that lets a genuinely
new case (no golden/input_timeline, only OCR + our own extraction) still
get a material-fact checklist to evaluate summaries against. No live API
calls -- call_json/save_frozen/load_frozen are all monkeypatched.
"""

from __future__ import annotations

import json

import pytest

import evalkit.judge.material_facts as mf


class _FakeCaseWithReference:
    case_id = "case-with-ref"

    def reference_timeline_path(self):
        from pathlib import Path
        return Path("does-not-matter.json")


class _FakeCaseNoReference:
    case_id = "case-no-ref"

    def reference_timeline_path(self):
        raise FileNotFoundError("no reference for this case")


def _fake_material_facts_response(prompt, **_):
    return {"material_facts": [{"fact_id": "f1", "category": "major injury", "description": "x",
                                 "materiality_weight": 2, "supporting_event_ids": [0]}]}


def test_reuses_frozen_file_without_rebuilding(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("must not attempt to build when a frozen file already exists")
    monkeypatch.setattr(mf, "build_material_fact_set", boom)
    monkeypatch.setattr(mf, "load_frozen", lambda case_id: {"case_id": case_id, "material_facts": ["already-frozen"]})

    result = mf.get_or_build_material_facts(_FakeCaseWithReference(), tracker=None)
    assert result["material_facts"] == ["already-frozen"]


def test_falls_back_to_our_own_extraction_when_no_reference(monkeypatch, tmp_path):
    def missing(case_id):
        raise FileNotFoundError
    monkeypatch.setattr(mf, "load_frozen", missing)
    monkeypatch.setattr(mf, "call_json", lambda tracker, category, *, prompt, system, max_tokens: _fake_material_facts_response(prompt))
    monkeypatch.setattr(mf, "CANDIDATE_TIMELINES_DIR", tmp_path)
    saved = {}
    monkeypatch.setattr(mf, "save_frozen", lambda case_id, fact_set: saved.update(case_id=case_id, fact_set=fact_set))

    (tmp_path / "case-no-ref.json").write_text(
        json.dumps({"timeline": {"events": [{"date": "2024-01-01", "type": "diagnosis", "detail": "test event"}]}}),
        encoding="utf-8",
    )

    result = mf.get_or_build_material_facts(_FakeCaseNoReference(), tracker=None)
    assert result["material_facts"][0]["fact_id"] == "f1"
    assert "our own extraction" in result["benchmark_timeline_path"]
    assert saved["case_id"] == "case-no-ref"


def test_raises_clearly_when_neither_reference_nor_extraction_exists(monkeypatch, tmp_path):
    def missing(case_id):
        raise FileNotFoundError
    monkeypatch.setattr(mf, "load_frozen", missing)
    monkeypatch.setattr(mf, "CANDIDATE_TIMELINES_DIR", tmp_path)  # empty -- no case-no-ref.json in it

    with pytest.raises(FileNotFoundError, match="run `extract"):
        mf.get_or_build_material_facts(_FakeCaseNoReference(), tracker=None)
