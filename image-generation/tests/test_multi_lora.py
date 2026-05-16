"""
Unit tests for multi-LoRA adapter naming and _build_lora_list().

Tests TML-01 through TML-08 per PRD §9.2.
All tests mock the diffusion pipeline — no GPU required.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, call

from generate import _build_lora_list, apply_lora


class TestApplyLora:
    """apply_lora() assigns unique adapter names lora_0, lora_1, ..."""

    def test_single_lora_uses_lora_0_adapter_name(self):
        """TML-01: Single --lora call assigns adapter name 'lora_0', not 'default'."""
        pipeline = MagicMock()
        apply_lora(pipeline, [("hf/model-a", 0.8)])
        pipeline.load_lora_weights.assert_called_once_with("hf/model-a", adapter_name="lora_0")
        pipeline.set_adapters.assert_called_once_with(["lora_0"], adapter_weights=[0.8])

    def test_two_loras_assign_lora_0_and_lora_1(self):
        """TML-02: Two --lora calls assign 'lora_0' and 'lora_1' — no collision."""
        pipeline = MagicMock()
        apply_lora(pipeline, [("hf/model-a", 0.8), ("hf/model-b", 0.6)])
        calls = pipeline.load_lora_weights.call_args_list
        assert calls[0] == call("hf/model-a", adapter_name="lora_0")
        assert calls[1] == call("hf/model-b", adapter_name="lora_1")
        pipeline.set_adapters.assert_called_once_with(
            ["lora_0", "lora_1"], adapter_weights=[0.8, 0.6]
        )

    def test_three_loras_assign_sequential_names(self):
        """TML-03: Three LoRAs get lora_0, lora_1, lora_2."""
        pipeline = MagicMock()
        loras = [("hf/a", 0.8), ("hf/b", 0.7), ("hf/c", 0.6)]
        apply_lora(pipeline, loras)
        calls = pipeline.load_lora_weights.call_args_list
        assert calls[0] == call("hf/a", adapter_name="lora_0")
        assert calls[1] == call("hf/b", adapter_name="lora_1")
        assert calls[2] == call("hf/c", adapter_name="lora_2")
        pipeline.set_adapters.assert_called_once_with(
            ["lora_0", "lora_1", "lora_2"], adapter_weights=[0.8, 0.7, 0.6]
        )

    def test_empty_lora_list_does_nothing(self):
        """TML-04: apply_lora(pipeline, []) calls neither load_lora_weights nor set_adapters."""
        pipeline = MagicMock()
        apply_lora(pipeline, [])
        pipeline.load_lora_weights.assert_not_called()
        pipeline.set_adapters.assert_not_called()

    def test_set_adapters_called_with_all_names_and_weights(self):
        """TML-08: apply_lora with 2 LoRAs verifies set_adapters(['lora_0','lora_1'], [0.8, 0.6])."""
        pipeline = MagicMock()
        apply_lora(pipeline, [("hf/a", 0.8), ("hf/b", 0.6)])
        pipeline.set_adapters.assert_called_once_with(
            ["lora_0", "lora_1"], adapter_weights=[0.8, 0.6]
        )


class TestBuildLoraList:
    """_build_lora_list() normalizes CLI args into list[tuple[str, float]]."""

    def test_lora_weight_defaults_to_0_8_when_not_specified(self):
        """TML-05: _build_lora_list with one LoRA and no weight -> weight is 0.8."""
        args = SimpleNamespace(lora=["hf/model-a"], lora_weight=None)
        result = _build_lora_list(args)
        assert result == [("hf/model-a", 0.8)]

    def test_lora_weight_list_shorter_than_lora_list_pads_with_0_8(self):
        """TML-06: 3 LoRAs, 1 weight -> weights are [w, 0.8, 0.8]."""
        args = SimpleNamespace(lora=["hf/a", "hf/b", "hf/c"], lora_weight=[0.7])
        result = _build_lora_list(args)
        assert len(result) == 3
        assert result[0] == ("hf/a", 0.7)
        assert result[1] == ("hf/b", 0.8)
        assert result[2] == ("hf/c", 0.8)

    def test_scalar_lora_string_wrapped_in_list(self):
        """TML-07: _build_lora_list with args.lora = 'hf/model' (str, not list) -> [('hf/model', 0.8)]."""
        args = SimpleNamespace(lora="hf/model", lora_weight=None)
        result = _build_lora_list(args)
        assert result == [("hf/model", 0.8)]

    def test_none_lora_returns_empty_list(self):
        """_build_lora_list with args.lora=None returns []."""
        args = SimpleNamespace(lora=None, lora_weight=None)
        result = _build_lora_list(args)
        assert result == []

    def test_multiple_loras_with_matching_weights(self):
        """Multiple LoRAs with matching weight count."""
        args = SimpleNamespace(lora=["hf/a", "hf/b"], lora_weight=[0.9, 0.5])
        result = _build_lora_list(args)
        assert result == [("hf/a", 0.9), ("hf/b", 0.5)]

    def test_scalar_lora_weight_applies_to_first_only(self):
        """Single float weight (legacy) applies to lora_0, rest get 0.8."""
        args = SimpleNamespace(lora=["hf/a", "hf/b"], lora_weight=0.7)
        result = _build_lora_list(args)
        assert result[0] == ("hf/a", 0.7)
        assert result[1] == ("hf/b", 0.8)
