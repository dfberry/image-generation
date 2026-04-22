"""
Coverage gap tests (Issue #55).

Covers four previously untested areas:
    1. Seed binding — generator created with correct device and manual_seed
    2. Output path handling — auto-generated timestamp path vs explicit path
    3. xformers availability — _apply_performance_opts tries xformers, falls back
    4. Karras sigma scheduler — apply_scheduler sets use_karras_sigmas for DPMSolver

All tests use mocking — no GPU, torch, or diffusers required at import time.
"""

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import generate as gen_module
from generate import apply_scheduler

# ---------------------------------------------------------------------------
# Helpers — inject mocks directly into gen_module.__dict__ to bypass PEP 562
# __getattr__ which would otherwise try to ``import torch``.
# ---------------------------------------------------------------------------

@contextmanager
def _patch_heavy():
    """Inject mock torch/diffusers into generate's globals, then restore."""
    mock_torch = MagicMock()
    mock_torch.cuda.empty_cache = MagicMock()
    mock_torch.cuda.is_available.return_value = False
    mock_torch.backends.mps.is_available.return_value = False

    had_torch = "torch" in gen_module.__dict__
    had_diffusers = "diffusers" in gen_module.__dict__
    old_torch = gen_module.__dict__.get("torch")
    old_diffusers = gen_module.__dict__.get("diffusers")

    gen_module.__dict__["torch"] = mock_torch
    gen_module.__dict__["diffusers"] = MagicMock()

    original_ensure = gen_module._ensure_heavy_imports
    gen_module._ensure_heavy_imports = lambda: None

    try:
        yield mock_torch
    finally:
        gen_module._ensure_heavy_imports = original_ensure
        if had_torch:
            gen_module.__dict__["torch"] = old_torch
        else:
            gen_module.__dict__.pop("torch", None)
        if had_diffusers:
            gen_module.__dict__["diffusers"] = old_diffusers
        else:
            gen_module.__dict__.pop("diffusers", None)


