"""
Shared fixtures and mock utilities for generate.py regression tests.
"""

import types
from unittest.mock import MagicMock, patch

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
