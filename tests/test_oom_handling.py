"""
TDD Red Phase — OOM Handling tests.

These tests are written BEFORE the implementation exists.
ALL tests in this file are expected to FAIL until Trinity adds graceful
OOM error handling inside generate() in generate.py.

Feature contract under test:
    - generate() wraps torch OOM errors as OOMError (or a RuntimeError with OOM message)
    - The finally block still executes on OOM (cleanup is guaranteed)
    - The OOMError message includes actionable guidance
    - MPS RuntimeError("out of memory") is treated identically to CUDA OOM
    - After an OOM, the next generate() call succeeds (no dirty state)

If Trinity introduces a custom OOMError class, it should be importable:
    from generate import OOMError

Mocking strategy: patch torch pipeline loading to raise OOM at the right moment.
No GPU required.
"""

import gc
from unittest.mock import MagicMock, call, patch

import pytest
import torch

import generate as gen

# ---------------------------------------------------------------------------
# Import OOMError — expected to be defined in generate.py.
# Falls back to None so tests fail with a clear message rather than ImportError.
# ---------------------------------------------------------------------------
try:
    from generate import OOMError
except ImportError:
    OOMError = None  # Tests will fail explicitly when they try to use this


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_args(tmp_path, refine=False, cpu=False):
    """Build a minimal args namespace for generate()."""
    args = MagicMock()
    args.refine = refine
    args.cpu = cpu
    args.seed = None
    args.output = str(tmp_path / "out.png")
    args.prompt = "a tropical scene"
    args.steps = 2
    args.guidance = 7.5
    args.width = 64
    args.height = 64
    args.negative_prompt = ""
    args.scheduler = "DPMSolverMultistepScheduler"
    args.refiner_guidance = 5.0
    args.lora = None
    args.lora_weight = 0.8
    args.refiner_steps = 10
    return args


def _make_cuda_oom():
    """Construct a torch.cuda.OutOfMemoryError (or RuntimeError fallback)."""
    try:
        # torch >= 2.1 exposes OutOfMemoryError directly
        return torch.cuda.OutOfMemoryError("CUDA out of memory. Tried to allocate 2.00 GiB")
    except AttributeError:
        return RuntimeError("CUDA out of memory. Tried to allocate 2.00 GiB")


def _make_mps_oom():
    """MPS OOM surfaces as RuntimeError with 'out of memory' in the message."""
    return RuntimeError("MPS backend out of memory (MPS allocated: 8.00 GB)")


# ---------------------------------------------------------------------------
# Test 1 — CUDA OOM is re-raised as OOMError / clear RuntimeError
# ---------------------------------------------------------------------------

class TestCudaOOMReraise:
    """CUDA OutOfMemoryError must be caught and re-raised as OOMError."""

    def test_cuda_oom_raises_oom_error(self, tmp_path):
        """torch.cuda.OutOfMemoryError during pipeline loading → OOMError raised."""
        args = _base_args(tmp_path)

        with patch("generate.load_base", side_effect=_make_cuda_oom()), \
             patch("generate.gc"), \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.cuda.is_available", return_value=False), \
             patch("generate.torch.backends.mps.is_available", return_value=False):

            # Must raise OOMError (custom) or RuntimeError with OOM message
            # If OOMError is not defined yet, this test fails (expected in red phase)
            if OOMError is not None:
                with pytest.raises(OOMError):
                    gen.generate(args)
            else:
                pytest.fail(
                    "OOMError not importable from generate.py — Trinity must implement it"
                )

    def test_cuda_oom_not_silently_swallowed(self, tmp_path):
        """generate() must NOT silently return None/empty when OOM occurs."""
        args = _base_args(tmp_path)

        with patch("generate.load_base", side_effect=_make_cuda_oom()), \
             patch("generate.gc"), \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.cuda.is_available", return_value=False), \
             patch("generate.torch.backends.mps.is_available", return_value=False):

            raised = False
            try:
                gen.generate(args)
            except Exception as exc:
                raised = True
                # Must be OOMError or a RuntimeError with OOM content, not the raw torch error
                if OOMError is not None:
                    assert isinstance(exc, OOMError), (
                        f"Expected OOMError, got {type(exc).__name__}: {exc}"
                    )
                else:
                    assert "out of memory" in str(exc).lower() or "oom" in str(exc).lower(), (
                        "Exception message must reference OOM condition"
                    )

            assert raised, "generate() must raise on OOM — silent return is not acceptable"

    def test_cuda_oom_during_inference_raises_oom_error(self, tmp_path):
        """OOM during base() inference call → OOMError raised."""
        args = _base_args(tmp_path)

        base = MagicMock()
        base.side_effect = _make_cuda_oom()

        with patch("generate.load_base", return_value=base), \
             patch("generate.gc"), \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.cuda.is_available", return_value=False), \
             patch("generate.torch.backends.mps.is_available", return_value=False):

            if OOMError is not None:
                with pytest.raises(OOMError):
                    gen.generate(args)
            else:
                pytest.fail("OOMError not importable from generate.py")


