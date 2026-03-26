"""
Unit tests for previously-untested functions in generate.py (Issue #8).

Covers:
    1. get_device()   — CUDA, MPS, CPU fallback, force_cpu
    2. get_dtype()    — float16 for GPU, float32 for CPU
    3. load_base()    — from_pretrained args, device routing, torch.compile
    4. load_refiner()  — from_pretrained args, shared components, device routing
    5. flush pattern  — CUDA/MPS cache clearing in generate() pre-flight
    6. main()         — single-prompt path calls generate_with_retry

All tests use mocking — no GPU or model downloads required.
"""

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

import pytest
import torch

import generate as gen
from generate import get_device, get_dtype, load_base, load_refiner, main


# ── 1. get_device() ─────────────────────────────────────────────────────────

class TestGetDevice:
    """get_device(force_cpu) selects CUDA > MPS > CPU, respects force_cpu."""

    def test_force_cpu_returns_cpu(self):
        """force_cpu=True always returns 'cpu' regardless of GPU availability."""
        result = get_device(force_cpu=True)
        assert result == "cpu"

    @patch("generate.torch")
    def test_cuda_available_returns_cuda(self, mock_torch):
        """When CUDA is available, returns 'cuda'."""
        mock_torch.cuda.is_available.return_value = True
        result = get_device(force_cpu=False)
        assert result == "cuda"

    @patch("generate.torch")
    def test_mps_available_returns_mps(self, mock_torch):
        """When CUDA unavailable but MPS available, returns 'mps'."""
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = True
        # hasattr check on mock returns True by default
        result = get_device(force_cpu=False)
        assert result == "mps"

    @patch("generate.torch")
    def test_no_gpu_returns_cpu(self, mock_torch):
        """When no GPU available, falls back to 'cpu'."""
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = False
        result = get_device(force_cpu=False)
        assert result == "cpu"

    @patch("generate.torch")
    def test_cuda_preferred_over_mps(self, mock_torch):
        """CUDA takes priority when both CUDA and MPS are available."""
        mock_torch.cuda.is_available.return_value = True
        mock_torch.backends.mps.is_available.return_value = True
        result = get_device(force_cpu=False)
        assert result == "cuda"


# ── 2. get_dtype() ──────────────────────────────────────────────────────────

class TestGetDtype:
    """get_dtype(device) returns appropriate dtype per device."""

    def test_cuda_returns_float16(self):
        assert get_dtype("cuda") == torch.float16

    def test_mps_returns_float16(self):
        assert get_dtype("mps") == torch.float16

    def test_cpu_returns_float32(self):
        assert get_dtype("cpu") == torch.float32

    def test_unknown_device_returns_float32(self):
        """Any device not in ('cuda', 'mps') gets float32."""
        assert get_dtype("xla") == torch.float32


# ── 3. load_base() ──────────────────────────────────────────────────────────

