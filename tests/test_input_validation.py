"""Tests for input validation hardening (Issues #24, #29, #30).

- #24: Scheduler whitelist — reject names not in SUPPORTED_SCHEDULERS
- #29: Batch schema validation — required keys, types, unexpected-key warnings
- #30: Per-item scheduler and refiner_steps overrides in batch JSON
"""

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import generate as gen_module
from generate import SUPPORTED_SCHEDULERS, apply_scheduler, batch_generate

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cli_args(**overrides):
    """Return a minimal SimpleNamespace matching CLI args shape."""
    defaults = dict(
        steps=22, guidance=6.5, refiner_guidance=5.0,
        scheduler="DPMSolverMultistepScheduler",
        width=1024, height=1024, refine=False,
        negative_prompt="", cpu=True,
        lora=None, lora_weight=0.8, refiner_steps=10,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


@contextmanager
def _patch_heavy():
    """Inject mock torch/diffusers into generate's globals, then restore.

    We inject directly into gen_module.__dict__ to bypass the PEP 562
    __getattr__ which would try to actually ``import torch``.
    """
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


# ===================================================================
# Issue #24 — Scheduler whitelist
# ===================================================================

class TestSchedulerWhitelist:
    """apply_scheduler must reject names not in SUPPORTED_SCHEDULERS."""

    def test_rejects_name_not_in_supported_list(self):
        """Even if diffusers *has* the attribute, non-whitelisted names are rejected."""
        pipe = MagicMock()
        pipe.scheduler.config = {}
        with pytest.raises(ValueError, match="not a supported scheduler"):
            apply_scheduler(pipe, "FooScheduler")

    def test_accepts_every_supported_scheduler(self):
        """All names in SUPPORTED_SCHEDULERS must be accepted (not raise)."""
        for name in SUPPORTED_SCHEDULERS:
            pipe = MagicMock()
            pipe.scheduler.config = {}
            mock_cls = MagicMock()
            mock_cls.from_config.return_value = MagicMock()
            with _patch_heavy():
                mock_diffusers = gen_module.__dict__["diffusers"]
                setattr(mock_diffusers, name, mock_cls)
                apply_scheduler(pipe, name)

    def test_error_message_lists_valid_options(self):
        """The ValueError message must include at least one valid scheduler name."""
        pipe = MagicMock()
        pipe.scheduler.config = {}
        with pytest.raises(ValueError, match="DPMSolverMultistepScheduler"):
            apply_scheduler(pipe, "InvalidSchedulerXYZ")


# ===================================================================
# Issue #29 — Batch schema validation
# ===================================================================

class TestBatchSchemaValidation:
    """batch_generate must validate each item before processing."""

    def test_missing_prompt_key_returns_error_result(self):
        """Item without 'prompt' → error result, batch continues."""
        items = [
            {"output": "out/01.png"},  # missing prompt
            {"prompt": "good", "output": "out/02.png"},
        ]
        with _patch_heavy(), \
             patch("generate.generate_with_retry", side_effect=lambda a: a.output):
            results = batch_generate(items, device="cpu")

        assert len(results) == 2
        assert results[0]["status"] == "error"
        assert "prompt" in results[0]["error"].lower()
        assert results[1]["status"] == "ok"

    def test_missing_output_key_returns_error_result(self):
        """Item without 'output' → error result, batch continues."""
        items = [
            {"prompt": "test"},  # missing output
            {"prompt": "good", "output": "out/02.png"},
        ]
        with _patch_heavy(), \
             patch("generate.generate_with_retry", side_effect=lambda a: a.output):
            results = batch_generate(items, device="cpu")

        assert len(results) == 2
        assert results[0]["status"] == "error"
        assert "output" in results[0]["error"].lower()
        assert results[1]["status"] == "ok"

    def test_prompt_wrong_type_returns_error_result(self):
        """'prompt' must be str — non-string → error."""
        items = [{"prompt": 123, "output": "out/01.png"}]
        with _patch_heavy(), \
             patch("generate.generate_with_retry", side_effect=lambda a: a.output):
            results = batch_generate(items, device="cpu")

        assert results[0]["status"] == "error"
        assert "prompt" in results[0]["error"].lower()

    def test_output_wrong_type_returns_error_result(self):
        """'output' must be str — non-string → error."""
        items = [{"prompt": "test", "output": 42}]
        with _patch_heavy(), \
             patch("generate.generate_with_retry", side_effect=lambda a: a.output):
            results = batch_generate(items, device="cpu")

        assert results[0]["status"] == "error"
        assert "output" in results[0]["error"].lower()

    def test_unexpected_keys_warns(self, capsys):
        """Unexpected keys should print a warning but not fail."""
        items = [{"prompt": "test", "output": "out/01.png", "bogus_key": True}]
        with _patch_heavy(), \
             patch("generate.generate_with_retry", side_effect=lambda a: a.output):
            results = batch_generate(items, device="cpu")

        assert results[0]["status"] == "ok"
        captured = capsys.readouterr()
        assert "bogus_key" in captured.out


# ===================================================================
# Issue #30 — Per-item scheduler and refiner_steps overrides
# ===================================================================

class TestPerItemOverrides:
    """Batch items can override scheduler and refiner_steps per-item."""

    def test_per_item_scheduler_override(self):
        """Item-level 'scheduler' overrides the CLI arg."""
        items = [{"prompt": "test", "output": "out/01.png",
                  "scheduler": "EulerDiscreteScheduler"}]
        captured = {}

        def grab(args):
            captured["scheduler"] = args.scheduler
            return args.output

        cli = _make_cli_args(scheduler="DPMSolverMultistepScheduler")
        with _patch_heavy(), \
             patch("generate.generate_with_retry", side_effect=grab):
            batch_generate(items, device="cpu", args=cli)

        assert captured["scheduler"] == "EulerDiscreteScheduler"

    def test_per_item_scheduler_falls_back_to_cli_arg(self):
        """Without item-level scheduler, the CLI arg is used."""
        items = [{"prompt": "test", "output": "out/01.png"}]
        captured = {}

        def grab(args):
            captured["scheduler"] = args.scheduler
            return args.output

        cli = _make_cli_args(scheduler="DDIMScheduler")
        with _patch_heavy(), \
             patch("generate.generate_with_retry", side_effect=grab):
            batch_generate(items, device="cpu", args=cli)

        assert captured["scheduler"] == "DDIMScheduler"

    def test_per_item_refiner_steps_override(self):
        """Item-level 'refiner_steps' overrides the CLI arg."""
        items = [{"prompt": "test", "output": "out/01.png",
                  "refiner_steps": 25}]
        captured = {}

        def grab(args):
            captured["refiner_steps"] = args.refiner_steps
            return args.output

        cli = _make_cli_args(refiner_steps=10)
        with _patch_heavy(), \
             patch("generate.generate_with_retry", side_effect=grab):
            batch_generate(items, device="cpu", args=cli)

        assert captured["refiner_steps"] == 25

    def test_per_item_refiner_steps_falls_back_to_cli_arg(self):
        """Without item-level refiner_steps, the CLI arg is used."""
        items = [{"prompt": "test", "output": "out/01.png"}]
        captured = {}

        def grab(args):
            captured["refiner_steps"] = args.refiner_steps
            return args.output

        cli = _make_cli_args(refiner_steps=15)
        with _patch_heavy(), \
             patch("generate.generate_with_retry", side_effect=grab):
            batch_generate(items, device="cpu", args=cli)

        assert captured["refiner_steps"] == 15

    def test_per_item_scheduler_default_without_args(self):
        """When no CLI args passed, item scheduler still works."""
        items = [{"prompt": "test", "output": "out/01.png",
                  "scheduler": "HeunDiscreteScheduler"}]
        captured = {}

        def grab(args):
            captured["scheduler"] = args.scheduler
            return args.output

        with _patch_heavy(), \
             patch("generate.generate_with_retry", side_effect=grab):
            batch_generate(items, device="cpu", args=None)

        assert captured["scheduler"] == "HeunDiscreteScheduler"
