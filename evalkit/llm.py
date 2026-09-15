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


def call_json(
    tracker: BudgetTracker,
    category: str,
    *,
    prompt: str,
    system: Optional[str] = None,
    model: str = constants.SONNET_5,
    max_tokens: int = 4096,
) -> dict[str, Any]:
    """Call /v1/generate, parse the response as JSON, retry once on parse failure.

    Returns the parsed JSON object. Raises LLMCallError if it's still not
    valid JSON after the retry, or BudgetExceeded (from budget.py) if the
    floor would be breached before a call is attempted.
    """
    tracker.check_floor()
    parsed, raw_text, error = _attempt(tracker, category, prompt, system, model, max_tokens)
    if parsed is not None:
        return parsed

    tracker.check_floor()
    repair_prompt = (
        f"{prompt}\n\n---\nYour previous response was not valid JSON. "
        f"Parse error: {error}\nPrevious response:\n{raw_text}\n\n"
        "Respond again with ONLY valid JSON, no other text, no markdown fences."
    )
    parsed, raw_text, error = _attempt(tracker, category, repair_prompt, system, model, max_tokens)
    if parsed is not None:
        return parsed

    raise LLMCallError(f"Still not valid JSON after one retry: {error}\nRaw: {raw_text[:500]}")


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
) -> tuple[Optional[dict], str, Optional[str]]:
    response = _generate_with_transient_retry(prompt, model=model, system=system, max_tokens=max_tokens)
    tracker.record(category, response)
    raw_text = response.get("text", "")
    _log_prompt(category, prompt, system, raw_text)
    try:
        return _extract_json(raw_text), raw_text, None
    except (json.JSONDecodeError, ValueError) as exc:
        return None, raw_text, str(exc)


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        text = text[first_newline + 1 :] if first_newline != -1 else text
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        salvaged = _salvage_truncated_array(text)
        if salvaged is not None:
            return salvaged
        raise exc


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
