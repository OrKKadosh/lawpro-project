"""Tiered inclusion -- select_material_timeline_events (PLAN.md S3/S9).

A distinct problem from clustering (DECISIONS.md): clustering already
guaranteed distinct real events (e.g. individual PT sessions on different
dates) stay separate canonical events. This stage decides which of those
real events actually belong in the final attorney timeline. High/relevant
materiality events are always kept. Routine, repetitive events (e.g. a long
run of near-identical therapy sessions) are compressed to a "started /
notable milestone / ended" pattern rather than flooding the timeline with
every occurrence -- deterministic heuristics, no LLM call.
"""

from __future__ import annotations

from evalkit.extraction.canonicalize import CanonicalEvent
from evalkit.extraction.cluster import _significant_words

FLAG_KEYWORDS = (
    "missed", "no show", "no-show", "provoked", "rebound", "worsening",
    "increased pain", "deficit", "discharge", "initial", "final",
    "transition", "gap", "flare",
)

MIN_GROUP_SIZE_FOR_COMPRESSION = 4  # below this, keep every event -- not worth compressing

# Only `medication` is reliably a short, specific, consistently-worded
# name across repeated mentions of the same real thing -- confirmed
# against real data (DECISIONS.md). `procedure`/`diagnosis_or_finding`
# turned out NOT to have that property: real repetitive PT-visit
# candidates commonly populate `procedure` with descriptive text that
# varies phrase-to-phrase just like `concept` does ("physical therapy"
# vs "ambulation with PT"), so keying on them exactly fragmented real PT
# courses into near-singletons instead of compressing them. Those two
# fields are pooled into the fuzzy tier instead, alongside `concept`.
HARD_NAME_FIELDS = ("medication",)
SOFT_NAME_FIELDS = ("concept", "procedure", "diagnosis_or_finding")


def _group_key(event: CanonicalEvent) -> tuple:
    return (event.type, (event.attribution or {}).get("provider"))


def _hard_identity(event: CanonicalEvent) -> str | None:
    cf = event.clinical_facts or {}
    for f in HARD_NAME_FIELDS:
        val = cf.get(f)
        if val:
            return f"{f}:{str(val).strip().lower()}"
    return None


def _fuzzy_cluster_by_concept(events: list[CanonicalEvent]) -> list[list[CanonicalEvent]]:
    """Union-find on SOFT_NAME_FIELDS word overlap, for events with no
    `medication` value (e.g. a PT visit note, which typically populates
    `concept`/`procedure` with text worded differently mention to mention
    -- "ambulation with physical therapy" vs "physical therapy session").
    Restricted to this subset specifically so it can never bridge two
    differently-named medications again (see module docstring /
    DECISIONS.md) -- medications are the one field confirmed to need
    exact, non-transitive separation; these looser descriptive fields are
    where the original fuzzy-compression behavior actually belongs."""
    n = len(events)
    words = [
        _significant_words(" ".join(str((e.clinical_facts or {}).get(f) or "") for f in SOFT_NAME_FIELDS))
        for e in events
    ]
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

    for i in range(n):
        for j in range(i + 1, n):
            if not words[i] or not words[j] or (words[i] & words[j]):
                union(i, j)

    groups: dict[int, list[CanonicalEvent]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(events[i])
    return list(groups.values())


def _sub_cluster_by_name(events: list[CanonicalEvent]) -> list[list[CanonicalEvent]]:
    """Within one (type, provider) bucket, split apart events that clearly
    name different things -- e.g. distinct medications sharing no
    attributed provider all fell into one bucket, and would otherwise be
    compressed together as if they were repeat instances of the same drug
    (found via real case-davis output, DECISIONS.md).

    Two tiers, deliberately NOT one fuzzy transitive union-find over
    everything -- an earlier version of this fix did exactly that (treat
    "shares no word on any populated field" as the sole merge veto,
    unioned pairwise) and it silently reintroduced the same contamination
    through a THIRD path: a compound "transitioned to Oxycodone and
    Gabapentin" candidate shares one word with pure-Oxycodone events and a
    different word with pure-Gabapentin events, so union-find's transitive
    closure walked Oxycodone -> bridge -> Gabapentin -> (chained further)
    into one 26-member group spanning half the medication list, even
    though any two of those drugs compared directly would have been
    correctly flagged as distinct. A pairwise "not distinct" veto isn't
    transitive, and union-find doesn't respect that.

    Fix: events with a specific named field (medication/procedure/
    diagnosis_or_finding -- `HARD_NAME_FIELDS`) are grouped by an EXACT
    normalized key, not fuzzy overlap -- no transitive bridging is
    possible through a dict key. Only events with NO hard identity field
    at all (concept-only, or nothing) go through fuzzy concept-word
    clustering, and that pool can no longer contain a medication/procedure
    name to bridge through."""
    hard_groups: dict[str, list[CanonicalEvent]] = {}
    soft_pool: list[CanonicalEvent] = []
    for e in events:
        key = _hard_identity(e)
        if key is not None:
            hard_groups.setdefault(key, []).append(e)
        else:
            soft_pool.append(e)

    groups = list(hard_groups.values())
    if soft_pool:
        groups.extend(_fuzzy_cluster_by_concept(soft_pool))
    return groups


def _is_flagged(event: CanonicalEvent) -> bool:
    text = " ".join(str(e.get("snippet") or "") for e in event.evidence).lower()
    return any(kw in text for kw in FLAG_KEYWORDS)


def select_material_timeline_events(events: list[CanonicalEvent]) -> list[CanonicalEvent]:
    high_relevant = [e for e in events if e.materiality in ("high", "relevant")]
    routine = [e for e in events if e.materiality == "routine"]

    groups: dict[tuple, list[CanonicalEvent]] = {}
    for e in routine:
        groups.setdefault(_group_key(e), []).append(e)

    kept_routine: list[CanonicalEvent] = []
    for group in groups.values():
        for sub_group in _sub_cluster_by_name(group):
            group_sorted = sorted(sub_group, key=lambda e: e.date or "")
            if len(group_sorted) < MIN_GROUP_SIZE_FOR_COMPRESSION:
                kept_routine.extend(group_sorted)
                continue
            keep_ids = {id(group_sorted[0]), id(group_sorted[-1])}
            for e in group_sorted:
                if _is_flagged(e):
                    keep_ids.add(id(e))
            kept_routine.extend([e for e in group_sorted if id(e) in keep_ids])

    return high_relevant + kept_routine
