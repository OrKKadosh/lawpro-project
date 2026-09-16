"""Thin JSON-mode wrapper over chronos.client.generate.

Every call in evalkit that needs structured output goes through here:
- prompts and responses are logged to runs/prompt_log.jsonl for review
  (prompt logs are visible to reviewers -- see CLAUDE.md)
- the response text is parsed as JSON; on a parse failure, one retry is
  made with the parse error appended to the prompt
- the BudgetTracker records cost and enforces the floor before every call
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Optional

from chronos import client, constants
from evalkit.budget import BudgetTracker

PROMPT_LOG_PATH = Path(__file__).resolve().parents[1] / "runs" / "prompt_log.jsonl"


class LLMCallError(RuntimeError):
    """Raised when a call still isn't valid JSON after one retry."""


class TruncatedResponseError(LLMCallError):
    """Raised when a response was cut off by max_tokens mid-array and no
    COMPLETE JSON could be obtained even after the repair retry -- a
    genuinely different failure mode from ordinary malformed JSON, and one
    that must never be silently accepted as a normal success. A response
    salvaged from truncation is real, partial, already-paid-for data (some
    callers -- recall-oriented candidate extraction -- deliberately choose
    to keep it via `allow_salvage=True`), but the caller must always be
    told it happened, never left to assume the response was complete."""


def call_json(
    tracker: BudgetTracker,
    category: str,
    *,
    prompt: str,
    system: Optional[str] = None,
    model: str = constants.SONNET_5,
    max_tokens: int = 4096,
    allow_salvage: bool = False,
) -> dict[str, Any]:
    """Call /v1/generate, parse the response as JSON, retry once on parse failure.

    Returns the parsed JSON object. Raises LLMCallError if it's still not
    valid JSON after the retry, or BudgetExceeded (from budget.py) if the
    floor would be breached before a call is attempted.

    A response cut off by max_tokens (detected via `_salvage_truncated_
    array`'s partial-parse) is NEVER treated as an ordinary success, even
    though it produces valid-looking JSON for the objects that did complete
    (FINDINGS.md: this was a real, unguarded gap -- a 16000-token-capped
    extraction call salvaging 37 of 60 real events looked identical to a
    normal 37-event response, with nothing anywhere recording that
    truncation happened). By default (`allow_salvage=False`, every judge
    call site), a salvaged parse is treated exactly like a JSON parse
    failure -- the repair retry is attempted, and if the retry ALSO comes
    back truncated, `TruncatedResponseError` is raised rather than quietly
    returning partial data. A caller that explicitly wants the partial data
    over nothing (candidate extraction: recall-oriented, a caller-level
    retry/chunk-split strategy already exists to recover the rest) passes
    `allow_salvage=True`; even then, the returned dict carries
    `_incomplete_salvaged_response: True` so the caller has to notice
    rather than being able to ignore it by construction.
    """
    tracker.check_floor()
    parsed, raw_text, error, salvaged = _attempt(tracker, category, prompt, system, model, max_tokens)
    if parsed is not None and not salvaged:
        return parsed
    if parsed is not None and salvaged and allow_salvage:
        first_salvage = parsed

    tracker.check_floor()
    if parsed is not None and salvaged:
        repair_prompt = (
            f"{prompt}\n\n---\nYour previous response was CUT OFF before it finished (truncated mid-array). "
            "Respond again with the COMPLETE JSON, no other text, no markdown fences -- make sure every "
            "object in the array is fully closed and the response is not cut off this time."
        )
    else:
        repair_prompt = (
            f"{prompt}\n\n---\nYour previous response was not valid JSON. "
            f"Parse error: {error}\nPrevious response:\n{raw_text}\n\n"
            "Respond again with ONLY valid JSON, no other text, no markdown fences."
        )
    parsed2, raw_text2, error2, salvaged2 = _attempt(tracker, category, repair_prompt, system, model, max_tokens)
    if parsed2 is not None and not salvaged2:
        return parsed2
    if allow_salvage:
        candidates = []
        if parsed is not None and salvaged:
            candidates.append(first_salvage)
        if parsed2 is not None and salvaged2:
            candidates.append(parsed2)
        if candidates:
            # Both attempts truncated -- keep whichever salvage actually recovered MORE
            # complete objects, not just whichever ran second. The repair prompt echoes the
            # whole original prompt plus new instructions, so it can plausibly truncate
            # EARLIER into the array than the first attempt did; blindly preferring the
            # second attempt could silently discard a strictly better partial result,
            # working against "recall-oriented, partial data beats none" (this module's
            # whole reason for supporting allow_salvage in the first place).
            best = max(candidates, key=_salvaged_item_count)
            best["_incomplete_salvaged_response"] = True
            return best

    if salvaged or salvaged2:
        raise TruncatedResponseError(
            f"Response truncated by max_tokens and could not be completed after retry "
            f"(category={category!r}, max_tokens={max_tokens}). Raw (first attempt): {raw_text[:500]}"
        )
    raise LLMCallError(f"Still not valid JSON after one retry: {error2}\nRaw: {raw_text2[:500]}")


