"""Regression tests for the summary_quote validation fix (FINDINGS.md): the
old omission-exclusion heuristic was found to be the ONLY mechanism actually
in use for the entire committed controlled benchmark (0% of real claims had
a summary_quote), and it demonstrably misclassified a genuine major-
materiality unsupported claim as an omission because its `reason` field
happened to contain "does not state". The real fix is structural: every
claim must carry a non-empty summary_quote that's an actual substring of
the summary, enforced by evalkit/judge/schemas.py with a mandatory repair
retry in evalkit/judge/faithfulness_coverage.py -- never a heuristic over
`reason` text. No live API calls -- call_json is monkeypatched throughout.
"""

from __future__ import annotations

import pytest

import evalkit.judge.faithfulness_coverage as fc
from evalkit.budget import BudgetTracker
from evalkit.judge.schemas import SchemaError, validate_faithfulness_coverage_output

SUMMARY = "Patient was discharged home in stable condition after treatment."

VALID_RESULT = {
    "claims": [
        {"claim_id": "c1", "text": "discharged home", "status": "supported", "materiality": "minor",
         "summary_quote": "discharged home in stable condition"},
    ],
    "fact_coverage": [],
    "usefulness": {"concision": 4},
}


def test_valid_result_with_real_quote_passes():
    validate_faithfulness_coverage_output(VALID_RESULT, SUMMARY)  # must not raise


def test_missing_summary_quote_fails_validation():
    result = {
        "claims": [{"claim_id": "c1", "text": "x", "status": "supported", "materiality": "minor"}],
        "fact_coverage": [], "usefulness": {},
    }
    with pytest.raises(SchemaError, match="summary_quote"):
        validate_faithfulness_coverage_output(result, SUMMARY)


def test_empty_summary_quote_fails_validation():
    result = {
        "claims": [{"claim_id": "c1", "text": "x", "status": "supported", "materiality": "minor", "summary_quote": "   "}],
        "fact_coverage": [], "usefulness": {},
    }
    with pytest.raises(SchemaError, match="summary_quote"):
        validate_faithfulness_coverage_output(result, SUMMARY)


def test_hallucinated_summary_quote_fails_validation():
    """The quote must be a REAL substring, not just non-empty."""
    result = {
        "claims": [{"claim_id": "c1", "text": "x", "status": "unsupported", "materiality": "major",
                    "summary_quote": "underwent emergency amputation surgery"}],
        "fact_coverage": [], "usefulness": {},
    }
    with pytest.raises(SchemaError, match="not an actual substring"):
        validate_faithfulness_coverage_output(result, SUMMARY)


def test_a_reason_containing_does_not_state_does_not_discard_a_genuine_claim_when_quote_is_valid():
    """Regression: the exact adversarial case found in real committed data --
    a genuine unsupported factual assertion whose `reason` field contains
    "does not state" must NOT be excluded, as long as it has a real,
    valid summary_quote. Schema validation (this function) is the gate now,
    not a text search over `reason`."""
    result = {
        "claims": [{
            "claim_id": "c1",
            "text": "The rehabilitation delay was caused by insurer authorization.",
            "status": "unsupported", "materiality": "major",
            "reason": "The timeline does not state that the authorization issue caused the delay.",
            "summary_quote": "discharged home in stable condition",
        }],
        "fact_coverage": [], "usefulness": {},
    }
    validate_faithfulness_coverage_output(result, SUMMARY)  # must not raise -- quote is real and valid
    # And scoring must count it as a real, unsupported claim -- not silently excluded.
    from evalkit.scoring import score_faithfulness
    scored = score_faithfulness(result["claims"])
    assert scored["claim_count"] == 1
    assert scored["omission_shaped_claims_excluded"] == 0
    assert scored["composite"] < 1.0


def test_whitespace_normalization_is_the_only_slack_allowed():
    """A quote that matches after whitespace/case normalization is fine; one
    that's genuinely paraphrased is not."""
    result_ok = {
        "claims": [{"claim_id": "c1", "text": "x", "status": "supported", "materiality": "minor",
                    "summary_quote": "  Discharged   HOME  in stable condition  "}],
        "fact_coverage": [], "usefulness": {},
    }
    validate_faithfulness_coverage_output(result_ok, SUMMARY)  # must not raise

    result_paraphrased = {
        "claims": [{"claim_id": "c1", "text": "x", "status": "supported", "materiality": "minor",
                    "summary_quote": "sent home in a stable state"}],
        "fact_coverage": [], "usefulness": {},
    }
    with pytest.raises(SchemaError):
        validate_faithfulness_coverage_output(result_paraphrased, SUMMARY)


