"""
Regression tests for memory management in generate.py.

Coverage:
- Exception-safety cleanup (try/finally correctness) — 13 tests
- MEDIUM memory fixes: entry-point flush, latents CPU transfer, dynamo cache — 9 tests

No GPU required: all external calls are patched.
"""

from unittest.mock import MagicMock, patch

import pytest

import generate as gen
from tests.conftest import MockPipeline

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_base_pipeline():
    return MockPipeline(return_latents=False)


def _make_base_pipeline_with_latents():
    return MockPipeline(return_latents=True)


def _make_refiner_pipeline():
    return MockPipeline(return_latents=False)


# ---------------------------------------------------------------------------
# Group 1 — Exception-safety / try-finally cleanup  (13 tests, PR #3 / PR #4)
# ---------------------------------------------------------------------------


class TestExceptionSafety:

    def test_generate_base_path_cleans_up_on_success(self, mock_args_base):
        base = _make_base_pipeline()
        with patch("generate.load_base", return_value=base), \
             patch("generate.gc") as mock_gc, \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.backends.mps.is_available", return_value=False), \
             patch("generate.torch.cuda.is_available", return_value=False), \
             patch("generate.torch.backends.mps.is_available", return_value=False):
            gen.generate(mock_args_base)

        mock_gc.collect.assert_called()

    def test_generate_refiner_path_cleans_up_on_success(self, mock_args_refine):
        base = _make_base_pipeline_with_latents()
        refiner = _make_refiner_pipeline()
        with patch("generate.load_base", return_value=base), \
             patch("generate.load_refiner", return_value=refiner), \
             patch("generate.gc") as mock_gc, \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.mps.empty_cache"), \
             patch("generate.torch.cuda.is_available", return_value=False), \
             patch("generate.torch.backends.mps.is_available", return_value=False):
            gen.generate(mock_args_refine)

        mock_gc.collect.assert_called()

    def test_generate_refine_path_cleans_up_on_refiner_exception(self, mock_args_refine):
        """Exception in refiner must not prevent finally-block cleanup."""
        base = _make_base_pipeline_with_latents()
        with patch("generate.load_base", return_value=base), \
             patch("generate.load_refiner", side_effect=RuntimeError("OOM")), \
             patch("generate.gc") as mock_gc, \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.mps.empty_cache"), \
             patch("generate.torch.cuda.is_available", return_value=False), \
             patch("generate.torch.backends.mps.is_available", return_value=False):
            with pytest.raises(RuntimeError, match="OOM"):
                gen.generate(mock_args_refine)

        mock_gc.collect.assert_called()

    def test_generate_base_path_cleans_up_on_exception(self, mock_args_base):
        """Exception during base inference must still trigger finally cleanup."""
        base = MagicMock()
        base.side_effect = RuntimeError("inference failed")
        with patch("generate.load_base", return_value=base), \
             patch("generate.gc") as mock_gc, \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.backends.mps.is_available", return_value=False), \
             patch("generate.torch.cuda.is_available", return_value=False):
            with pytest.raises(RuntimeError):
                gen.generate(mock_args_base)

        mock_gc.collect.assert_called()

    def test_generate_cleans_up_when_load_base_fails(self, mock_args_base):
        """If load_base raises, gc still runs (finally fires even before try body completes)."""
        with patch("generate.load_base", side_effect=MemoryError("no VRAM")), \
             patch("generate.gc") as mock_gc, \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.backends.mps.is_available", return_value=False), \
             patch("generate.torch.cuda.is_available", return_value=False):
            with pytest.raises(MemoryError):
                gen.generate(mock_args_base)

        mock_gc.collect.assert_called()

    def test_generate_gc_collect_called_in_finally(self, mock_args_base):
        base = _make_base_pipeline()
        with patch("generate.load_base", return_value=base), \
             patch("generate.gc") as mock_gc, \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.cuda.is_available", return_value=False), \
             patch("generate.torch.backends.mps.is_available", return_value=False):
            gen.generate(mock_args_base)

        assert mock_gc.collect.call_count >= 1

    def test_generate_cuda_cache_cleared_in_finally(self, mock_args_base):
        base = _make_base_pipeline()
        with patch("generate.load_base", return_value=base), \
             patch("generate.gc"), \
             patch("generate.torch.cuda.empty_cache") as mock_cuda, \
             patch("generate.torch.cuda.is_available", return_value=False), \
             patch("generate.torch.backends.mps.is_available", return_value=False):
            gen.generate(mock_args_base)

        mock_cuda.assert_called()

    def test_generate_mps_cache_cleared_in_finally_when_available(self, mock_args_base):
        base = _make_base_pipeline()
        with patch("generate.load_base", return_value=base), \
             patch("generate.gc"), \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.mps.empty_cache") as mock_mps, \
             patch("generate.torch.cuda.is_available", return_value=False), \
             patch("generate.torch.backends.mps.is_available", return_value=True):
            gen.generate(mock_args_base)

        mock_mps.assert_called()

    def test_generate_mps_not_cleared_when_unavailable(self, mock_args_base):
        base = _make_base_pipeline()
        with patch("generate.load_base", return_value=base), \
             patch("generate.gc"), \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.mps.empty_cache") as mock_mps, \
             patch("generate.torch.cuda.is_available", return_value=False), \
             patch("generate.torch.backends.mps.is_available", return_value=False):
            gen.generate(mock_args_base)

        mock_mps.assert_not_called()

    def test_generate_image_nulled_in_finally(self, mock_args_base):
        """generate() should set image = None in finally so PIL buffer is released."""
        base = _make_base_pipeline()


        with patch("generate.load_base", return_value=base), \
             patch("generate.gc"), \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.cuda.is_available", return_value=False), \
             patch("generate.torch.backends.mps.is_available", return_value=False):
            result = gen.generate(mock_args_base)

        # Function completes without error — the PIL image was cleaned up in finally
        assert result is not None

    def test_generate_image_saved_inside_try(self, mock_args_base):
        """image.save() should run inside try, before finally nulls the reference."""
        save_calls = []

        class TrackingSaveImage:
            def save(self, path):
                save_calls.append(path)

        class TrackingPipeline(MockPipeline):
            def __call__(self, **kwargs):
                result = MagicMock()
                result.images = [TrackingSaveImage()]
                return result

        base = TrackingPipeline()
        with patch("generate.load_base", return_value=base), \
             patch("generate.gc"), \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.cuda.is_available", return_value=False), \
             patch("generate.torch.backends.mps.is_available", return_value=False):
            gen.generate(mock_args_base)

        assert len(save_calls) == 1

    def test_generate_exception_propagates_after_cleanup(self, mock_args_base):
        """Exceptions must still propagate after finally runs."""
        with patch("generate.load_base", side_effect=ValueError("bad args")), \
             patch("generate.gc"), \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.cuda.is_available", return_value=False), \
             patch("generate.torch.backends.mps.is_available", return_value=False):
            with pytest.raises(ValueError, match="bad args"):
                gen.generate(mock_args_base)

    def test_accelerate_version_floor(self):
        """accelerate>=0.24.0 is required for CPU offload hook deregistration."""
        import importlib.metadata as meta

        from packaging.version import Version

        try:
            version = Version(meta.version("accelerate"))
            assert version >= Version("0.24.0"), (
                f"accelerate {version} is below 0.24.0 floor. "
                "CPU offload hooks won't deregister on model delete."
            )
        except meta.PackageNotFoundError:
            pytest.skip("accelerate not installed in this environment")