def _base_args(tmp_path, **overrides):
    """Return a minimal args namespace for generate()."""
    defaults = dict(
        prompt="test prompt",
        output=str(tmp_path / "out.png"),
        seed=None,
        cpu=True,
        refine=False,
        steps=2,
        guidance=7.5,
        width=64,
        height=64,
        negative_prompt="",
        scheduler="DPMSolverMultistepScheduler",
        refiner_guidance=5.0,
        lora=None,
        lora_weight=0.8,
        refiner_steps=10,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_mock_pipe():
    """Return a MagicMock pipeline that produces a single mock image."""
    pipe = MagicMock()
    pipe.return_value.images = [MagicMock()]
    pipe.scheduler = MagicMock()
    pipe.scheduler.config = {}
    return pipe


# ===================================================================
# 1. Seed binding — torch.Generator created correctly
# ===================================================================


class TestSeedBinding:
    """generate() must create a torch.Generator seeded on the correct device."""

    def test_seed_creates_generator_with_manual_seed(self, tmp_path):
        """When seed is set, torch.Generator().manual_seed(seed) is called."""
        args = _base_args(tmp_path, seed=42)

        mock_generator = MagicMock()
        mock_generator.manual_seed.return_value = mock_generator

        with _patch_heavy() as mock_torch:
            mock_torch.Generator.return_value = mock_generator
            mock_pipe = _make_mock_pipe()
            with patch.object(gen_module, "load_base", return_value=mock_pipe), \
                 patch.object(gen_module, "get_device", return_value="cpu"):
                gen_module.generate(args)

        mock_torch.Generator.assert_called_once()
        mock_generator.manual_seed.assert_called_once_with(42)

    def test_no_seed_skips_generator(self, tmp_path):
        """When seed is None, torch.Generator should NOT be called."""
        args = _base_args(tmp_path, seed=None)

        with _patch_heavy() as mock_torch:
            mock_pipe = _make_mock_pipe()
            with patch.object(gen_module, "load_base", return_value=mock_pipe), \
                 patch.object(gen_module, "get_device", return_value="cpu"):
                gen_module.generate(args)

        mock_torch.Generator.assert_not_called()

    def test_seed_generator_device_is_cpu_for_cpu_mode(self, tmp_path):
        """On CPU device, Generator device must be 'cpu'."""
        args = _base_args(tmp_path, seed=7, cpu=True)

        mock_generator = MagicMock()
        mock_generator.manual_seed.return_value = mock_generator

        with _patch_heavy() as mock_torch:
            mock_torch.Generator.return_value = mock_generator
            mock_pipe = _make_mock_pipe()
            with patch.object(gen_module, "load_base", return_value=mock_pipe), \
                 patch.object(gen_module, "get_device", return_value="cpu"):
                gen_module.generate(args)

        mock_torch.Generator.assert_called_once_with(device="cpu")

    def test_seed_generator_device_is_cpu_for_mps(self, tmp_path):
        """On MPS device, Generator device must be 'cpu' (cpu_offload routing)."""
        args = _base_args(tmp_path, seed=7, cpu=False)

        mock_generator = MagicMock()
        mock_generator.manual_seed.return_value = mock_generator

        with _patch_heavy() as mock_torch:
            mock_torch.backends.mps.is_available.return_value = True
            mock_torch.Generator.return_value = mock_generator
            mock_pipe = _make_mock_pipe()
            with patch.object(gen_module, "load_base", return_value=mock_pipe), \
                 patch.object(gen_module, "get_device", return_value="mps"):
                gen_module.generate(args)

        mock_torch.Generator.assert_called_once_with(device="cpu")

    def test_seed_generator_device_matches_cuda(self, tmp_path):
        """On CUDA device, Generator device must be 'cuda'."""
        args = _base_args(tmp_path, seed=99, cpu=False)

        mock_generator = MagicMock()
        mock_generator.manual_seed.return_value = mock_generator

        with _patch_heavy() as mock_torch:
            mock_torch.cuda.is_available.return_value = True
            mock_torch.backends.mps.is_available.return_value = False
            mock_torch._dynamo = MagicMock()
            mock_torch.Generator.return_value = mock_generator
            mock_pipe = _make_mock_pipe()
            with patch.object(gen_module, "load_base", return_value=mock_pipe), \
                 patch.object(gen_module, "get_device", return_value="cuda"):
                gen_module.generate(args)

        mock_torch.Generator.assert_called_once_with(device="cuda")

    def test_generator_passed_to_pipeline_call(self, tmp_path):
        """The seeded generator must be forwarded to the pipeline __call__."""
        args = _base_args(tmp_path, seed=42)

        mock_generator = MagicMock()
        mock_generator.manual_seed.return_value = mock_generator

        with _patch_heavy() as mock_torch:
            mock_torch.Generator.return_value = mock_generator
            mock_pipe = _make_mock_pipe()
            with patch.object(gen_module, "load_base", return_value=mock_pipe), \
                 patch.object(gen_module, "get_device", return_value="cpu"):
                gen_module.generate(args)

        _, pipe_kwargs = mock_pipe.call_args
        assert pipe_kwargs["generator"] is mock_generator


# ===================================================================
# 2. Output path handling
# ===================================================================


class TestOutputPathHandling:
    """generate() auto-generates a timestamp path when output is None."""

    def test_explicit_output_path_returned(self, tmp_path):
        """When output is set, generate() returns that exact path."""
        target = str(tmp_path / "explicit.png")
        args = _base_args(tmp_path, output=target)

        with _patch_heavy():
            mock_pipe = _make_mock_pipe()
            with patch.object(gen_module, "load_base", return_value=mock_pipe), \
                 patch.object(gen_module, "get_device", return_value="cpu"):
                result = gen_module.generate(args)

        assert result == target

    def test_none_output_generates_timestamped_path(self, tmp_path):
        """When output is None, generate() creates outputs/image_<timestamp>.png."""
        args = _base_args(tmp_path, output=None)

        with _patch_heavy(), \
             patch("os.makedirs"):
            mock_pipe = _make_mock_pipe()
            with patch.object(gen_module, "load_base", return_value=mock_pipe), \
                 patch.object(gen_module, "get_device", return_value="cpu"):
                result = gen_module.generate(args)

        assert result.startswith("outputs/image_")
        assert result.endswith(".png")

    def test_none_output_path_has_correct_timestamp_format(self, tmp_path):
        """Auto-generated path matches outputs/image_YYYYMMDD_HHMMSS.png pattern."""
        import re
        args = _base_args(tmp_path, output=None)

        with _patch_heavy(), \
             patch("os.makedirs"):
            mock_pipe = _make_mock_pipe()
            with patch.object(gen_module, "load_base", return_value=mock_pipe), \
                 patch.object(gen_module, "get_device", return_value="cpu"):
                result = gen_module.generate(args)

        pattern = r"^outputs/image_\d{8}_\d{6}\.png$"
        assert re.match(pattern, result), f"Path '{result}' does not match expected pattern"


# ===================================================================
# 3. xformers availability check — _apply_performance_opts
# ===================================================================


class TestXformersAvailability:
    """_apply_performance_opts tries xformers first, then falls back to attention slicing."""

    def test_xformers_called_when_available(self):
        """If pipe has enable_xformers_memory_efficient_attention, it is called."""
        pipe = MagicMock()
        pipe.enable_xformers_memory_efficient_attention = MagicMock()
        pipe.enable_attention_slicing = MagicMock()

        with _patch_heavy():
            gen_module._apply_performance_opts(pipe, "cpu")

        pipe.enable_xformers_memory_efficient_attention.assert_called_once()
        pipe.enable_attention_slicing.assert_not_called()

    def test_attention_slicing_fallback_when_xformers_raises(self):
        """If xformers raises, falls back to attention slicing."""
        pipe = MagicMock()
        pipe.enable_xformers_memory_efficient_attention.side_effect = RuntimeError("no xformers")
        pipe.enable_attention_slicing = MagicMock()

        with _patch_heavy():
            gen_module._apply_performance_opts(pipe, "cpu")

        pipe.enable_xformers_memory_efficient_attention.assert_called_once()
        pipe.enable_attention_slicing.assert_called_once()

    def test_attention_slicing_when_xformers_not_present(self):
        """If pipe lacks enable_xformers_memory_efficient_attention entirely."""
        pipe = MagicMock(spec=["enable_attention_slicing", "unet"])
        pipe.enable_attention_slicing = MagicMock()

        with _patch_heavy():
            gen_module._apply_performance_opts(pipe, "cpu")

        pipe.enable_attention_slicing.assert_called_once()

    def test_cuda_triggers_torch_compile(self):
        """On CUDA with torch.compile, UNet gets compiled."""
        pipe = MagicMock()
        original_unet = pipe.unet
        mock_compiled = MagicMock(name="compiled")

        with _patch_heavy() as mock_torch:
            mock_torch.compile.return_value = mock_compiled
            gen_module._apply_performance_opts(pipe, "cuda")
            # Assert inside the block while mock is still active
            mock_torch.compile.assert_called_once()
            call_args, call_kwargs = mock_torch.compile.call_args
            assert call_args[0] is original_unet
            assert call_kwargs["mode"] == "reduce-overhead"

        assert pipe.unet == mock_compiled

    def test_non_cuda_skips_torch_compile(self):
        """On non-CUDA devices, torch.compile is never called."""
        pipe = MagicMock()

        with _patch_heavy() as mock_torch:
            gen_module._apply_performance_opts(pipe, "mps")
            mock_torch.compile.assert_not_called()


# ===================================================================
# 4. Karras sigma scheduler variant
# ===================================================================


class TestKarrasSigmaScheduler:
    """apply_scheduler sets use_karras_sigmas=True for DPMSolverMultistepScheduler."""

    def test_dpm_solver_gets_karras_sigmas(self):
        """DPMSolverMultistepScheduler config must include use_karras_sigmas=True."""
        pipe = MagicMock()
        pipe.scheduler.config = {"some_key": "value"}

        mock_cls = MagicMock()
        mock_cls.from_config.return_value = MagicMock()

        with _patch_heavy():
            mock_diffusers = gen_module.__dict__["diffusers"]
            setattr(mock_diffusers, "DPMSolverMultistepScheduler", mock_cls)
            apply_scheduler(pipe, "DPMSolverMultistepScheduler")

        config_used = mock_cls.from_config.call_args[0][0]
        assert config_used["use_karras_sigmas"] is True

    def test_non_dpm_solver_does_not_set_karras(self):
        """Other schedulers must NOT get use_karras_sigmas injected."""
        pipe = MagicMock()
        pipe.scheduler.config = {"some_key": "value"}

        mock_cls = MagicMock()
        mock_cls.from_config.return_value = MagicMock()

        with _patch_heavy():
            mock_diffusers = gen_module.__dict__["diffusers"]
            setattr(mock_diffusers, "EulerDiscreteScheduler", mock_cls)
            apply_scheduler(pipe, "EulerDiscreteScheduler")

        config_used = mock_cls.from_config.call_args[0][0]
        assert "use_karras_sigmas" not in config_used

    def test_karras_sigmas_with_empty_config(self):
        """DPMSolver with empty scheduler config still gets karras_sigmas."""
        pipe = MagicMock()
        pipe.scheduler.config = {}

        mock_cls = MagicMock()
        mock_cls.from_config.return_value = MagicMock()

        with _patch_heavy():
            mock_diffusers = gen_module.__dict__["diffusers"]
            setattr(mock_diffusers, "DPMSolverMultistepScheduler", mock_cls)
            apply_scheduler(pipe, "DPMSolverMultistepScheduler")

        config_used = mock_cls.from_config.call_args[0][0]
        assert config_used == {"use_karras_sigmas": True}

    def test_karras_preserves_existing_config_keys(self):
        """Karras injection must not clobber existing scheduler config."""
        pipe = MagicMock()
        pipe.scheduler.config = {"beta_schedule": "scaled_linear", "solver_order": 2}

        mock_cls = MagicMock()
        mock_cls.from_config.return_value = MagicMock()

        with _patch_heavy():
            mock_diffusers = gen_module.__dict__["diffusers"]
            setattr(mock_diffusers, "DPMSolverMultistepScheduler", mock_cls)
            apply_scheduler(pipe, "DPMSolverMultistepScheduler")

        config_used = mock_cls.from_config.call_args[0][0]
        assert config_used["beta_schedule"] == "scaled_linear"
        assert config_used["solver_order"] == 2
        assert config_used["use_karras_sigmas"] is True