class TestLoadBase:
    """load_base(device) calls from_pretrained correctly and routes to device."""

    @patch("generate.torch")
    @patch("generate.DiffusionPipeline")
    def test_load_base_calls_from_pretrained_with_sdxl_model(self, mock_dp, mock_torch):
        """from_pretrained is called with the SDXL base model ID."""
        mock_pipe = MagicMock()
        mock_dp.from_pretrained.return_value = mock_pipe
        mock_torch.float32 = torch.float32
        mock_torch.float16 = torch.float16

        load_base("cpu")

        mock_dp.from_pretrained.assert_called_once()
        args, kwargs = mock_dp.from_pretrained.call_args
        assert args[0] == "stabilityai/stable-diffusion-xl-base-1.0"

    @patch("generate.torch")
    @patch("generate.DiffusionPipeline")
    def test_load_base_cpu_uses_float32(self, mock_dp, mock_torch):
        """CPU device uses float32 dtype."""
        mock_pipe = MagicMock()
        mock_dp.from_pretrained.return_value = mock_pipe
        mock_torch.float32 = torch.float32
        mock_torch.float16 = torch.float16

        load_base("cpu")

        _, kwargs = mock_dp.from_pretrained.call_args
        assert kwargs["torch_dtype"] == torch.float32

    @patch("generate.torch")
    @patch("generate.DiffusionPipeline")
    def test_load_base_cuda_uses_float16(self, mock_dp, mock_torch):
        """CUDA device uses float16 dtype."""
        mock_pipe = MagicMock()
        mock_dp.from_pretrained.return_value = mock_pipe
        mock_torch.float16 = torch.float16
        mock_torch.float32 = torch.float32
        # Prevent torch.compile branch
        mock_torch.compile = None
        delattr(mock_torch, 'compile')

        load_base("cuda")

        _, kwargs = mock_dp.from_pretrained.call_args
        assert kwargs["torch_dtype"] == torch.float16

    @patch("generate.torch")
    @patch("generate.DiffusionPipeline")
    def test_load_base_cuda_uses_fp16_variant(self, mock_dp, mock_torch):
        """CUDA uses variant='fp16' for faster loading."""
        mock_pipe = MagicMock()
        mock_dp.from_pretrained.return_value = mock_pipe
        mock_torch.float16 = torch.float16
        mock_torch.float32 = torch.float32
        delattr(mock_torch, 'compile')

        load_base("cuda")

        _, kwargs = mock_dp.from_pretrained.call_args
        assert kwargs["variant"] == "fp16"

    @patch("generate.torch")
    @patch("generate.DiffusionPipeline")
    def test_load_base_cpu_no_fp16_variant(self, mock_dp, mock_torch):
        """CPU does not use fp16 variant."""
        mock_pipe = MagicMock()
        mock_dp.from_pretrained.return_value = mock_pipe
        mock_torch.float32 = torch.float32
        mock_torch.float16 = torch.float16

        load_base("cpu")

        _, kwargs = mock_dp.from_pretrained.call_args
        assert kwargs["variant"] is None

    @patch("generate.torch")
    @patch("generate.DiffusionPipeline")
    def test_load_base_cpu_enables_cpu_offload(self, mock_dp, mock_torch):
        """CPU device calls enable_model_cpu_offload()."""
        mock_pipe = MagicMock()
        mock_dp.from_pretrained.return_value = mock_pipe
        mock_torch.float32 = torch.float32
        mock_torch.float16 = torch.float16

        load_base("cpu")

        mock_pipe.enable_model_cpu_offload.assert_called_once()
        mock_pipe.to.assert_not_called()

    @patch("generate.torch")
    @patch("generate.DiffusionPipeline")
    def test_load_base_mps_enables_cpu_offload(self, mock_dp, mock_torch):
        """MPS device calls enable_model_cpu_offload()."""
        mock_pipe = MagicMock()
        mock_dp.from_pretrained.return_value = mock_pipe
        mock_torch.float16 = torch.float16
        mock_torch.float32 = torch.float32

        load_base("mps")

        mock_pipe.enable_model_cpu_offload.assert_called_once()
        mock_pipe.to.assert_not_called()

    @patch("generate.torch")
    @patch("generate.DiffusionPipeline")
    def test_load_base_cuda_calls_to_device(self, mock_dp, mock_torch):
        """CUDA device calls pipe.to('cuda') instead of cpu_offload."""
        mock_pipe = MagicMock()
        mock_dp.from_pretrained.return_value = mock_pipe
        mock_torch.float16 = torch.float16
        mock_torch.float32 = torch.float32
        # Prevent torch.compile branch
        delattr(mock_torch, 'compile')

        load_base("cuda")

        mock_pipe.to.assert_called_once_with("cuda")
        mock_pipe.enable_model_cpu_offload.assert_not_called()

    @patch("generate.torch")
    @patch("generate.DiffusionPipeline")
    def test_load_base_uses_safetensors(self, mock_dp, mock_torch):
        """from_pretrained always uses use_safetensors=True."""
        mock_pipe = MagicMock()
        mock_dp.from_pretrained.return_value = mock_pipe
        mock_torch.float32 = torch.float32
        mock_torch.float16 = torch.float16

        load_base("cpu")

        _, kwargs = mock_dp.from_pretrained.call_args
        assert kwargs["use_safetensors"] is True

    @patch("generate.torch")
    @patch("generate.DiffusionPipeline")
    def test_load_base_cuda_with_compile(self, mock_dp, mock_torch):
        """On CUDA with torch.compile available, UNet gets compiled."""
        mock_pipe = MagicMock()
        mock_dp.from_pretrained.return_value = mock_pipe
        mock_torch.float16 = torch.float16
        mock_torch.float32 = torch.float32
        mock_compiled = MagicMock(name="compiled_unet")
        mock_torch.compile.return_value = mock_compiled

        # Capture the original unet before load_base reassigns it
        original_unet = mock_pipe.unet

        load_base("cuda")

        mock_torch.compile.assert_called_once_with(
            original_unet, mode="reduce-overhead", fullgraph=True
        )
        assert mock_pipe.unet == mock_compiled