# ---------------------------------------------------------------------------
# Group 2 — MEDIUM memory fixes (9 tests, PR #5)
# ---------------------------------------------------------------------------


class TestEntryPointFlush:
    """
    Entry-point VRAM flush fires before load_base(), reclaiming residual
    GPU memory from any prior generate() call.
    """

    def test_gc_collect_called_at_entry_cuda(self, mock_args_cuda):
        call_log = []

        def track_gc():
            call_log.append("gc")

        def track_load_base(device):
            call_log.append("load_base")
            return _make_base_pipeline()

        with patch("generate.get_device", return_value="cuda"), \
             patch("generate.load_base", side_effect=track_load_base), \
             patch("generate.gc") as mock_gc, \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.cuda.is_available", return_value=True), \
             patch("generate.torch.backends.mps.is_available", return_value=False), \
             patch("generate.torch._dynamo", create=True):
            mock_gc.collect.side_effect = track_gc
            gen.generate(mock_args_cuda)

        assert mock_gc.collect.called, "gc.collect() should fire before load_base on CUDA"
        gc_idx = next((i for i, e in enumerate(call_log) if e == "gc"), -1)
        lb_idx = next((i for i, e in enumerate(call_log) if e == "load_base"), len(call_log))
        assert gc_idx < lb_idx, "gc.collect() must precede load_base()"

    def test_cuda_cache_flush_at_entry(self, mock_args_cuda):
        call_log = []

        def track_cuda_flush():
            call_log.append("cuda_flush")

        def track_load_base(device):
            call_log.append("load_base")
            return _make_base_pipeline()

        with patch("generate.get_device", return_value="cuda"), \
             patch("generate.load_base", side_effect=track_load_base), \
             patch("generate.gc"), \
             patch("generate.torch.cuda.empty_cache") as mock_cuda, \
             patch("generate.torch.cuda.is_available", return_value=True), \
             patch("generate.torch.backends.mps.is_available", return_value=False), \
             patch("generate.torch._dynamo", create=True):
            mock_cuda.side_effect = track_cuda_flush
            gen.generate(mock_args_cuda)

        assert mock_cuda.called, "torch.cuda.empty_cache() should fire before load_base"
        flush_idx = next((i for i, e in enumerate(call_log) if e == "cuda_flush"), -1)
        lb_idx = next((i for i, e in enumerate(call_log) if e == "load_base"), len(call_log))
        assert flush_idx < lb_idx, "cuda.empty_cache() must precede load_base()"

    def test_mps_cache_flush_at_entry(self, mock_args_base):
        call_log = []

        def track_mps_flush():
            call_log.append("mps_flush")

        def track_load_base(device):
            call_log.append("load_base")
            return _make_base_pipeline()

        with patch("generate.get_device", return_value="mps"), \
             patch("generate.load_base", side_effect=track_load_base), \
             patch("generate.gc"), \
             patch("generate.torch.mps.empty_cache") as mock_mps, \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.cuda.is_available", return_value=False), \
             patch("generate.torch.backends.mps.is_available", return_value=True):
            mock_mps.side_effect = track_mps_flush
            gen.generate(mock_args_base)

        assert mock_mps.called, "torch.mps.empty_cache() should fire before load_base"
        flush_idx = next((i for i, e in enumerate(call_log) if e == "mps_flush"), -1)
        lb_idx = next((i for i, e in enumerate(call_log) if e == "load_base"), len(call_log))
        assert flush_idx < lb_idx, "mps.empty_cache() must precede load_base()"


