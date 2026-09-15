"""Everything about the platform that is fixed, in one place.

Standard library only — nothing to install, nothing to call. `GET /v1/models`
returns the same model list live if you would rather read it from the server.

Prices are USD per 1,000,000 tokens and are what you are actually charged, so
`estimate_usd()` below is the same arithmetic the platform bills you with. It
is an estimate only in that you cannot know the output length in advance.
"""

from typing import Final

# --------------------------------------------------------------- endpoints

BASE_URL_ENV: Final = "INTERVIEW_BASE_URL"
API_KEY_ENV: Final = "INTERVIEW_API_KEY"
API_KEY_HEADER: Final = "x-api-key"

GENERATE_PATH: Final = "/v1/generate"
SUMMARIZE_PATH: Final = "/v1/summarize/{tool}"
MODELS_PATH: Final = "/v1/models"
CASES_PATH: Final = "/v1/cases"
BUDGET_PATH: Final = "/v1/budget"

# Free, and they take no arguments.
FREE_PATHS: Final = (MODELS_PATH, CASES_PATH, BUDGET_PATH)

# --------------------------------------------------------------- the models

SONNET_5: Final = "us.anthropic.claude-sonnet-5"
HAIKU_4_5: Final = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

#: model id -> what you can rely on about it.
#:
#: `max_output_tokens` is the platform's ceiling on one call, not the model's
#: own limit — it exists so a single request cannot consume a whole budget.
MODELS: Final = {
    SONNET_5: {
        "label": "Claude Sonnet 5",
        "context_window": 1_000_000,
        "max_output_tokens": 16_000,
        "usd_per_1m_input": 2.20,
        "usd_per_1m_output": 11.00,
    },
    HAIKU_4_5: {
        "label": "Claude Haiku 4.5",
        "context_window": 200_000,
        "max_output_tokens": 8_192,
        "usd_per_1m_input": 1.00,
        "usd_per_1m_output": 5.00,
    },
}

MODEL_IDS: Final = tuple(MODELS)

#: Applied when a request omits `max_tokens`.
DEFAULT_MAX_OUTPUT_TOKENS: Final = 4_096

# --------------------------------------------------------------- the tools

#: The four summarisers. A letter does **not** mean the same thing from one case
#: to the next — whatever you conclude about one, you have concluded it for the
#: case you tested it on.
TOOLS: Final = ("A", "B", "C", "D")

# ------------------------------------------------------------ the timeline

#: The only event types accepted. Anything else is a validation error.
EVENT_TYPES: Final = (
    "encounter", "imaging", "medication", "procedure", "therapy", "diagnosis",
)

#: The only fields accepted on an event. An unexpected key is an error rather
#: than being ignored, so a typo fails loudly instead of dropping data.
EVENT_FIELDS: Final = ("date", "type", "detail", "source")

MAX_EVENTS: Final = 400
MAX_DETAIL_CHARS: Final = 600

# --------------------------------------------------------------- the limits

#: Request body ceiling, bytes.
MAX_REQUEST_BYTES: Final = 2_000_000

#: Error `type` values worth branching on. `budget_exhausted` and `rate_limited`
#: are the two that mean "wait or stop" rather than "fix the request".
ERROR_TYPES: Final = (
    "invalid_request",
    "not_found",
    "unauthorized",
    "budget_exhausted",
    "rate_limited",
    "payload_too_large",
    "upstream_error",
)


def estimate_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """What a call with those token counts costs.

    >>> round(estimate_usd(HAIKU_4_5, 100_000, 2_000), 4)
    0.11
    """
    row = MODELS[model]
    return (input_tokens * row["usd_per_1m_input"] / 1_000_000
            + output_tokens * row["usd_per_1m_output"] / 1_000_000)
