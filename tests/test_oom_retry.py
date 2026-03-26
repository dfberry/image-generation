"""
TDD Red Phase — OOM Retry Logic tests.

These tests are written BEFORE the implementation exists.
ALL tests in this file are expected to FAIL until Trinity adds
`generate_with_retry(args, max_retries=2)` to generate.py.

Feature contract under test:
    generate_with_retry(args, max_retries=2)
    - Calls generate(args) internally
    - On OOMError: halves args.steps and retries up to max_retries times
    - Total attempts = max_retries + 1
    - If all attempts raise OOMError, re-raises final OOMError
    - Final OOMError message includes the steps count used on last attempt
    - Non-OOM exceptions are NOT retried — raised immediately
    - Prints/logs a warning on each retry containing the new step count
    - steps never go below 1 (floor at 1)
    - Successful retry returns the result string from generate()

Mocking strategy:
    Patch `generate.generate` with side_effect to raise OOMError on
    the first N calls, then optionally succeed.
    No GPU required.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

import pytest

import generate as gen

# ---------------------------------------------------------------------------
# Import targets — expected to exist in generate.py after Trinity implements
# ---------------------------------------------------------------------------
try:
    from generate import OOMError
except ImportError:
    OOMError = None  # Tests will fail explicitly rather than crashing

try:
    from generate import generate_with_retry
except ImportError:
    generate_with_retry = None  # Tests will fail explicitly


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _args(steps=40):
    """Build a minimal SimpleNamespace args for generate_with_retry()."""
    return SimpleNamespace(
        steps=steps,
        prompt="a tropical scene",
        output="outputs/test.png",
        seed=None,
        cpu=True,
        refine=False,
        guidance=7.5,
        width=64,
        height=64,
        negative_prompt="",
        scheduler="DPMSolverMultistepScheduler",
        refiner_guidance=5.0,
    )


def _oom():
    """Return an OOMError instance (or RuntimeError if not yet defined)."""
    if OOMError is not None:
        return OOMError("Out of GPU memory. Reduce steps with --steps.")
    return RuntimeError("OOM sentinel")


# ---------------------------------------------------------------------------
# 1. Retry is attempted when OOMError raised on first call
# ---------------------------------------------------------------------------

class TestOomRetriesWithHalvedSteps:
    """generate_with_retry retries with halved steps after OOMError."""

    def test_oom_retries_with_halved_steps(self):
        assert generate_with_retry is not None, (
            "generate_with_retry not found in generate.py — Trinity must implement it"
        )
        args = _args(steps=40)
        oom = _oom()
        success_result = "outputs/test.png"

        with patch("generate.generate") as mock_gen:
            mock_gen.side_effect = [oom, success_result]
            generate_with_retry(args, max_retries=2)

        assert mock_gen.call_count == 2
        # Second call must have args.steps == 20
        second_call_args = mock_gen.call_args_list[1][0][0]
        assert second_call_args.steps == 20, (
            f"Expected steps=20 on retry, got {second_call_args.steps}"
        )


# ---------------------------------------------------------------------------
# 2. Successful retry returns the result
# ---------------------------------------------------------------------------

class TestOomRetrySucceedsOnSecondAttempt:
    """generate_with_retry returns result if second attempt succeeds."""

    def test_oom_retry_succeeds_on_second_attempt(self):
        assert generate_with_retry is not None, (
            "generate_with_retry not found in generate.py"
        )
        args = _args(steps=40)
        oom = _oom()
        expected = "outputs/success.png"

        with patch("generate.generate") as mock_gen:
            mock_gen.side_effect = [oom, expected]
            result = generate_with_retry(args, max_retries=2)

        assert result == expected, (
            f"Expected '{expected}' but got '{result}'"
        )


# ---------------------------------------------------------------------------
# 3. Steps halved each retry
# ---------------------------------------------------------------------------

class TestOomRetryHalvesStepsEachTime:
    """Steps go 40 → 20 → 10 across two retries."""

    def test_oom_retry_halves_steps_each_time(self):
        assert generate_with_retry is not None, (
            "generate_with_retry not found in generate.py"
        )
        args = _args(steps=40)
        oom = _oom()

        recorded_steps = []

        def capturing_generate(a):
            recorded_steps.append(a.steps)
            raise oom

        with patch("generate.generate", side_effect=capturing_generate):
            with pytest.raises(Exception):
                generate_with_retry(args, max_retries=2)

        assert recorded_steps == [40, 20, 10], (
            f"Expected steps sequence [40, 20, 10], got {recorded_steps}"
        )


# ---------------------------------------------------------------------------
# 4. All retries exhausted → OOMError raised
# ---------------------------------------------------------------------------

class TestOomRetryExhaustedRaisesOomError:
    """After max_retries all fail, OOMError is raised."""

    def test_oom_retry_exhausted_raises_oom_error(self):
        assert generate_with_retry is not None, (
            "generate_with_retry not found in generate.py"
        )
        assert OOMError is not None, (
            "OOMError not found in generate.py"
        )
        args = _args(steps=40)
        oom = _oom()

        with patch("generate.generate", side_effect=oom):
            with pytest.raises(OOMError):
                generate_with_retry(args, max_retries=2)


# ---------------------------------------------------------------------------
# 5. Final OOMError message mentions steps count
# ---------------------------------------------------------------------------

class TestOomRetryExhaustedMessageIncludesSteps:
    """Final OOMError message includes the steps count from the last attempt."""

    def test_oom_retry_exhausted_message_includes_steps(self):
        assert generate_with_retry is not None, (
            "generate_with_retry not found in generate.py"
        )
        assert OOMError is not None, (
            "OOMError not found in generate.py"
        )
        args = _args(steps=40)
        oom = _oom()

        with patch("generate.generate", side_effect=oom):
            with pytest.raises(OOMError) as exc_info:
                generate_with_retry(args, max_retries=2)

        # After 2 retries from 40: 40→20→10, last attempt uses 10 steps
        error_msg = str(exc_info.value)
        assert "10" in error_msg, (
            f"Expected final OOMError message to contain '10' (last steps), got: '{error_msg}'"
        )


# ---------------------------------------------------------------------------
# 6. Non-OOM errors are NOT retried
# ---------------------------------------------------------------------------

class TestNonOomErrorNotRetried:
    """Non-OOM RuntimeError is raised immediately without retry."""

    def test_non_oom_error_not_retried(self):
        assert generate_with_retry is not None, (
            "generate_with_retry not found in generate.py"
        )
        args = _args(steps=40)
        non_oom = RuntimeError("Something else went wrong (not OOM)")

        with patch("generate.generate", side_effect=non_oom) as mock_gen:
            with pytest.raises(RuntimeError, match="Something else went wrong"):
                generate_with_retry(args, max_retries=2)

        assert mock_gen.call_count == 1, (
            f"Non-OOM error should not retry; generate called {mock_gen.call_count} times"
        )


# ---------------------------------------------------------------------------
# 7. Default retry count is 2 (3 total attempts)
# ---------------------------------------------------------------------------

class TestOomDefaultRetryCountIs2:
    """Default max_retries=2 means 3 total calls before giving up."""

    def test_oom_default_retry_count_is_2(self):
        assert generate_with_retry is not None, (
            "generate_with_retry not found in generate.py"
        )
        args = _args(steps=40)
        oom = _oom()

        with patch("generate.generate", side_effect=oom) as mock_gen:
            with pytest.raises(Exception):
                generate_with_retry(args)  # no max_retries arg — uses default

        assert mock_gen.call_count == 3, (
            f"Default should make 3 total attempts (1 + 2 retries), got {mock_gen.call_count}"
        )


# ---------------------------------------------------------------------------
# 8. Warning printed on each retry
# ---------------------------------------------------------------------------

class TestOomRetryPrintsWarning:
    """A warning is printed on each retry containing the new step count."""

    def test_oom_retry_prints_warning(self, capsys):
        assert generate_with_retry is not None, (
            "generate_with_retry not found in generate.py"
        )
        args = _args(steps=40)
        oom = _oom()
        success_result = "outputs/test.png"

        with patch("generate.generate") as mock_gen:
            mock_gen.side_effect = [oom, success_result]
            generate_with_retry(args, max_retries=2)

        captured = capsys.readouterr()
        output = captured.out + captured.err

        assert "20" in output, (
            f"Expected retry warning to mention new steps (20) in stdout/stderr, got: '{output}'"
        )


# ---------------------------------------------------------------------------
# 9. Steps floor at 1 — halving never produces 0
# ---------------------------------------------------------------------------

class TestOomStepsFloorAt1:
    """Steps never go below 1 even when halving from 1."""

    def test_oom_steps_floor_at_1(self):
        assert generate_with_retry is not None, (
            "generate_with_retry not found in generate.py"
        )
        args = _args(steps=1)
        oom = _oom()

        recorded_steps = []

        def capturing_generate(a):
            recorded_steps.append(a.steps)
            raise oom

        with patch("generate.generate", side_effect=capturing_generate):
            with pytest.raises(Exception):
                generate_with_retry(args, max_retries=2)

        assert all(s >= 1 for s in recorded_steps), (
            f"Steps went below 1: {recorded_steps}"
        )
        assert recorded_steps[-1] == 1, (
            f"Final steps should be 1 (floor), got {recorded_steps[-1]}"
        )


# ---------------------------------------------------------------------------
# 10. Other exception types (ValueError, KeyError) are not retried
# ---------------------------------------------------------------------------

class TestOomRetryDoesNotAffectNonOomExceptionTypes:
    """ValueError, KeyError, TypeError are raised immediately without retry."""

    @pytest.mark.parametrize("exc", [
        ValueError("bad value"),
        KeyError("missing key"),
        TypeError("wrong type"),
    ])
    def test_oom_retry_does_not_affect_non_oom_exception_types(self, exc):
        assert generate_with_retry is not None, (
            "generate_with_retry not found in generate.py"
        )
        args = _args(steps=40)

        with patch("generate.generate", side_effect=exc) as mock_gen:
            with pytest.raises(type(exc)):
                generate_with_retry(args, max_retries=2)

        assert mock_gen.call_count == 1, (
            f"{type(exc).__name__} should not be retried; generate called {mock_gen.call_count} times"
        )
