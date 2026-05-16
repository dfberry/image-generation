"""test_lora_compatibility.py — Model compatibility enforcement tests.

Covers test cases LC-1 through LC-6 from PRD §15.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from presets import LORAS
from simple_config import check_lora_compatibility, resolve_preset

# ---------------------------------------------------------------------------
# LC-1 — SDXL LoRA + SDXL model → compatible, no exception
# ---------------------------------------------------------------------------


class TestSdxlLoraWithSdxlModel:
    def test_aether_watercolor_precise_no_exception(self):
        """LC-1: SDXL LoRA + SDXL model (precise) → no exception."""
        check_lora_compatibility("aether-watercolor", "precise", LORAS)


# ---------------------------------------------------------------------------
# LC-2 — SDXL LoRA + FLUX.1 model → SystemExit with helpful message
# ---------------------------------------------------------------------------


class TestSdxlLoraWithFluxModel:
    def test_aether_watercolor_creative_raises_system_exit(self):
        """LC-2: SDXL LoRA + FLUX.1 model (creative) → SystemExit."""
        with pytest.raises(SystemExit) as exc_info:
            check_lora_compatibility("aether-watercolor", "creative", LORAS)
        message = str(exc_info.value)
        assert "creative" in message
        assert "sdxl" in message.lower()

    def test_error_message_contains_lora_name(self):
        """LC-2: SystemExit message includes the LoRA name."""
        with pytest.raises(SystemExit) as exc_info:
            check_lora_compatibility("aether-watercolor", "creative", LORAS)
        assert "aether-watercolor" in str(exc_info.value)


# ---------------------------------------------------------------------------
# LC-3 — SDXL LoRA + SD3 model → SystemExit
# ---------------------------------------------------------------------------


class TestSdxlLoraWithSd3Model:
    def test_aether_watercolor_balanced_raises_system_exit(self):
        """LC-3: SDXL LoRA + SD3 model (balanced) → SystemExit."""
        with pytest.raises(SystemExit):
            check_lora_compatibility("aether-watercolor", "balanced", LORAS)


# ---------------------------------------------------------------------------
# LC-4 — Raw HF ID (not in registry) → no check, no exception
# ---------------------------------------------------------------------------


class TestRawHfIdSkipsCheck:
    def test_unknown_lora_id_no_exception(self):
        """LC-4: Raw HF ID not in registry → compatibility check is skipped."""
        # This should not raise regardless of model
        check_lora_compatibility("author/raw-lora-model", "creative", LORAS)
        check_lora_compatibility("some/arbitrary-hf-id", "balanced", LORAS)


# ---------------------------------------------------------------------------
# LC-5 — Compatibility check fires after modifier resolution
# ---------------------------------------------------------------------------


class TestCompatibilityAfterModifierResolution:
    def test_artistic_modifier_sets_creative_then_check_fires(self):
        """LC-5: --modifier artistic → model=creative; SDXL LoRA check fires."""
        params = resolve_preset("standard")
        from presets import apply_modifier  # noqa: PLC0415
        apply_modifier(params, "artistic")
        model_alias = params.get("model")
        assert model_alias == "creative", "artistic modifier should set model=creative"
        with pytest.raises(SystemExit):
            check_lora_compatibility("aether-watercolor", model_alias, LORAS)


# ---------------------------------------------------------------------------
# LC-6 — Error message quality: contains LoRA name, model type, corrective suggestion
# ---------------------------------------------------------------------------


class TestErrorMessageQuality:
    def test_error_contains_lora_name_model_type_and_suggestion(self):
        """LC-6: SystemExit message includes LoRA name, current model type, and correction."""
        with pytest.raises(SystemExit) as exc_info:
            check_lora_compatibility("aether-watercolor", "creative", LORAS)
        message = str(exc_info.value)
        assert "aether-watercolor" in message, "Error must name the LoRA"
        assert "flux" in message.lower() or "creative" in message, "Error must name the model type"
        # Corrective suggestion
        assert "precise" in message.lower() or "sdxl" in message.lower(), (
            "Error must suggest the correct model type"
        )
