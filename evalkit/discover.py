"""Case discovery from data/<case>/.

CLAUDE.md non-negotiable: no hardcoded case or document identifiers. Every
case is found by walking data/ for a manifest.json, never by name.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
GOLDEN_DIR = Path(__file__).resolve().parents[1] / "golden"


@dataclass
class CaseDoc:
    doc_id: str
    title: str
    pages: int


@dataclass
class Case:
    case_id: str
    label: str
    documents: list[CaseDoc]
    ocr_dir: Path
    pdf_dir: Path
    summaries_dir: Path
    manifest_path: Path

    def ocr_pages(self, doc_id: str) -> list[str]:
        path = self.ocr_dir / f"{doc_id}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return data["pages"]

    def ocr_text(self, doc_id: str) -> str:
        """All pages of a document, joined with [pN] markers for citation."""
        pages = self.ocr_pages(doc_id)
        return "\n\n".join(f"[p{i + 1}]\n{page}" for i, page in enumerate(pages))

    def golden_timeline_path(self) -> Optional[Path]:
        p = GOLDEN_DIR / f"{self.case_id}.timeline.json"
        return p if p.is_file() else None

    def input_timeline_path(self) -> Optional[Path]:
        p = self.summaries_dir / "input_timeline.json"
        return p if p.is_file() else None

    def reference_timeline_path(self) -> Path:
        """The confirmed exact input behind this case's 8 supplied summaries (PLAN.md S8).

        Both cases now have a confirmed exact input: Davis via the shipped
        input_timeline.json, Vance via golden/case-vance.timeline.json
        (confirmed through the hiring contact -- FINDINGS.md).
        """
        for candidate in (self.golden_timeline_path(), self.input_timeline_path()):
            if candidate is not None:
                return candidate
        raise FileNotFoundError(f"No reference timeline found for case {self.case_id}")

    def corrected_reference_timeline_path(self) -> Path:
        """The reference timeline used for scoring OUR OWN extraction
        (evalkit/reference/compare.py) -- deliberately separate from
        reference_timeline_path(), which the controlled benchmark uses and
        which must keep pointing at the exact, unedited timeline the 8
        pre-generated summaries were actually produced from.

        Prefers golden/<case>.timeline.corrected.json when one exists --
        a manually-corrected reference whose changes are sourced only from
        the independent source audit (never from our own candidate
        extraction, DECISIONS.md) -- falling back to
        reference_timeline_path() for any case without one (e.g. Davis,
        whose own audit found no confirmed errors to correct).
        """
        corrected = GOLDEN_DIR / f"{self.case_id}.timeline.corrected.json"
        if corrected.is_file():
            return corrected
        return self.reference_timeline_path()

    def pregenerated_summary_paths(self) -> list[Path]:
        return sorted(
            p for p in self.summaries_dir.glob("*-run*.json") if p.name != "input_timeline.json"
        )


def discover_cases() -> list[Case]:
    """Every case under data/<case>/ with a manifest.json."""
    cases = []
    if not DATA_DIR.is_dir():
        return cases
    for case_dir in sorted(DATA_DIR.iterdir()):
        manifest_path = case_dir / "manifest.json"
        if not manifest_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        documents = [
            CaseDoc(doc_id=d["doc_id"], title=d["title"], pages=d["pages"])
            for d in manifest["documents"]
        ]
        cases.append(
            Case(
                case_id=manifest["case_id"],
                label=manifest.get("label", manifest["case_id"]),
                documents=documents,
                ocr_dir=case_dir / "ocr",
                pdf_dir=case_dir / "pdf",
                summaries_dir=case_dir / "summaries",
                manifest_path=manifest_path,
            )
        )
    return cases


def get_case(case_id: str) -> Case:
    for case in discover_cases():
        if case.case_id == case_id:
            return case
    raise KeyError(f"Unknown case: {case_id!r}")