TRANSIENT_RETRY_DELAY_SECONDS = 3


def _generate_with_transient_retry(prompt: str, *, model: str, system: Optional[str], max_tokens: int) -> dict:
    """One short retry for a transient platform-side failure (5xx/timeout) --
    distinct from call_json's JSON-repair retry, which handles a different
    failure mode (a successful response that isn't valid JSON). Found the
    hard way: a multi-call batch job (e.g. prepare.py's full extraction
    run) has no per-call checkpointing, so one flaky 504 previously killed
    an entire ~$2 run with zero completed progress saved."""
    try:
        return client.generate(prompt, model=model, system=system, max_tokens=max_tokens)
    except client.PlatformError as exc:
        if exc.status < 500:
            raise
        time.sleep(TRANSIENT_RETRY_DELAY_SECONDS)
        return client.generate(prompt, model=model, system=system, max_tokens=max_tokens)


def _attempt(
    tracker: BudgetTracker,
    category: str,
    prompt: str,
    system: Optional[str],
    model: str,
    max_tokens: int,
) -> tuple[Optional[dict], str, Optional[str], bool]:
    response = _generate_with_transient_retry(prompt, model=model, system=system, max_tokens=max_tokens)
    tracker.record(category, response)
    raw_text = response.get("text", "")
    _log_prompt(category, prompt, system, raw_text)
    try:
        parsed, salvaged = _extract_json(raw_text)
        return parsed, raw_text, None, salvaged
    except (json.JSONDecodeError, ValueError) as exc:
        return None, raw_text, str(exc), False


def _extract_json(text: str) -> tuple[dict, bool]:
    """Returns (parsed, was_salvaged) -- was_salvaged is True whenever the
    clean json.loads() failed and a partial-array salvage was used instead,
    meaning the parsed dict is INCOMPLETE relative to what the model
    actually generated before being cut off."""
    text = text.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        text = text[first_newline + 1 :] if first_newline != -1 else text
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    try:
        return json.loads(text), False
    except json.JSONDecodeError as exc:
        salvaged = _salvage_truncated_array(text)
        if salvaged is not None:
            return salvaged, True
        raise exc


def _salvaged_item_count(parsed: dict) -> int:
    """How many complete objects a salvaged parse actually recovered --
    used only to pick the better of two truncated salvages (call_json),
    never to judge a clean parse. A salvaged dict is always {key: [objects]}
    by construction (_salvage_truncated_array's return shape)."""
    for value in parsed.values():
        if isinstance(value, list):
            return len(value)
    return 0


def _salvage_truncated_array(text: str) -> Optional[dict]:
    """Best-effort recovery for a response cut off mid-array by max_tokens.

    If `text` looks like `{"<key>": [ {...}, {...}, <cut off> ...`, parse as
    many complete top-level objects out of the array as possible rather than
    discarding the whole (already-paid-for) response. Returns None if the
    text doesn't look like this shape at all.
    """
    match = re.search(r'"(\w+)"\s*:\s*\[', text)
    if not match:
        return None
    key = match.group(1)
    array_start = match.end()
    objects: list[Any] = []
    depth = 0
    obj_start: Optional[int] = None
    in_string = False
    escape = False
    for i in range(array_start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            if depth == 0:
                obj_start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and obj_start is not None:
                try:
                    objects.append(json.loads(text[obj_start : i + 1]))
                except json.JSONDecodeError:
                    pass
                obj_start = None
    if not objects:
        return None
    return {key: objects}


def _log_prompt(category: str, prompt: str, system: Optional[str], response_text: str) -> None:
    PROMPT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": time.time(),
        "category": category,
        "system": system,
        "prompt": prompt,
        "response": response_text,
    }
    with PROMPT_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