# ---------------------------------------------------------------------------
# Test 2 — finally block still runs on OOM (cleanup is guaranteed)
# ---------------------------------------------------------------------------

class TestOOMCleanupStillRuns:
    """The finally block must execute even when OOM is raised."""

    def test_gc_collect_runs_after_cuda_oom(self, tmp_path):
        """gc.collect() must fire in finally even when CUDA OOM is raised."""
        args = _base_args(tmp_path)

        with patch("generate.load_base", side_effect=_make_cuda_oom()), \
             patch("generate.gc") as mock_gc, \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.cuda.is_available", return_value=False), \
             patch("generate.torch.backends.mps.is_available", return_value=False):

            try:
                gen.generate(args)
            except Exception:
                pass  # OOMError expected; we care about side effects

        assert mock_gc.collect.called, (
            "gc.collect() must run in the finally block even when OOM is raised"
        )

    def test_cuda_empty_cache_runs_after_cuda_oom(self, tmp_path):
        """torch.cuda.empty_cache() must fire in finally even on OOM."""
        args = _base_args(tmp_path)

        with patch("generate.load_base", side_effect=_make_cuda_oom()), \
             patch("generate.gc"), \
             patch("generate.torch.cuda.empty_cache") as mock_cuda_cache, \
             patch("generate.torch.cuda.is_available", return_value=False), \
             patch("generate.torch.backends.mps.is_available", return_value=False):

            try:
                gen.generate(args)
            except Exception:
                pass

        assert mock_cuda_cache.called, (
            "torch.cuda.empty_cache() must run in finally even when OOM occurs"
        )

    def test_mps_empty_cache_runs_after_oom_when_available(self, tmp_path):
        """torch.mps.empty_cache() must fire in finally when MPS is available."""
        args = _base_args(tmp_path)

        with patch("generate.load_base", side_effect=_make_mps_oom()), \
             patch("generate.gc"), \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.mps.empty_cache") as mock_mps_cache, \
             patch("generate.torch.cuda.is_available", return_value=False), \
             patch("generate.torch.backends.mps.is_available", return_value=True):

            try:
                gen.generate(args)
            except Exception:
                pass

        assert mock_mps_cache.called, (
            "torch.mps.empty_cache() must run in finally even when MPS OOM occurs"
        )


# ---------------------------------------------------------------------------
# Test 3 — OOMError message includes actionable guidance
# ---------------------------------------------------------------------------

class TestOOMErrorMessage:
    """The OOMError message must give the user something to do."""

    GUIDANCE_HINTS = ["--steps", "--cpu", "gpu", "memory", "close"]

    def _get_oom_message(self, tmp_path):
        """Helper: trigger OOM and return the exception message."""
        args = _base_args(tmp_path)

        with patch("generate.load_base", side_effect=_make_cuda_oom()), \
             patch("generate.gc"), \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.cuda.is_available", return_value=False), \
             patch("generate.torch.backends.mps.is_available", return_value=False):

            try:
                gen.generate(args)
            except Exception as exc:
                return str(exc)

        return ""  # Should not reach here

    def test_oom_message_is_not_empty(self, tmp_path):
        """OOMError must have a non-empty message."""
        msg = self._get_oom_message(tmp_path)
        assert msg.strip(), "OOMError message must not be empty"

    def test_oom_message_contains_actionable_hint(self, tmp_path):
        """OOMError message must contain at least one actionable hint."""
        if OOMError is None:
            pytest.fail("OOMError not importable — implement it first")

        msg = self._get_oom_message(tmp_path).lower()
        assert any(hint in msg for hint in self.GUIDANCE_HINTS), (
            f"OOMError message must include one of {self.GUIDANCE_HINTS} "
            f"to guide the user. Got: {msg!r}"
        )

    def test_oom_message_mentions_steps_or_cpu_flag(self, tmp_path):
        """OOMError must specifically mention --steps or --cpu as a remedy."""
        if OOMError is None:
            pytest.fail("OOMError not importable — implement it first")

        msg = self._get_oom_message(tmp_path).lower()
        assert "--steps" in msg or "--cpu" in msg, (
            "OOMError message must mention --steps or --cpu as actionable flags"
        )


# ---------------------------------------------------------------------------
# Test 4 — MPS RuntimeError("out of memory") triggers same re-raise behavior
# ---------------------------------------------------------------------------