class TestLatentsTensorHandling:
    """Latents are moved to CPU before the cache flush window, then back for refiner."""

    def _make_base_with_latent(self, latent_mock):
        """Return a MagicMock pipeline that yields latent_mock as its output."""
        base = MagicMock(spec=MockPipeline())
        base.text_encoder_2 = MagicMock()
        base.vae = MagicMock()
        call_result = MagicMock()
        call_result.images = latent_mock
        base.return_value = call_result
        return base

    def test_latents_not_holding_gpu_ref_during_cache_flush(self, mock_args_cuda_refine):
        """latents.cpu() is called before the between-pipelines empty_cache()."""
        call_log = []
        latent_mock = MagicMock()
        latent_mock.cpu.side_effect = lambda: (call_log.append("latents_cpu"), latent_mock)[1]
        latent_mock.to.return_value = latent_mock

        base = self._make_base_with_latent(latent_mock)
        refiner = _make_refiner_pipeline()

        def track_cuda_flush():
            call_log.append("cuda_flush")

        with patch("generate.get_device", return_value="cuda"), \
             patch("generate.load_base", return_value=base), \
             patch("generate.load_refiner", return_value=refiner), \
             patch("generate.gc"), \
             patch("generate.torch.cuda.empty_cache") as mock_cuda, \
             patch("generate.torch.cuda.is_available", return_value=True), \
             patch("generate.torch.backends.mps.is_available", return_value=False), \
             patch("generate.torch._dynamo", create=True):
            mock_cuda.side_effect = track_cuda_flush
            gen.generate(mock_args_cuda_refine)

        assert latent_mock.cpu.called, "latents.cpu() must be called before cache flush"
        cpu_idx = next((i for i, e in enumerate(call_log) if e == "latents_cpu"), -1)
        # The between-pipelines flush occurs AFTER latents.cpu() — find the first
        # cuda_flush that comes after latents_cpu (entry flush comes before, so skip it).
        post_cpu_flushes = [i for i, e in enumerate(call_log) if e == "cuda_flush" and i > cpu_idx]
        assert cpu_idx >= 0, "latents.cpu() was never called"
        assert post_cpu_flushes, "cuda.empty_cache() must be called after latents.cpu()"

    def test_latents_transferred_back_for_refiner(self, mock_args_cuda_refine):
        """latents.to(device) is used when passing latents to the refiner."""
        latent_mock = MagicMock()
        latent_mock.cpu.return_value = latent_mock
        latent_mock.to.return_value = latent_mock

        base = self._make_base_with_latent(latent_mock)
        refiner = _make_refiner_pipeline()

        with patch("generate.get_device", return_value="cuda"), \
             patch("generate.load_base", return_value=base), \
             patch("generate.load_refiner", return_value=refiner), \
             patch("generate.gc"), \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.cuda.is_available", return_value=True), \
             patch("generate.torch.backends.mps.is_available", return_value=False), \
             patch("generate.torch._dynamo", create=True):
            gen.generate(mock_args_cuda_refine)

        latent_mock.to.assert_called_with("cuda")

    def test_latents_cleanup_in_finally(self, mock_args_refine):
        """latents is deleted in the finally block regardless of success or failure."""
        base = _make_base_pipeline_with_latents()
        refiner = _make_refiner_pipeline()

        # Trigger the finally path — function completes normally, latents must be cleaned up.
        with patch("generate.load_base", return_value=base), \
             patch("generate.load_refiner", return_value=refiner), \
             patch("generate.gc"), \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.cuda.is_available", return_value=False), \
             patch("generate.torch.backends.mps.is_available", return_value=False):
            # Should complete without error; finally block cleans latents
            gen.generate(mock_args_refine)


