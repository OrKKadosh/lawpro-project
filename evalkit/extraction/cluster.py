"""Duplicate/event clustering (PLAN.md S3/S6).

Groups candidate mentions of the same real-world event, preserving every
field value each mention carries. Selects nothing -- no date/provider/
finding is chosen here. Deterministic blocking (date + type + a lightweight
text-similarity check on clinical_facts/evidence_text), not an LLM call:
the goal is a cheap, auditable heuristic, not a full NLP dedup system.

Distinct-but-repetitive events (e.g. individual PT sessions on different
dates) block apart naturally, since they don't share a date -- clustering
never conflates "same kind of event" with "same event instance". That
distinction is salience.py's job (PLAN.md: dedup vs. salience are separate
problems, DECISIONS.md).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date as _date
from typing import Any

SIMILARITY_THRESHOLD = 0.25
NEAR_DATE_WINDOW_DAYS = 5
NEAR_DATE_SIMILARITY_THRESHOLD = 0.45
NEAR_DATE_ELIGIBLE_TYPES = {"procedure", "diagnosis", "imaging"}
STOPWORDS = {
    "the", "a", "an", "of", "for", "and", "or", "with", "to", "on", "in",
    "at", "by", "was", "is", "were", "left", "right", "patient",
}


def _significant_words(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 2}


def _candidate_words(candidate: dict[str, Any]) -> set[str]:
    cf = candidate.get("clinical_facts") or {}
    text_parts = [
        candidate.get("evidence_text", ""),
        candidate.get("raw_summary", ""),
        str(cf.get("concept") or ""),
        str(cf.get("procedure") or ""),
        str(cf.get("diagnosis_or_finding") or ""),
        str(cf.get("medication") or ""),
    ]
    return _significant_words(" ".join(text_parts))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


NAME_FIELDS = ("concept", "diagnosis_or_finding", "procedure", "medication")


def facts_clearly_distinct(cf_a: dict[str, Any], cf_b: dict[str, Any]) -> bool:
    """True if two clinical_facts dicts name something specific for the SAME
    field and those names share no significant word -- a specific
    structured signal that overrides generic text-boilerplate similarity.
    Found via real Davis output (DECISIONS.md): four distinct same-day
    medications (Hydromorphone PCA, Gabapentin, Cefazolin, Oxycodone)
    shared enough templated administration-note wording to clear the
    Pass-1 clustering Jaccard bar, even though each carried a clean,
    populated, mutually-exclusive `medication` name that clustering wasn't
    checking. A populated name field beats a blunt text-overlap threshold
    whenever the two names disagree entirely.

    Checks EVERY populated field pair, not just the first one found -- an
    existence check ("does any field pair disagree"), order-independent by
    construction, since only a disagreement causes an early return; an
    agreement never stops the scan early. This matters: two different
    "fix the field check" attempts were tried this session and BOTH
    reverted after real-data testing found them unsafe (full account in
    FINDINGS.md/DECISIONS.md) --
      1. "Stop at the first field both candidates populate, in a
         most-specific-first order" -- this looked like it would fix the
         Harrison/X-ray case-vance fabrication (concept disagreeing vetoed
         a merge procedure would have allowed), but a second adversarial
         review, testing it against the real cached candidates end-to-end
         (not just a unit-test fixture), found it silently dropped a
         materiality="high" billing event (an Anesthesia line, CPT 01402)
         from case-vance's actual final timeline -- because the boilerplate
         token "CPT" alone was enough to make two DIFFERENT billed
         procedures' `procedure` fields register as "agreeing," and
         stopping at that first comparable field meant a genuinely
         disagreeing `diagnosis_or_finding`/`concept` was never consulted.
         ~16 case-vance and 4 case-davis real clusters were affected.
      2. "Field agreement forces a merge" (not just non-blocking) -- tested
         separately, collapsed case-vance's final timeline from 202 to 137
         events (a third of it gone), for the same underlying reason: a
         single shared boilerplate word is too weak a signal to override
         Jaccard corpus-wide.
    Both attempts changed WHICH fields get consulted (via ordering/
    early-stopping); the original "check everything, block on any
    disagreement" property in THIS version never had that flaw -- it's
    restored here deliberately, unchanged from before this session's
    investigation. The Harrison/X-ray fabrication remains genuinely
    unresolved as a result (a real, disclosed limitation, not silently
    dropped) -- see FINDINGS.md for why: a proper fix needs boilerplate
    tokens (billing codes, generic category words) excluded from the
    word-overlap comparison, which is a larger, more carefully-tested
    change than this session's remaining budget/time supported doing
    safely.

    Deliberately compares each field to ITSELF only (medication vs.
    medication, concept vs. concept), never pooling every field's words
    into one bag -- an earlier version of this idea pooled fields and
    reintroduced the same contamination one level up (two different
    drugs' `concept` text both saying "...antibiotic administration" /
    "...medication administration" shared enough generic words to merge
    again, even though their `medication` fields flatly disagreed)."""
    for f in NAME_FIELDS:
        va, vb = cf_a.get(f), cf_b.get(f)
        if not va or not vb:
            continue
        wa, wb = _significant_words(str(va)), _significant_words(str(vb))
        if wa and wb and not (wa & wb):
            return True
    return False


def _clearly_distinct_named_facts(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return facts_clearly_distinct(a.get("clinical_facts") or {}, b.get("clinical_facts") or {})


def _days_apart(date_a: str, date_b: str) -> int:
    try:
        return abs((_date.fromisoformat(date_a) - _date.fromisoformat(date_b)).days)
    except ValueError:
        return 9999


@dataclass
class Cluster:
    cluster_id: str
    member_indices: list[int] = field(default_factory=list)

    def members(self, candidates: list[dict]) -> list[dict]:
        return [candidates[i] for i in self.member_indices]


def cluster_candidates(candidates: list[dict[str, Any]], id_prefix: str) -> list[Cluster]:
    """Block by (normalized_date, event_type), then merge within a block by
    text-similarity union-find. Candidates with no normalized_date never
    auto-merge with anything (too weak a signal to cluster on safely) --
    each becomes its own singleton cluster.
    """
    n = len(candidates)
    words = [_candidate_words(c) for c in candidates]
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    # Pass 1: exact (date, type) blocking + moderate similarity. Catches the
    # common case -- the same visit/event mentioned twice with a matching date.
    buckets: dict[tuple, list[int]] = {}
    for i, c in enumerate(candidates):
        date = c.get("normalized_date")
        if not date:
            continue  # no safe blocking key -- stays a singleton for this pass
        key = (date, c.get("event_type_candidate"))
        buckets.setdefault(key, []).append(i)

    for indices in buckets.values():
        for a in range(len(indices)):
            for b in range(a + 1, len(indices)):
                i, j = indices[a], indices[b]
                if _jaccard(words[i], words[j]) >= SIMILARITY_THRESHOLD and not _clearly_distinct_named_facts(
                    candidates[i], candidates[j]
                ):
                    union(i, j)

    # Pass 2: near-date matching (same type, dates within NEAR_DATE_WINDOW_DAYS)
    # with a HIGHER similarity bar. Exact-date blocking alone would never even
    # bucket together a billing-form date and an operative-report date for the
    # same surgery when they genuinely disagree -- which is exactly the failure
    # mode conflict.py needs to see (PLAN.md S6 / the billing-vs-operative-date
    # trap, FINDINGS.md).
    #
    # Restricted to NEAR_DATE_ELIGIBLE_TYPES (one-time clinical events, where a
    # cited date genuinely disagreeing across sources is the trap this pass
    # targets) -- NOT therapy/encounter/medication, whose templated, highly
    # repetitive notes (found the hard way: two real, genuinely distinct PT
    # visits two days apart shared enough boilerplate wording to clear even a
    # 0.45 Jaccard bar) would otherwise get wrongly merged. Distinct-but-
    # repetitive events staying separate is the whole point of this module
    # (DECISIONS.md) -- text similarity alone can't safely carry that
    # distinction for templated routine notes, so this pass doesn't try to.
    dated = [(i, c) for i, c in enumerate(candidates) if c.get("normalized_date")]
    for a in range(len(dated)):
        i, ci = dated[a]
        for b in range(a + 1, len(dated)):
            j, cj = dated[b]
            if find(i) == find(j):
                continue
            if ci.get("event_type_candidate") != cj.get("event_type_candidate"):
                continue
            if ci.get("event_type_candidate") not in NEAR_DATE_ELIGIBLE_TYPES:
                continue
            if _days_apart(ci["normalized_date"], cj["normalized_date"]) > NEAR_DATE_WINDOW_DAYS:
                continue
            if _jaccard(words[i], words[j]) >= NEAR_DATE_SIMILARITY_THRESHOLD and not _clearly_distinct_named_facts(
                ci, cj
            ):
                union(i, j)

    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)

    return [
        Cluster(cluster_id=f"{id_prefix}-cl{k:03d}", member_indices=sorted(idxs))
        for k, idxs in enumerate(groups.values())
    ]