# --- judge_summary retry/failure behavior ---

def _call_json_returning(*results):
    it = iter(results)
    def fake(tracker, category, *, prompt, system, max_tokens):
        return next(it)
    return fake


def test_judge_summary_returns_directly_when_first_response_is_valid(monkeypatch):
    monkeypatch.setattr(fc, "call_json", _call_json_returning(VALID_RESULT))
    result = fc.judge_summary(
        tracker=BudgetTracker(), case_id="case-x", tool="A", run=1, summary_text=SUMMARY,
        timeline_events=[], material_facts=[],
    )
    assert result == VALID_RESULT


def test_judge_summary_retries_once_and_succeeds(monkeypatch):
    invalid = {"claims": [{"claim_id": "c1", "text": "x", "status": "supported", "materiality": "minor"}],
               "fact_coverage": [], "usefulness": {}}
    monkeypatch.setattr(fc, "call_json", _call_json_returning(invalid, VALID_RESULT))
    result = fc.judge_summary(
        tracker=BudgetTracker(), case_id="case-x", tool="A", run=1, summary_text=SUMMARY,
        timeline_events=[], material_facts=[],
    )
    assert result == VALID_RESULT


def test_judge_summary_raises_judge_output_invalid_when_still_broken_after_retry(monkeypatch):
    """Test 5 (reviewer spec): missing/invalid summary_quote causes judge
    validation failure/retry, and if STILL invalid, the result is marked
    invalid -- never silently scored from whatever's left."""
    invalid = {"claims": [{"claim_id": "c1", "text": "x", "status": "supported", "materiality": "minor"}],
               "fact_coverage": [], "usefulness": {}}
    monkeypatch.setattr(fc, "call_json", _call_json_returning(invalid, invalid))
    with pytest.raises(fc.JudgeOutputInvalid, match="case-x"):
        fc.judge_summary(
            tracker=BudgetTracker(), case_id="case-x", tool="A", run=1, summary_text=SUMMARY,
            timeline_events=[], material_facts=[],
        )


def test_a_run_with_invalid_judge_output_is_excluded_not_silently_scored(monkeypatch):
    """Test 6 (reviewer spec): quote validation cannot silently change the
    faithfulness denominator -- an invalid run must be excluded from
    aggregation entirely (visible as an explicit failure), never patched
    together from a partial/broken claims list."""
    import evalkit.report as report_mod
    from evalkit.budget import BudgetTracker

    class FakeCase:
        case_id = "case-x"
        def reference_timeline_path(self):
            from pathlib import Path
            return Path(__file__)  # never actually read, chronos_timeline.parse is mocked below

    class FakeRun:
        def __init__(self, run, summary):
            self.run, self.tool, self.case_id, self.summary, self.cost_usd = run, "A", "case-x", summary, 0.01

    monkeypatch.setattr(report_mod, "load_frozen", lambda case_id: {"material_facts": []})
    monkeypatch.setattr(report_mod.chronos_timeline, "parse", lambda text: [])
    monkeypatch.setattr(report_mod, "load_controlled_benchmark", lambda case: [FakeRun(1, "s1"), FakeRun(2, "s2")])
    monkeypatch.setattr(report_mod, "group_by_tool", lambda runs: {"A": runs})

    def fake_judge_summary(tracker, *, case_id, tool, run, summary_text, timeline_events, material_facts, **kw):
        if run == 1:
            raise fc.JudgeOutputInvalid("still invalid after repair retry")
        return VALID_RESULT
    monkeypatch.setattr(report_mod, "judge_summary", fake_judge_summary)
    monkeypatch.setattr(report_mod, "judge_stability", lambda *a, **k: {"claim_pairs": []})

    result = report_mod.run_controlled_benchmark_for_case(FakeCase(), BudgetTracker())
    tool_result = result["tools"]["A"]
    assert len(tool_result["invalid_runs"]) == 1
    assert tool_result["invalid_runs"][0]["run"] == 1
    assert len(tool_result["runs"]) == 1, "only the valid run should contribute to the scorecard"