# ── 4. load_refiner() ───────────────────────────────────────────────────────

class TestLoadRefiner:
    """load_refiner() calls from_pretrained with refiner model and shared components."""

    @patch("generate.torch")
    @patch("generate.DiffusionPipeline")
    def test_load_refiner_uses_refiner_model_id(self, mock_dp, mock_torch):
        """from_pretrained is called with the SDXL refiner model ID."""
        mock_refiner = MagicMock()
        mock_dp.from_pretrained.return_value = mock_refiner
        mock_torch.float32 = torch.float32
        mock_torch.float16 = torch.float16

        te2 = MagicMock()
        vae = MagicMock()
        load_refiner(te2, vae, "cpu")

        args, kwargs = mock_dp.from_pretrained.call_args
        assert args[0] == "stabilityai/stable-diffusion-xl-refiner-1.0"

    @patch("generate.torch")
    @patch("generate.DiffusionPipeline")
    def test_load_refiner_shares_text_encoder_and_vae(self, mock_dp, mock_torch):
        """Refiner receives shared text_encoder_2 and vae from base."""
        mock_refiner = MagicMock()
        mock_dp.from_pretrained.return_value = mock_refiner
        mock_torch.float32 = torch.float32
        mock_torch.float16 = torch.float16

        te2 = MagicMock(name="text_encoder_2")
        vae = MagicMock(name="vae")
        load_refiner(te2, vae, "cpu")

        _, kwargs = mock_dp.from_pretrained.call_args
        assert kwargs["text_encoder_2"] is te2
        assert kwargs["vae"] is vae

    @patch("generate.torch")
    @patch("generate.DiffusionPipeline")
    def test_load_refiner_cpu_enables_offload(self, mock_dp, mock_torch):
        """CPU device calls enable_model_cpu_offload on refiner."""
        mock_refiner = MagicMock()
        mock_dp.from_pretrained.return_value = mock_refiner
        mock_torch.float32 = torch.float32
        mock_torch.float16 = torch.float16

        load_refiner(MagicMock(), MagicMock(), "cpu")

        mock_refiner.enable_model_cpu_offload.assert_called_once()
        mock_refiner.to.assert_not_called()

    @patch("generate.torch")
    @patch("generate.DiffusionPipeline")
    def test_load_refiner_cuda_calls_to_device(self, mock_dp, mock_torch):
        """CUDA device calls refiner.to('cuda')."""
        mock_refiner = MagicMock()
        mock_dp.from_pretrained.return_value = mock_refiner
        mock_torch.float16 = torch.float16
        mock_torch.float32 = torch.float32

        load_refiner(MagicMock(), MagicMock(), "cuda")

        mock_refiner.to.assert_called_once_with("cuda")
        mock_refiner.enable_model_cpu_offload.assert_not_called()

    @patch("generate.torch")
    @patch("generate.DiffusionPipeline")
    def test_load_refiner_cuda_uses_fp16(self, mock_dp, mock_torch):
        """CUDA refiner uses float16 and fp16 variant."""
        mock_refiner = MagicMock()
        mock_dp.from_pretrained.return_value = mock_refiner
        mock_torch.float16 = torch.float16
        mock_torch.float32 = torch.float32

        load_refiner(MagicMock(), MagicMock(), "cuda")

        _, kwargs = mock_dp.from_pretrained.call_args
        assert kwargs["torch_dtype"] == torch.float16
        assert kwargs["variant"] == "fp16"

    @patch("generate.torch")
    @patch("generate.DiffusionPipeline")
    def test_load_refiner_mps_enables_offload(self, mock_dp, mock_torch):
        """MPS device calls enable_model_cpu_offload on refiner."""
        mock_refiner = MagicMock()
        mock_dp.from_pretrained.return_value = mock_refiner
        mock_torch.float16 = torch.float16
        mock_torch.float32 = torch.float32

        load_refiner(MagicMock(), MagicMock(), "mps")

        mock_refiner.enable_model_cpu_offload.assert_called_once()


# ── 5. Pre-flight device cache flush in generate() ─────────────────────────