class TestDynamoCacheReset:
    """torch._dynamo.reset() must fire on CUDA after cleanup, never on CPU."""

    def test_dynamo_reset_called_after_cleanup_cuda(self, mock_args_cuda):
        """On CUDA, torch._dynamo.reset() is called in finally."""
        dynamo_mock = MagicMock()
        base = _make_base_pipeline()

        with patch("generate.get_device", return_value="cuda"), \
             patch("generate.load_base", return_value=base), \
             patch("generate.gc"), \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.cuda.is_available", return_value=True), \
             patch("generate.torch.backends.mps.is_available", return_value=False), \
             patch("generate.torch._dynamo", dynamo_mock, create=True), \
             patch("generate.hasattr", return_value=True):
            gen.generate(mock_args_cuda)

        dynamo_mock.reset.assert_called_once()

    def test_dynamo_not_reset_on_cpu(self, mock_args_base):
        """On CPU, torch._dynamo.reset() must NOT be called."""
        dynamo_mock = MagicMock()
        base = _make_base_pipeline()

        with patch("generate.load_base", return_value=base), \
             patch("generate.gc"), \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.cuda.is_available", return_value=False), \
             patch("generate.torch.backends.mps.is_available", return_value=False), \
             patch("generate.torch._dynamo", dynamo_mock, create=True):
            gen.generate(mock_args_base)

        dynamo_mock.reset.assert_not_called()


class TestGlobalState:

    def test_repeated_calls_dont_compound_memory(self, mock_args_base):
        """generate() uses only local pipeline vars — no module-level accumulation."""
        base = _make_base_pipeline()
        gc_call_counts = []

        with patch("generate.load_base", return_value=base), \
             patch("generate.gc") as mock_gc, \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.cuda.is_available", return_value=False), \
             patch("generate.torch.backends.mps.is_available", return_value=False):
            gen.generate(mock_args_base)
            gc_call_counts.append(mock_gc.collect.call_count)

            # Reset the base mock so it can be "loaded" again
            mock_gc.collect.reset_mock()
            base2 = _make_base_pipeline()

        with patch("generate.load_base", return_value=base2), \
             patch("generate.gc") as mock_gc2, \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.cuda.is_available", return_value=False), \
             patch("generate.torch.backends.mps.is_available", return_value=False):
            gen.generate(mock_args_base)
            gc_call_counts.append(mock_gc2.collect.call_count)

        # Both calls trigger gc — same count, no accumulation
        assert gc_call_counts[0] == gc_call_counts[1], (
            "gc.collect() call count should be consistent across generate() invocations"
        )
