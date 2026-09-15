"""Recall-oriented candidate-event extraction (PLAN.md S3/S4).

This call is deliberately NOT asked to decide what belongs in the final
attorney timeline -- only to find and preserve every plausible clinical
event, with enough structure (date_basis, status, attribution,
clinical_facts) that later stages (cluster/conflict/salience/project) have
something real to work with. Information dropped here can never be
recovered downstream, so recall is the only objective at this stage.
"""

from __future__ import annotations

from evalkit.budget import BudgetTracker
from evalkit.llm import call_json

EXTRACTION_SYSTEM_PROMPT = """You are extracting a recall-oriented list of candidate clinical \
events from a scanned medical record, for a legal case timeline. Your ONLY job at this stage is \
to find every plausible clinical event and preserve it faithfully -- you do NOT decide whether an \
event is important enough for a final attorney-facing timeline; that decision happens in a later \
stage. When in doubt, include it as a candidate rather than omit it. Extract EVERY event you can \
find, including routine/repetitive ones (e.g. each individual therapy visit is its own event, not \
one summary event) -- do not compress or select at this stage.

Scope: extract CLINICAL events only -- encounters/visits, diagnoses, procedures or surgeries, \
imaging studies, medication administrations or prescription fills, and therapy sessions. Do NOT \
extract individual billing line items for supplies, equipment, room & board, tourniquets, \
drapes, or other non-clinical charges as their own events -- a billing document's date-of-service \
and diagnosis/procedure codes are useful evidence for confirming a real clinical event's date or \
provider, but the line item itself is not a clinical event. When a billing/claim form lists the \
same clinical service (e.g. a surgery, an office visit, a PT session) that's also documented \
elsewhere in this chunk, extract it once, using whichever source is more specific about what \
actually happened.

For each event, extract these fields:

- source_page: the page number where the evidence appears (from the [pN] markers in the text)
- evidence_text: a SHORT verbatim quote or close paraphrase of the specific text supporting this \
event -- one phrase or sentence, under roughly 150 characters, not the whole page and not \
multiple sentences
- raw_date: the date exactly as it appears or is implied in the source (e.g. "09/15/2023", \
"six days ago", "last week")
- normalized_date: your best ISO YYYY-MM-DD normalization of raw_date, or null if not recoverable
- date_basis, one of:
  - "explicit_event_date": the date the clinical event itself occurred, stated directly (e.g. an \
operative report's "Date of Surgery")
  - "relative_to_note_date": a relative statement ("six days ago", "last week") anchored to the \
date the note itself was written
  - "note_signing_date": the date a note/report was signed or dictated, used only when that's the \
only date available and it may differ from when the event actually happened
  - "billing_service_date": a date drawn from a billing/claim form's service-date field -- BE \
CAREFUL, billing dates can differ from the actual clinical event date (e.g. a hospital's \
"principal procedure date" on a UB-04 form may reflect the admission date rather than the actual \
surgery date). If you also see a more specific clinical source for the same event elsewhere in \
this chunk, prefer that source and note the discrepancy in evidence_text.
  - "inferred": you calculated the date from other information (e.g. "postoperative day 4" plus a \
known admission date)
  - "unknown": no date information recoverable
- date_confidence: 0.0-1.0
- event_type_candidate: one of encounter, imaging, medication, procedure, therapy, diagnosis
- status: one of performed, ordered, recommended, planned, considered, cancelled, \
reported_history -- do NOT default to "performed"; read carefully whether something was actually \
done, merely ordered/recommended, or is a plan for the future
- attribution: {"asserted_by": one of patient_reported / clinician_observed / clinician_opinion / \
billing_system, "provider": the named provider if any or null, "certainty": confirmed / suspected \
/ uncertain -- reflect the SOURCE's own hedging language (e.g. "inconclusive", "possibly") rather \
than flattening it into false certainty}
- temporal_relation_to_incident: pre-incident / index-incident / post-incident / unknown (use \
"unknown" if this chunk alone doesn't make clear which incident is the index one)
- materiality_hint: high / relevant / routine -- your rough guess only; a later stage makes the \
real decision
- extraction_confidence: 0.0-1.0, your overall confidence this is a real, correctly-characterized \
event
- clinical_facts: a compact object with any of these that apply, others null -- concept, \
body_site, laterality, diagnosis_or_finding, procedure, medication, dose. Do not force values that \
aren't in the source.
- raw_summary: one plain-English sentence describing the event, for a human reviewer

Respond with ONLY this JSON structure, no other text, no markdown fences:
{"candidates": [ {<all fields above>}, ... ]}

ADDITIONAL RULES (added after real-run failures found by manual inspection -- read carefully; frozen after a bounded comparison experiment against a baseline, DECISIONS.md/results/prompt_experiment.md):

1. GROUNDING: never populate clinical_facts using outside medical-coding knowledge (e.g. what a \
CPT/HCPCS code conventionally means). If a billing line gives only a code and a generic charge \
description ("Operating Room Services", "Radiology/Diagnostic") with no clinical narrative \
elsewhere in this chunk describing what was actually done, leave clinical_facts.procedure, \
.diagnosis_or_finding, and .body_site null and put the raw code/description verbatim in \
evidence_text instead of interpreting it. A code is evidence a billed service occurred, never \
evidence of what that service specifically was for THIS patient.

2. ATTRIBUTION: a note's signer/attending physician is not always the physician responsible for a \
specific action described in that note. When the note names a DIFFERENT physician as the one being \
consulted, ordering, or performing a specific procedure (e.g. "Consult Dr. X immediately for \
emergency surgery", "per Dr. Y's recommendation"), set attribution.provider to that specifically-\
named acting physician for that action, not to the note's signer. Read the sentence carefully to \
identify who is actually doing or being asked to do the thing, not just whose letterhead the note \
is on."""


def extract_candidates(
    tracker: BudgetTracker,
    *,
    doc_id: str,
    chunk_text: str,
    category: str = "extraction",
    max_tokens: int = 16000,
    system_prompt: str = EXTRACTION_SYSTEM_PROMPT,
) -> list[dict]:
    """Extract candidate events from one chunk of a document's OCR text.

    `chunk_text` should already carry [pN] page markers (see discover.py's
    ocr_text / a page-range slice of it). Returns the raw list of candidate
    dicts -- no dedup/salience/projection happens here.

    `system_prompt` defaults to the frozen production prompt; the prompt
    iteration experiment (`prompt_experiment.py`) overrides it to compare
    variants without duplicating the call/parsing logic.
    """
    prompt = f"""Document `{doc_id}`, OCR text (pages marked [pN]):

{chunk_text}

---

Extract every candidate clinical event per the instructions above."""
    result = call_json(
        tracker, category, prompt=prompt, system=system_prompt, max_tokens=max_tokens
    )
    candidates = result.get("candidates", [])
    for c in candidates:
        c["source_doc_id"] = doc_id
    return candidates