class TestMPSOOMHandling:
    """MPS OOM (RuntimeError with 'out of memory') must get the same treatment."""

    def test_mps_oom_raises_oom_error_not_raw_runtime_error(self, tmp_path):
        """MPS RuntimeError('out of memory') → re-raised as OOMError."""
        args = _base_args(tmp_path)

        with patch("generate.load_base", side_effect=_make_mps_oom()), \
             patch("generate.gc"), \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.cuda.is_available", return_value=False), \
             patch("generate.torch.backends.mps.is_available", return_value=False):

            if OOMError is not None:
                with pytest.raises(OOMError):
                    gen.generate(args)
            else:
                pytest.fail("OOMError not importable from generate.py")

    def test_mps_oom_not_silently_swallowed(self, tmp_path):
        """MPS OOM must raise — not return silently."""
        args = _base_args(tmp_path)

        with patch("generate.load_base", side_effect=_make_mps_oom()), \
             patch("generate.gc"), \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.cuda.is_available", return_value=False), \
             patch("generate.torch.backends.mps.is_available", return_value=False):

            raised = False
            try:
                gen.generate(args)
            except Exception as exc:
                raised = True
                msg = str(exc).lower()
                assert "out of memory" in msg or "oom" in msg or (
                    OOMError is not None and isinstance(exc, OOMError)
                ), f"Unexpected exception on MPS OOM: {type(exc).__name__}: {exc}"

            assert raised, "MPS OOM must raise — not silently return"

    def test_mps_oom_cleanup_still_runs(self, tmp_path):
        """gc.collect() fires in finally even on MPS OOM."""
        args = _base_args(tmp_path)

        with patch("generate.load_base", side_effect=_make_mps_oom()), \
             patch("generate.gc") as mock_gc, \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.cuda.is_available", return_value=False), \
             patch("generate.torch.backends.mps.is_available", return_value=False):

            try:
                gen.generate(args)
            except Exception:
                pass

        assert mock_gc.collect.called, (
            "gc.collect() must run in finally even when MPS OOM is raised"
        )


# ---------------------------------------------------------------------------
# Test 5 — After OOM, calling generate() again succeeds (state is clean)
# ---------------------------------------------------------------------------

class TestStateCleanAfterOOM:
    """The finally block must leave the process in a clean state for the next call."""

    def test_second_call_succeeds_after_oom(self, tmp_path):
        """
        First call raises OOM; second call (with working pipeline) must succeed.
        This validates that the finally block cleaned up all state and no
        dirty global references prevent a subsequent call.
        """
        from tests.conftest import MockPipeline

        args_oom     = _base_args(tmp_path / "first")
        args_success = _base_args(tmp_path / "second")
        (tmp_path / "first").mkdir()
        (tmp_path / "second").mkdir()

        good_pipeline = MockPipeline(return_latents=False)

        call_count = {"n": 0}

        def load_base_sequence(device):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise _make_cuda_oom()
            return good_pipeline

        with patch("generate.load_base", side_effect=load_base_sequence), \
             patch("generate.gc"), \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.cuda.is_available", return_value=False), \
             patch("generate.torch.backends.mps.is_available", return_value=False):

            # First call — expect OOM
            try:
                gen.generate(args_oom)
            except Exception:
                pass  # Expected

            # Second call — must succeed without any leftover dirty state
            result = gen.generate(args_success)

        assert result == args_success.output, (
            "Second generate() call must succeed after a previous OOM was handled cleanly"
        )

    def test_no_pipeline_leak_after_oom(self, tmp_path):
        """
        After OOM, there must be no pipeline reference surviving in generate()'s scope.
        We verify this indirectly: load_base is called fresh on the second invocation
        (not reused from a leaked closure or module-global).
        """
        from tests.conftest import MockPipeline

        good_pipeline = MockPipeline(return_latents=False)
        load_calls = []

        def track_load(device):
            load_calls.append(device)
            if len(load_calls) == 1:
                raise _make_cuda_oom()
            return good_pipeline

        args1 = _base_args(tmp_path / "a")
        args2 = _base_args(tmp_path / "b")
        (tmp_path / "a").mkdir()
        (tmp_path / "b").mkdir()

        with patch("generate.load_base", side_effect=track_load), \
             patch("generate.gc"), \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.cuda.is_available", return_value=False), \
             patch("generate.torch.backends.mps.is_available", return_value=False):

            try:
                gen.generate(args1)
            except Exception:
                pass

            gen.generate(args2)

        assert len(load_calls) == 2, (
            "load_base must be called again on the second generate() call — "
            "no cached pipeline must survive OOM cleanup"
        )
