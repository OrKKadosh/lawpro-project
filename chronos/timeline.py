"""The timeline format, and a checker for it.

Standard library only — nothing to install.

A timeline is a JSON object with an `events` array. Each event:

    {
      "date":   "2024-03-14"     ISO 8601, or null when the record gives no
                                 recoverable date
      "type":   "encounter"      one of: encounter, imaging, medication,
                                 procedure, therapy, diagnosis
      "detail": "..."            one sentence, required
      "source": "D003 p2"        optional; where in the records this came from
    }

Nothing else is accepted — an unexpected key is an error rather than being
ignored, so a typo fails loudly instead of silently dropping data.

Check a file before you spend a model call on it:

    python -m chronos.timeline check my_timeline.json

Exits 0 and prints a summary if the file is valid, or prints every problem with
its index and exits 1. The server applies the same rules and will tell you the
same things, but this is free and instant.
"""

import json
import sys
from datetime import date as _date
from pathlib import Path

EVENT_TYPES = ("encounter", "imaging", "medication", "procedure", "therapy", "diagnosis")
FIELDS = ("date", "type", "detail", "source")

MAX_EVENTS = 400
MAX_DETAIL_CHARS = 600


class TimelineError(ValueError):
    """One or more problems with a timeline. `problems` lists them all."""

    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__(f"{len(problems)} problem(s): " + "; ".join(problems[:3]))


def parse(raw) -> list[dict]:
    """Validate a timeline and return its events in normal form.

    Accepts either the full object (`{"events": [...]}`) or a bare list. Raises
    TimelineError listing *every* problem, not just the first — fixing one at a
    time is miserable.
    """
    if isinstance(raw, (str, bytes)):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TimelineError([f"not valid JSON: {exc}"]) from None

    events = raw.get("events") if isinstance(raw, dict) else raw
    if not isinstance(events, list):
        raise TimelineError(
            ['expected {"events": [...]} or a bare array of events']
        )
    if not events:
        raise TimelineError(["the timeline is empty"])
    if len(events) > MAX_EVENTS:
        raise TimelineError([f"{len(events)} events; the limit is {MAX_EVENTS}"])

    problems: list[str] = []
    out: list[dict] = []

    for i, event in enumerate(events):
        where = f"events[{i}]"
        if not isinstance(event, dict):
            problems.append(f"{where} is {type(event).__name__}, expected an object")
            continue

        unknown = sorted(set(event) - set(FIELDS))
        if unknown:
            problems.append(
                f"{where} has unexpected field(s) {unknown}; allowed: {list(FIELDS)}"
            )

        detail = event.get("detail")
        if not isinstance(detail, str) or not detail.strip():
            problems.append(f"{where}.detail is required and must be a non-empty string")
        elif len(detail) > MAX_DETAIL_CHARS:
            problems.append(
                f"{where}.detail is {len(detail)} chars; the limit is {MAX_DETAIL_CHARS}"
            )

        kind = event.get("type")
        if kind not in EVENT_TYPES:
            problems.append(
                f"{where}.type is {kind!r}; must be one of {list(EVENT_TYPES)}"
            )

        raw_date = event.get("date", None)
        if raw_date is not None and not _is_iso_date(raw_date):
            problems.append(
                f"{where}.date is {raw_date!r}; must be YYYY-MM-DD, or null if the "
                "record gives no recoverable date"
            )

        source = event.get("source")
        if source is not None and not isinstance(source, str):
            problems.append(f"{where}.source must be a string if present")

        out.append(
            {
                "date": raw_date if raw_date is not None else None,
                "type": kind,
                "detail": (detail or "").strip(),
                "source": source or "",
            }
        )

    if problems:
        raise TimelineError(problems)
    return out


def _is_iso_date(value) -> bool:
    if not isinstance(value, str) or len(value) != 10:
        return False
    try:
        _date.fromisoformat(value)
        return True
    except ValueError:
        return False


def summarise(events: list[dict]) -> str:
    counts: dict[str, int] = {}
    for e in events:
        counts[e["type"]] = counts.get(e["type"], 0) + 1
    dated = [e["date"] for e in events if e["date"]]
    span = f"{min(dated)} to {max(dated)}" if dated else "no dated events"
    breakdown = ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))
    undated = sum(1 for e in events if not e["date"])
    line = f"{len(events)} events, {span}\n  {breakdown}"
    if undated:
        line += f"\n  {undated} undated"
    return line


def _cli(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] != "check":
        print("usage: python -m chronos.timeline check <file.json>", file=sys.stderr)
        return 2

    path = Path(argv[1]).expanduser()
    if not path.is_file():
        print(f"no such file: {path}", file=sys.stderr)
        return 2

    try:
        events = parse(path.read_text())
    except TimelineError as exc:
        print(f"\n  {path.name}: {len(exc.problems)} problem(s)\n")
        for problem in exc.problems:
            print(f"    - {problem}")
        print()
        return 1

    print(f"\n  {path.name}: valid\n  {summarise(events)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