class TestPreFlightCacheFlush:
    """generate() flushes GPU caches at entry before loading pipelines."""

    @patch("generate.load_base")
    @patch("generate.get_device", return_value="cpu")
    @patch("generate.gc")
    @patch("generate.torch")
    def test_gc_collect_called_at_preflight(self, mock_torch, mock_gc,
                                            mock_get_device, mock_load_base):
        """gc.collect() is called during pre-flight flush."""
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = False
        mock_pipe = MagicMock()
        mock_pipe.return_value.images = [MagicMock()]
        mock_load_base.return_value = mock_pipe

        args = SimpleNamespace(
            prompt="test", output="outputs/test.png", seed=None,
            cpu=True, refine=False, steps=2, guidance=7.5,
            width=64, height=64, negative_prompt="bad",
            scheduler="DPMSolverMultistepScheduler", refiner_guidance=5.0,
        )
        gen.generate(args)
        mock_gc.collect.assert_called()

    @patch("generate.load_base")
    @patch("generate.get_device", return_value="cuda")
    @patch("generate.gc")
    @patch("generate.torch")
    def test_cuda_cache_flushed_at_preflight(self, mock_torch, mock_gc,
                                              mock_get_device, mock_load_base):
        """torch.cuda.empty_cache() called during pre-flight on CUDA."""
        mock_torch.cuda.is_available.return_value = True
        mock_torch.backends.mps.is_available.return_value = False
        mock_torch.float16 = torch.float16
        # Set up _dynamo for finally block
        mock_torch._dynamo = MagicMock()
        mock_pipe = MagicMock()
        mock_pipe.return_value.images = [MagicMock()]
        mock_load_base.return_value = mock_pipe

        args = SimpleNamespace(
            prompt="test", output="outputs/test.png", seed=None,
            cpu=False, refine=False, steps=2, guidance=7.5,
            width=64, height=64, negative_prompt="bad",
            scheduler="DPMSolverMultistepScheduler", refiner_guidance=5.0,
        )
        gen.generate(args)
        mock_torch.cuda.empty_cache.assert_called()

    @patch("generate.load_base")
    @patch("generate.get_device", return_value="mps")
    @patch("generate.gc")
    @patch("generate.torch")
    def test_mps_cache_flushed_at_preflight(self, mock_torch, mock_gc,
                                             mock_get_device, mock_load_base):
        """torch.mps.empty_cache() called during pre-flight on MPS."""
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = True
        mock_torch.float16 = torch.float16
        mock_pipe = MagicMock()
        mock_pipe.return_value.images = [MagicMock()]
        mock_load_base.return_value = mock_pipe

        args = SimpleNamespace(
            prompt="test", output="outputs/test.png", seed=None,
            cpu=False, refine=False, steps=2, guidance=7.5,
            width=64, height=64, negative_prompt="bad",
            scheduler="DPMSolverMultistepScheduler", refiner_guidance=5.0,
        )
        gen.generate(args)
        mock_torch.mps.empty_cache.assert_called()


# ── 6. main() single-prompt path ────────────────────────────────────────────

class TestMainSinglePrompt:
    """main() with --prompt (no batch file) calls generate_with_retry."""

    @patch("generate.generate_with_retry", return_value="outputs/test.png")
    @patch("generate.parse_args")
    def test_main_single_prompt_calls_generate_with_retry(self, mock_parse, mock_gwr):
        """Single prompt path delegates to generate_with_retry."""
        mock_args = MagicMock()
        mock_args.batch_file = None
        mock_args.prompt = "test prompt"
        mock_args.cpu = False
        mock_parse.return_value = mock_args

        main()

        mock_gwr.assert_called_once_with(mock_args)

    @patch("generate.generate_with_retry", return_value="outputs/test.png")
    @patch("generate.parse_args")
    def test_main_single_prompt_does_not_call_batch_generate(self, mock_parse, mock_gwr):
        """Single prompt path does NOT call batch_generate."""
        mock_args = MagicMock()
        mock_args.batch_file = None
        mock_args.prompt = "a tropical scene"
        mock_args.cpu = False
        mock_parse.return_value = mock_args

        with patch("generate.batch_generate") as mock_bg:
            main()
            mock_bg.assert_not_called()

    @patch("generate.generate_with_retry", side_effect=RuntimeError("test fail"))
    @patch("generate.parse_args")
    def test_main_single_prompt_propagates_exception(self, mock_parse, mock_gwr):
        """Exceptions from generate_with_retry propagate out of main()."""
        mock_args = MagicMock()
        mock_args.batch_file = None
        mock_args.prompt = "test"
        mock_args.cpu = False
        mock_parse.return_value = mock_args

        with pytest.raises(RuntimeError, match="test fail"):
            main()
