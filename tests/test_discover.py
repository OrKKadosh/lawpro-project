"""Direct test of the dynamic case-discovery constraint (CLAUDE.md: "no
hardcoding to specific cases... discover cases dynamically from data/").

The existing coverage of this relied on data/case-synthtest/ (a real, but
fixed, fixture) actually being present -- true today, but not a test that
would fail if discovery quietly regressed into hardcoding case names. This
builds an arbitrary, never-seen-before case directory in a tmp_path and
proves discover_cases() finds it purely by scanning, with no code changes."""

from __future__ import annotations

import json

import evalkit.discover as discover


def test_discover_cases_finds_an_arbitrary_new_case_dir_by_scanning(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    case_dir = data_dir / "case-never-seen-before-xyz123"
    (case_dir / "ocr").mkdir(parents=True)
    (case_dir / "manifest.json").write_text(json.dumps({
        "case_id": "case-never-seen-before-xyz123",
        "label": "arbitrary fixture, exists only for this test",
        "documents": [{"doc_id": "doc1", "title": "doc1.pdf", "pages": 1}],
    }), encoding="utf-8")

    monkeypatch.setattr(discover, "DATA_DIR", data_dir)
    cases = discover.discover_cases()

    assert len(cases) == 1
    assert cases[0].case_id == "case-never-seen-before-xyz123"
    assert cases[0].documents[0].doc_id == "doc1"


def test_discover_cases_ignores_a_directory_with_no_manifest(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    (data_dir / "not-a-case").mkdir(parents=True)

    monkeypatch.setattr(discover, "DATA_DIR", data_dir)
    assert discover.discover_cases() == []


def test_discover_cases_empty_when_data_dir_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(discover, "DATA_DIR", tmp_path / "does-not-exist")
    assert discover.discover_cases() == []
