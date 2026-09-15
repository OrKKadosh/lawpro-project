"""Thin client for the two platform endpoints.

Everything you build talks to the model through here. Both endpoints are
metered against one shared budget; `budget` on every response tells you where
you are.
"""

import json
import os
import pathlib
import urllib.error
import urllib.request
from typing import Any, Optional


def _from_env_file() -> dict:
    """`.env` next to this package, if there is one.

    The endpoint and your key ship in `.env`, so nothing has to be exported to
    get started. A real environment variable wins over the file, so you can
    point a shell at something else without editing it.
    """
    path = pathlib.Path(__file__).resolve().parents[1] / ".env"
    if not path.is_file():
        return {}
    values = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


_FILE = _from_env_file()

BASE_URL = (os.environ.get("INTERVIEW_BASE_URL")
            or _FILE.get("INTERVIEW_BASE_URL", "")).rstrip("/")
API_KEY = os.environ.get("INTERVIEW_API_KEY") or _FILE.get("INTERVIEW_API_KEY", "")

TIMEOUT_SECONDS = 300


class PlatformError(RuntimeError):
    """A structured error from the platform. `type` is stable; branch on it."""

    def __init__(self, status: int, payload: dict):
        self.status = status
        self.payload = payload
        err = payload.get("error", {})
        self.type = err.get("type", "unknown")
        self.detail = err.get("detail", {})
        super().__init__(f"[{status} {self.type}] {err.get('message', payload)}")


def _request(method: str, path: str, body: Optional[dict] = None) -> dict:
    if not BASE_URL or not API_KEY:
        raise RuntimeError(
            "No endpoint or key. They ship in .env at the root of this package; "
            "run from there, or export INTERVIEW_BASE_URL and INTERVIEW_API_KEY "
            "(see CREDENTIALS.md)."
        )
    req = urllib.request.Request(
        BASE_URL + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"content-type": "application/json", "x-api-key": API_KEY},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            raise PlatformError(exc.code, json.loads(raw)) from None
        except json.JSONDecodeError:
            raise RuntimeError(f"HTTP {exc.code}: {raw[:400]}") from None


def models() -> dict:
    """Available models, their limits, and what they cost you."""
    return _request("GET", "/v1/models")


def cases() -> dict:
    """Case ids you can summarise."""
    return _request("GET", "/v1/cases")


def budget() -> dict:
    return _request("GET", "/v1/budget")


def generate(
    prompt: str,
    *,
    model: str = "us.anthropic.claude-haiku-4-5-20251001-v1:0",
    system: Optional[str] = None,
    max_tokens: int = 4096,
) -> dict:
    """One model call. Returns text, usage, cost_usd and your budget.

    The parameter surface is the same for every model — there are no sampling
    parameters to set.
    """
    body: dict[str, Any] = {"model": model, "prompt": prompt, "max_tokens": max_tokens}
    if system is not None:
        body["system"] = system
    return _request("POST", "/v1/generate", body)


def summarize(tool: str, *, case_id: str, timeline: list[dict]) -> dict:
    """Ask one summarisation tool for a summary.

    Your timeline is the only input. The tool has no access to the source
    documents; `case_id` labels the run and is checked against the case list,
    nothing more. What comes back is the summary and what it cost — not the
    model, not the token counts.

    A letter does not mean the same thing on every case.
    """
    return _request(
        "POST", f"/v1/summarize/{tool}", {"case_id": case_id, "timeline": timeline}
    )
