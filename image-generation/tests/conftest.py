"""
Shared fixtures and mock utilities for generate.py regression tests.

Mocking strategy:
    Every test automatically gets ``_patch_heavy_imports`` (autouse) which:
    1. Injects mock ``torch``, ``diffusers``, and ``DiffusionPipeline`` into
       the ``generate`` module dict so PEP-562 ``__getattr__`` never fires.
    2. Replaces ``_ensure_heavy_imports()`` with a no-op so functions like
       ``generate()``, ``load_base()``, ``get_dtype()`` etc. skip the real
       ``import torch`` / ``import diffusers``.

    Individual tests can still do ``@patch("generate.torch")`` or
    ``patch("generate.torch.cuda.empty_cache")`` on top — the autouse
    fixture guarantees ``generate.torch`` already exists as a MagicMock.
"""

import os
import sys

# Ensure the image-generation/ package root is on sys.path so
# `import generate` resolves regardless of the working directory
# from which pytest is invoked (repo root or image-generation/).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import MagicMock

import pytest


class MockImage:
    """Minimal PIL Image stand-in."""

    def save(self, path):
        pass


class MockPipeline:
    """
    Stand-in for a DiffusionPipeline.

    Calling the pipeline returns an object whose .images attribute contains
    either a list of MockImage (base/refiner path) or a mock latent tensor.
    """

    def __init__(self, return_latents=False):
        self.text_encoder_2 = MagicMock()
        self.vae = MagicMock()
        self.unet = MagicMock()
        self.scheduler = MagicMock()
        self.safety_checker = None
        self._return_latents = return_latents

    def __call__(self, **kwargs):
        result = MagicMock()
        if self._return_latents:
            latent = MagicMock()
            latent.cpu.return_value = latent
            latent.to.return_value = latent
            result.images = latent
        else:
            result.images = [MockImage()]
        return result

    def to(self, device):
        return self

    def enable_model_cpu_offload(self):
        pass

    def enable_attention_slicing(self):
        pass

    def enable_xformers_memory_efficient_attention(self):
        pass

    def load_lora_weights(self, *args, **kwargs):
        pass

    def set_adapters(self, *args, **kwargs):
        pass


@pytest.fixture()
def mock_args_base(tmp_path):
    """Args for base-only generation (no refiner)."""
    args = MagicMock()
    args.refine = False
    args.cpu = True
    args.seed = None
    args.output = str(tmp_path / "out.png")
    args.prompt = "test prompt"
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


@pytest.fixture()
def mock_args_refine(tmp_path):
    """Args for base+refiner generation."""
    args = MagicMock()
    args.refine = True
    args.cpu = True
    args.seed = None
    args.output = str(tmp_path / "out.png")
    args.prompt = "test prompt"
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


@pytest.fixture()
def mock_args_cuda(tmp_path):
    """Args for CUDA device generation (base-only)."""
    args = MagicMock()
    args.refine = False
    args.cpu = False
    args.seed = None
    args.output = str(tmp_path / "out.png")
    args.prompt = "test prompt"
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


@pytest.fixture()
def mock_args_cuda_refine(tmp_path):
    """Args for CUDA device with base+refiner."""
    args = MagicMock()
    args.refine = True
    args.cpu = False
    args.seed = None
    args.output = str(tmp_path / "out.png")
    args.prompt = "test prompt"
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


# ---------------------------------------------------------------------------
# Auto-use fixture: prevent real torch/diffusers imports in ALL tests
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _patch_heavy_imports():
    """Inject mock torch/diffusers into ``generate`` module for every test.

    This runs automatically before each test function. It:
    1. Sets ``generate.torch`` / ``generate.diffusers`` /
       ``generate.DiffusionPipeline`` to MagicMock objects.
    2. Replaces ``_ensure_heavy_imports()`` with a no-op.
    3. Restores originals in teardown.

    Individual tests can layer additional patches on top (e.g.
    ``@patch("generate.torch")``), which is safe because this fixture
    guarantees the attribute already exists in the module dict.
    """
    import generate as gen_mod

    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = False
    mock_torch.backends.mps.is_available.return_value = False

    # Make OutOfMemoryError a real exception class so isinstance() works
    # in generate.py's except block.
    class _MockCudaOOM(RuntimeError):
        pass
    mock_torch.cuda.OutOfMemoryError = _MockCudaOOM

    mock_diffusers = MagicMock()
    mock_dp = MagicMock()

    # Snapshot current state
    _saved = {}
    for attr in ("torch", "diffusers", "DiffusionPipeline"):
        _saved[attr] = (attr in vars(gen_mod), vars(gen_mod).get(attr))

    # Inject mocks (bypass __getattr__)
    gen_mod.__dict__["torch"] = mock_torch
    gen_mod.__dict__["diffusers"] = mock_diffusers
    gen_mod.__dict__["DiffusionPipeline"] = mock_dp

    original_ensure = gen_mod._ensure_heavy_imports
    gen_mod._ensure_heavy_imports = lambda: None

    try:
        yield mock_torch
    finally:
        gen_mod._ensure_heavy_imports = original_ensure
        for attr, (existed, old_val) in _saved.items():
            if existed:
                gen_mod.__dict__[attr] = old_val
            else:
                gen_mod.__dict__.pop(attr, None)
