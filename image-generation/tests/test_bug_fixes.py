"""
TDD Red Phase — Bug-fix regression tests.

These tests document two confirmed bugs and MUST FAIL against the current
code in generate.py, proving the bugs exist.

Issue #1: generate_with_retry() mutates caller's args.steps
    On OOM retry, line 294 does `args.steps = max(1, args.steps // 2)`,
    modifying the caller's object in-place.  After the function returns
    (success or exhausted), the caller sees a different .steps than they set.

Issue #4: batch_generate() ignores CLI params
    batch_generate() hardcodes steps=40, guidance=7.5, width=1024, height=1024
    in a SimpleNamespace (lines 245-248).  CLI flags are never forwarded.
    It also calls generate() directly instead of generate_with_retry().

Mocking strategy: patch generate.generate / generate.generate_with_retry.
No GPU required.
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from generate import OOMError, batch_generate, generate_with_retry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _args(steps=40, guidance=7.5, width=1024, height=1024):
    """Build a minimal SimpleNamespace for testing."""
    return SimpleNamespace(
        steps=steps,
        guidance=guidance,
        width=width,
        height=height,
        prompt="a tropical scene",
        output="outputs/test.png",
        seed=None,
        cpu=True,
        refine=False,
        negative_prompt="",
        refiner_guidance=5.0,
        scheduler="DPMSolverMultistepScheduler",
    )


def _oom():
    return OOMError("Out of GPU memory. Reduce steps with --steps.")


# ===========================================================================
# Issue #1: generate_with_retry() mutates caller's args.steps
# ===========================================================================

class TestRetryDoesNotMutateCallerArgs:
    """generate_with_retry must not modify the caller's args.steps."""

    def test_args_steps_unchanged_after_successful_retry(self):
        """
        Scenario: OOM on first attempt, success on second.
        Bug: args.steps is 20 after return (mutated from 40).
        Expected: args.steps remains 40.
        """
        args = _args(steps=40)
        original_steps = args.steps

        with patch("generate.generate") as mock_gen:
            mock_gen.side_effect = [_oom(), "outputs/test.png"]
            generate_with_retry(args, max_retries=2)

        assert args.steps == original_steps, (
            f"generate_with_retry mutated args.steps from {original_steps} to {args.steps}. "
            "The caller's args must not be modified."
        )

    def test_args_steps_unchanged_after_exhausted_retries(self):
        """
        Scenario: OOM on all attempts (retries exhausted).
        Bug: args.steps is 10 after OOMError (mutated 40 -> 20 -> 10).
        Expected: args.steps remains 40.
        """
        args = _args(steps=40)
        original_steps = args.steps

        with patch("generate.generate", side_effect=_oom()):
            with pytest.raises(OOMError):
                generate_with_retry(args, max_retries=2)

        assert args.steps == original_steps, (
            f"generate_with_retry mutated args.steps from {original_steps} to {args.steps}. "
            "The caller's args must not be modified even after exhausted retries."
        )


# ===========================================================================
# Issue #4: batch_generate() ignores CLI params
# ===========================================================================

class TestBatchRespectsCliParams:
    """batch_generate must forward CLI args (steps, guidance, width, height)."""

    def test_batch_respects_custom_steps(self):
        """
        Pass args with steps=20.  Verify generate receives steps=20.
        Bug: batch_generate() doesn't accept args; hardcodes steps=40.
        """
        prompts = [{"prompt": "test", "output": "out.png"}]
        cli_args = _args(steps=20)

        captured = []

        def capture(a, **kw):
            captured.append(SimpleNamespace(**vars(a)))
            return a.output

        with patch("generate.generate_with_retry", side_effect=capture):
            batch_generate(prompts, device="cpu", args=cli_args)

        assert captured[0].steps == 20, (
            f"Expected steps=20 from CLI args, got steps={captured[0].steps}. "
            "batch_generate() is ignoring --steps."
        )

    def test_batch_respects_custom_guidance(self):
        """
        Pass args with guidance=5.0.  Verify generate receives guidance=5.0.
        Bug: batch_generate() hardcodes guidance=7.5.
        """
        prompts = [{"prompt": "test", "output": "out.png"}]
        cli_args = _args(guidance=5.0)

        captured = []

        def capture(a, **kw):
            captured.append(SimpleNamespace(**vars(a)))
            return a.output

        with patch("generate.generate_with_retry", side_effect=capture):
            batch_generate(prompts, device="cpu", args=cli_args)

        assert captured[0].guidance == 5.0, (
            f"Expected guidance=5.0 from CLI args, got guidance={captured[0].guidance}. "
            "batch_generate() is ignoring --guidance."
        )

    def test_batch_respects_custom_dimensions(self):
        """
        Pass args with width=512, height=768.  Verify generate receives those.
        Bug: batch_generate() hardcodes width=1024, height=1024.
        """
        prompts = [{"prompt": "test", "output": "out.png"}]
        cli_args = _args(width=512, height=768)

        captured = []

        def capture(a, **kw):
            captured.append(SimpleNamespace(**vars(a)))
            return a.output

        with patch("generate.generate_with_retry", side_effect=capture):
            batch_generate(prompts, device="cpu", args=cli_args)

        assert captured[0].width == 512, (
            f"Expected width=512, got width={captured[0].width}"
        )
        assert captured[0].height == 768, (
            f"Expected height=768, got height={captured[0].height}"
        )

    def test_batch_forwards_all_cli_params_together(self):
        """
        All four params (steps, guidance, width, height) must be forwarded.
        Bug: all four are hardcoded in SimpleNamespace.
        """
        prompts = [{"prompt": "test", "output": "out.png"}]
        cli_args = _args(steps=15, guidance=3.0, width=768, height=512)

        captured = []

        def capture(a, **kw):
            captured.append(SimpleNamespace(**vars(a)))
            return a.output

        with patch("generate.generate_with_retry", side_effect=capture):
            batch_generate(prompts, device="cpu", args=cli_args)

        a = captured[0]
        assert (a.steps, a.guidance, a.width, a.height) == (15, 3.0, 768, 512), (
            f"Expected (15, 3.0, 768, 512) but got ({a.steps}, {a.guidance}, {a.width}, {a.height}). "
            "batch_generate() ignores CLI params."
        )


class TestBatchUsesRetryWrapper:
    """batch_generate must use generate_with_retry, not generate directly."""

    def test_batch_calls_generate_with_retry(self):
        """
        Bug: batch_generate() calls generate() directly (line 253).
        Expected: should call generate_with_retry() for OOM resilience.
        """
        prompts = [{"prompt": "test", "output": "out.png"}]

        with patch("generate.generate_with_retry", return_value="out.png") as mock_retry, \
             patch("generate.generate", return_value="out.png"):
            batch_generate(prompts, device="cpu")

        assert mock_retry.call_count >= 1, (
            "batch_generate must call generate_with_retry(), not generate() directly"
        )

    def test_batch_does_not_call_generate_directly(self):
        """
        Complementary check: generate() must NOT be called by batch_generate.
        (It should only be called indirectly via generate_with_retry.)
        """
        prompts = [{"prompt": "test", "output": "out.png"}]

        with patch("generate.generate_with_retry", return_value="out.png"), \
             patch("generate.generate", return_value="out.png") as mock_gen:
            batch_generate(prompts, device="cpu")

        assert mock_gen.call_count == 0, (
            f"batch_generate called generate() directly {mock_gen.call_count} time(s). "
            "It should delegate to generate_with_retry() instead."
        )
