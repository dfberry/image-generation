"""Scheduler optimisation tests (Issue #6)."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from generate import apply_scheduler, parse_args
from tests.conftest import MockPipeline


def _parse_with_args(cli_args):
    with patch.object(sys, "argv", ["generate.py"] + cli_args):
        return parse_args()


class TestSchedulerCLIFlag:
    def test_scheduler_flag_exists_with_default(self):
        args = _parse_with_args(["--prompt", "test"])
        assert hasattr(args, "scheduler")

    def test_scheduler_default_is_dpm_solver(self):
        args = _parse_with_args(["--prompt", "test"])
        assert args.scheduler == "DPMSolverMultistepScheduler"

    def test_scheduler_accepts_custom_value(self):
        args = _parse_with_args(["--prompt", "test", "--scheduler", "EulerDiscreteScheduler"])
        assert args.scheduler == "EulerDiscreteScheduler"

    def test_scheduler_accepts_ddim(self):
        args = _parse_with_args(["--prompt", "test", "--scheduler", "DDIMScheduler"])
        assert args.scheduler == "DDIMScheduler"


class TestDefaultStepsChanged:
    def test_default_steps_is_22(self):
        args = _parse_with_args(["--prompt", "test"])
        assert args.steps == 22

    def test_explicit_steps_still_honoured(self):
        args = _parse_with_args(["--prompt", "test", "--steps", "50"])
        assert args.steps == 50


class TestSchedulerApplied:
    def test_base_pipeline_scheduler_is_set(self, mock_args_base):
        mock_args_base.scheduler = "DPMSolverMultistepScheduler"
        base = MockPipeline(return_latents=False)
        base.scheduler = MagicMock()
        mock_scheduler_cls = MagicMock()
        mock_scheduler_cls.from_config.return_value = MagicMock()
        import generate as gen
        with patch("generate.load_base", return_value=base), \
             patch("generate.gc"), \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.cuda.is_available", return_value=False), \
             patch("generate.torch.backends.mps.is_available", return_value=False), \
             patch("diffusers.DPMSolverMultistepScheduler", mock_scheduler_cls, create=True):
            gen.generate(mock_args_base)
        assert mock_scheduler_cls.from_config.called

    def test_refiner_path_also_sets_scheduler_on_base(self, mock_args_refine):
        mock_args_refine.scheduler = "DPMSolverMultistepScheduler"
        base = MockPipeline(return_latents=True)
        base.scheduler = MagicMock()
        base.scheduler.config = {"some": "config"}
        refiner = MockPipeline(return_latents=False)
        mock_scheduler_cls = MagicMock()
        mock_scheduler_cls.from_config.return_value = MagicMock()
        import generate as gen
        with patch("generate.load_base", return_value=base), \
             patch("generate.load_refiner", return_value=refiner), \
             patch("generate.gc"), \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.cuda.is_available", return_value=False), \
             patch("generate.torch.backends.mps.is_available", return_value=False), \
             patch("diffusers.DPMSolverMultistepScheduler", mock_scheduler_cls, create=True):
            gen.generate(mock_args_refine)
        assert mock_scheduler_cls.from_config.called


class TestRefinerGuidance:
    def test_refiner_guidance_flag_exists(self):
        args = _parse_with_args(["--prompt", "test"])
        assert hasattr(args, "refiner_guidance")

    def test_refiner_guidance_default_is_5(self):
        args = _parse_with_args(["--prompt", "test"])
        assert args.refiner_guidance == 5.0

    def test_refiner_guidance_cli_override(self):
        args = _parse_with_args(["--prompt", "test", "--refiner-guidance", "3.0"])
        assert args.refiner_guidance == 3.0

    def test_refiner_uses_independent_guidance_in_generate(self, mock_args_refine):
        mock_args_refine.scheduler = "DPMSolverMultistepScheduler"
        mock_args_refine.refiner_guidance = 5.0
        mock_args_refine.guidance = 7.5
        base = MockPipeline(return_latents=True)
        base.scheduler = MagicMock()
        base.scheduler.config = {}

        # Use MagicMock for refiner so we can inspect call_args
        mock_image = MagicMock()
        refiner_result = MagicMock()
        refiner_result.images = [mock_image]
        refiner = MagicMock(spec=MockPipeline())
        refiner.return_value = refiner_result
        refiner.text_encoder_2 = MagicMock()
        refiner.vae = MagicMock()

        import generate as gen
        with patch("generate.load_base", return_value=base), \
             patch("generate.load_refiner", return_value=refiner), \
             patch("generate.gc"), \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.cuda.is_available", return_value=False), \
             patch("generate.torch.backends.mps.is_available", return_value=False):
            gen.generate(mock_args_refine)
        refiner.assert_called_once()
        refiner_kwargs = refiner.call_args.kwargs
        assert "guidance_scale" in refiner_kwargs
        assert refiner_kwargs["guidance_scale"] == 5.0


class TestBatchGenerateDefaults:
    def test_batch_generate_uses_22_steps(self):
        import generate as gen
        cap = {}
        def mg(args):
            cap["steps"] = args.steps
            return args.output
        with patch("generate.generate_with_retry", side_effect=mg):
            gen.batch_generate([{"prompt": "t", "output": "o.png"}], device="cpu")
        assert cap["steps"] == 22

    def test_batch_generate_forwards_scheduler(self):
        from types import SimpleNamespace

        import generate as gen
        cap = {}
        def mg(args):
            cap["scheduler"] = args.scheduler
            return args.output
        cli = SimpleNamespace(steps=28, guidance=7.5, refiner_guidance=5.0,
            scheduler="EulerDiscreteScheduler", width=1024, height=1024,
            refine=False, negative_prompt="", cpu=True)
        with patch("generate.generate_with_retry", side_effect=mg):
            gen.batch_generate([{"prompt": "t", "output": "o.png"}], device="cpu", args=cli)
        assert cap["scheduler"] == "EulerDiscreteScheduler"


class TestInvalidSchedulerHandling:
    def test_invalid_scheduler_raises_value_error(self):
        p = MockPipeline(return_latents=False)
        with pytest.raises(ValueError, match="Unknown scheduler"):
            apply_scheduler(p, "NotARealScheduler")

    def test_invalid_scheduler_error_lists_available(self):
        p = MockPipeline(return_latents=False)
        with pytest.raises(ValueError, match="DPMSolverMultistepScheduler"):
            apply_scheduler(p, "FakeScheduler123")

    def test_invalid_scheduler_does_not_raise_attribute_error(self):
        p = MockPipeline(return_latents=False)
        try:
            apply_scheduler(p, "CompletelyBogusScheduler")
            pytest.fail("Expected ValueError for bogus scheduler name")
        except ValueError:
            pass
        except AttributeError:
            pytest.fail("Got raw AttributeError")

    def test_invalid_scheduler_in_generate_raises_value_error(self, mock_args_base):
        mock_args_base.scheduler = "TotallyFakeScheduler"
        base = MockPipeline(return_latents=False)
        import generate as gen
        with patch("generate.load_base", return_value=base), \
             patch("generate.gc"), \
             patch("generate.torch.cuda.empty_cache"), \
             patch("generate.torch.cuda.is_available", return_value=False), \
             patch("generate.torch.backends.mps.is_available", return_value=False):
            with pytest.raises(ValueError, match="Unknown scheduler"):
                gen.generate(mock_args_base)
