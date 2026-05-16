"""test_presets.py — Unit tests for presets.py mapping tables and helpers.

Covers all 12 test cases from PRD §13 (Unit Tests).
"""

from __future__ import annotations

import pytest

from presets import (
    PRESETS,
    SIZES,
    STYLES,
    apply_modifier,
    apply_style_tokens,
    check_guidance_warning,
    estimate_tokens,
    resolve_preset,
)

_REQUIRED_KEYS = {"steps", "refine", "refiner_steps", "guidance", "refiner_guidance", "scheduler"}


# ---------------------------------------------------------------------------
# Test 1 — Preset completeness
# ---------------------------------------------------------------------------


class TestPresetCompleteness:
    def test_all_presets_have_required_keys(self):
        """Every preset must have all required parameter keys."""
        for name, preset in PRESETS.items():
            missing = _REQUIRED_KEYS - preset.keys()
            assert not missing, f"Preset '{name}' is missing keys: {missing}"


# ---------------------------------------------------------------------------
# Test 2 — Preset values
# ---------------------------------------------------------------------------


class TestPresetValues:
    def test_production_preset_values(self):
        params = resolve_preset("production")
        assert params["steps"] == 35
        assert params["refine"] is True
        assert params["refiner_steps"] == 15

    def test_quick_draft_preset_values(self):
        params = resolve_preset("quick-draft")
        assert params["steps"] == 15
        assert params["refine"] is False

    def test_standard_preset_values(self):
        params = resolve_preset("standard")
        assert params["steps"] == 22
        assert params["guidance"] == 6.5
        assert params["refine"] is False

    def test_high_quality_preset_values(self):
        params = resolve_preset("high-quality")
        assert params["steps"] == 35
        assert params["refine"] is False


# ---------------------------------------------------------------------------
# Test 3 — Modifier: guidance absolute override
# ---------------------------------------------------------------------------


class TestModifierGuidanceOverride:
    def test_dreamier_sets_guidance_4_0(self):
        """dreamier overrides guidance to 4.0; steps unchanged."""
        params = resolve_preset("standard")
        apply_modifier(params, "dreamier")
        assert params["guidance"] == 4.0
        assert params["steps"] == 22

    def test_softer_sets_guidance_5_0(self):
        params = resolve_preset("standard")
        apply_modifier(params, "softer")
        assert params["guidance"] == 5.0

    def test_crisper_sets_guidance_7_5(self):
        params = resolve_preset("standard")
        apply_modifier(params, "crisper")
        assert params["guidance"] == 7.5


# ---------------------------------------------------------------------------
# Test 4 — Modifier: steps delta below threshold (no refine auto-enable)
# ---------------------------------------------------------------------------


class TestModifierStepsDeltaBelowThreshold:
    def test_more_detailed_on_quick_draft_stays_below_30(self):
        """more-detailed on quick-draft: steps=15+10=25; refine remains False (25 < 30)."""
        params = resolve_preset("quick-draft")
        apply_modifier(params, "more-detailed")
        assert params["steps"] == 25
        assert params["refine"] is False


# ---------------------------------------------------------------------------
# Test 5 — Modifier: steps delta crosses threshold (auto-enable refine)
# ---------------------------------------------------------------------------


class TestModifierStepsDeltaThresholdCrossed:
    def test_more_detailed_on_standard_enables_refine(self):
        """more-detailed on standard: steps=22+10=32 ≥ 30 → refine auto-enabled."""
        params = resolve_preset("standard")
        apply_modifier(params, "more-detailed")
        assert params["steps"] == 32
        assert params["refine"] is True


# ---------------------------------------------------------------------------
# Test 6 — Modifier: double application
# ---------------------------------------------------------------------------


class TestModifierDoubleApplication:
    def test_more_detailed_twice_on_quick_draft(self):
        """Two more-detailed applications on quick-draft: 15+10=25+10=35 ≥ 30 → refine=True."""
        params = resolve_preset("quick-draft")
        apply_modifier(params, "more-detailed")
        apply_modifier(params, "more-detailed")
        assert params["steps"] == 35
        assert params["refine"] is True


# ---------------------------------------------------------------------------
# Test 7 — Style token injection: watercolor
# ---------------------------------------------------------------------------


class TestStyleWatercolor:
    def test_watercolor_prepends_tokens(self):
        """watercolor style prepends the canonical token string before user prompt."""
        user_prompt = "A developer at a standing desk, warm afternoon light, no text"
        final_prompt, lora, lw, passthrough = apply_style_tokens(user_prompt, "watercolor")
        assert final_prompt.startswith("Watercolor illustration,")
        assert user_prompt in final_prompt
        # token must be separated by space (tokens end with comma, so "..., user prompt")
        assert final_prompt.index(user_prompt) > 0
        assert lora == "joachim_s/aether-watercolor-and-ink-sdxl"
        assert lw == 0.8
        assert passthrough is None

    def test_watercolor_exact_token_prefix(self):
        expected_tokens = STYLES["watercolor"]["tokens"]
        user_prompt = "test prompt"
        final_prompt, _, _, _ = apply_style_tokens(user_prompt, "watercolor")
        assert final_prompt.startswith(expected_tokens)
        assert final_prompt == f"{expected_tokens} {user_prompt}"


# ---------------------------------------------------------------------------
# Test 8 — Style token injection: folk-art
# ---------------------------------------------------------------------------


class TestStyleFolkArt:
    def test_folk_art_prepends_canonical_tokens(self):
        """folk-art prepends its canonical anchor tokens."""
        user_prompt = "A team meeting, evening light, no text"
        final_prompt, lora, lw, passthrough = apply_style_tokens(user_prompt, "folk-art")
        assert final_prompt.startswith("Latin American folk art style,")
        assert user_prompt in final_prompt
        assert lora is None
        assert passthrough is None

    def test_default_style_is_folk_art(self):
        """When style_name is None (and no_default_style=False), folk-art is applied."""
        user_prompt = "A mountain at dusk, no text"
        default_prompt, _, _, _ = apply_style_tokens(user_prompt, None)
        folk_art_prompt, _, _, _ = apply_style_tokens(user_prompt, "folk-art")
        assert default_prompt == folk_art_prompt


# ---------------------------------------------------------------------------
# Test 9 — Size resolution
# ---------------------------------------------------------------------------


class TestSizeResolution:
    def test_blog_hero_dimensions(self):
        """blog-hero → width=1200, height=632 (both divisible by 8)."""
        size = SIZES["blog-hero"]
        assert size["width"] == 1200
        assert size["height"] == 632

    def test_all_sizes_divisible_by_8(self):
        """All size presets must produce dimensions divisible by 8 (generate.py requirement)."""
        for name, dims in SIZES.items():
            assert dims["width"] % 8 == 0, f"{name} width={dims['width']} not divisible by 8"
            assert dims["height"] % 8 == 0, f"{name} height={dims['height']} not divisible by 8"

    def test_square_is_1024_by_1024(self):
        assert SIZES["square"] == {"width": 1024, "height": 1024}


# ---------------------------------------------------------------------------
# Test 10 — No-default-style flag
# ---------------------------------------------------------------------------


class TestNoDefaultStyle:
    def test_no_default_style_passes_prompt_through_unchanged(self):
        """With no_default_style=True, prompt is returned without any token prepending."""
        user_prompt = "A robot painting, no text"
        final_prompt, lora, lw, passthrough = apply_style_tokens(user_prompt, None, no_default_style=True)
        assert final_prompt == user_prompt
        assert lora is None
        assert passthrough is None

    def test_style_none_is_equivalent_to_no_default_style(self):
        """--style none is an alias for --no-default-style."""
        user_prompt = "A scenic landscape, no text"
        no_default, _, _, _ = apply_style_tokens(user_prompt, None, no_default_style=True)
        style_none, _, _, _ = apply_style_tokens(user_prompt, "none")
        assert no_default == style_none == user_prompt


# ---------------------------------------------------------------------------
# Test 11 — Guidance warning trigger
# ---------------------------------------------------------------------------


class TestGuidanceWarning:
    def test_sharper_without_precise_model_triggers_warning(self):
        """guidance=8.0 without model=precise → warning returned, not exception."""
        params = resolve_preset("standard")
        apply_modifier(params, "sharper")
        assert params["guidance"] == 8.0
        warnings = check_guidance_warning(params)
        assert len(warnings) == 1
        assert "over-saturation" in warnings[0]

    def test_photorealistic_suppresses_warning(self):
        """photorealistic sets model=precise, which suppresses the guidance warning."""
        params = resolve_preset("standard")
        apply_modifier(params, "photorealistic")
        warnings = check_guidance_warning(params)
        assert warnings == []

    def test_crisper_7_5_no_warning(self):
        """guidance=7.5 is at the boundary — warning triggers only for > 7.5."""
        params = resolve_preset("standard")
        apply_modifier(params, "crisper")
        assert params["guidance"] == 7.5
        warnings = check_guidance_warning(params)
        assert warnings == []


# ---------------------------------------------------------------------------
# Test 12 — Modifier left-to-right precedence (last absolute wins)
# ---------------------------------------------------------------------------


class TestModifierPrecedence:
    def test_crisper_then_dreamier_dreamier_wins(self):
        """crisper (guidance=7.5) then dreamier (guidance=4.0) → dreamier wins (4.0)."""
        params = resolve_preset("standard")
        apply_modifier(params, "crisper")
        apply_modifier(params, "dreamier")
        assert params["guidance"] == 4.0

    def test_dreamier_then_crisper_crisper_wins(self):
        """dreamier (guidance=4.0) then crisper (guidance=7.5) → crisper wins (7.5)."""
        params = resolve_preset("standard")
        apply_modifier(params, "dreamier")
        apply_modifier(params, "crisper")
        assert params["guidance"] == 7.5

    def test_less_detailed_floor(self):
        """less-detailed: steps cannot go below 10."""
        params = resolve_preset("quick-draft")  # steps=15
        apply_modifier(params, "less-detailed")
        assert params["steps"] == 10  # max(15-5, 10) = 10

    def test_less_detailed_floor_at_10_steps(self):
        """Applying less-detailed when steps are already at 10 stays at 10."""
        params = resolve_preset("quick-draft")  # steps=15
        # Drive steps to 10
        apply_modifier(params, "less-detailed")
        apply_modifier(params, "less-detailed")
        assert params["steps"] == 10  # cannot go below floor

    def test_unknown_modifier_raises(self):
        params = resolve_preset("standard")
        with pytest.raises(ValueError, match="Unknown modifier"):
            apply_modifier(params, "nonexistent-modifier")

    def test_unknown_preset_raises(self):
        with pytest.raises(ValueError, match="Unknown preset"):
            resolve_preset("ultra-mega-quality")


# ---------------------------------------------------------------------------
# Test 13 — estimate_tokens null/empty guard
# ---------------------------------------------------------------------------


class TestEstimateTokensNullGuard:
    def test_none_returns_zero(self):
        """estimate_tokens(None) must return 0, not raise TypeError."""
        assert estimate_tokens(None) == 0

    def test_empty_string_returns_zero(self):
        """estimate_tokens('') must return 0."""
        assert estimate_tokens("") == 0


# ---------------------------------------------------------------------------
# Test 14 — fast modifier resets refiner_steps
# ---------------------------------------------------------------------------


class TestFastModifierRefinerSteps:
    def test_fast_on_production_resets_refiner_steps(self):
        """fast modifier must reset refiner_steps to 10 when applied to production preset."""
        params = resolve_preset("production")
        assert params["refiner_steps"] == 15
        apply_modifier(params, "fast")
        assert params["refine"] is False
        assert params["steps"] == 15
        assert params["refiner_steps"] == 10


# ---------------------------------------------------------------------------
# Test 15 (TP-11) — LoRA registry loading
# ---------------------------------------------------------------------------


class TestLoraRegistryLoading:
    def test_load_loras_returns_dict_with_aether_watercolor(self):
        """TP-11: load_loras() returns a dict containing 'aether-watercolor'."""
        from presets import load_loras  # noqa: PLC0415

        loras = load_loras()
        assert isinstance(loras, dict)
        assert "aether-watercolor" in loras

    def test_aether_watercolor_has_required_fields(self):
        """TP-11: The 'aether-watercolor' entry has model_id, default_weight, compatible_models."""
        from presets import load_loras  # noqa: PLC0415

        loras = load_loras()
        entry = loras["aether-watercolor"]
        assert "model_id" in entry
        assert "default_weight" in entry
        assert "compatible_models" in entry


# ---------------------------------------------------------------------------
# Test 16 (TP-12) — LoRA name resolution
# ---------------------------------------------------------------------------


class TestLoraNameResolution:
    def test_aether_watercolor_resolves_to_correct_hf_model_id(self):
        """TP-12: LORAS['aether-watercolor']['model_id'] == correct HuggingFace model ID."""
        from presets import LORAS  # noqa: PLC0415

        assert LORAS["aether-watercolor"]["model_id"] == "joachim_s/aether-watercolor-and-ink-sdxl"


# ---------------------------------------------------------------------------
# Test 17 (TP-13) — Weight alias: strong → 0.9
# ---------------------------------------------------------------------------


class TestWeightAliasStrong:
    def test_strong_resolves_to_0_9(self):
        """TP-13: resolve_lora_weight('strong') == 0.9."""
        from presets import resolve_lora_weight  # noqa: PLC0415

        assert resolve_lora_weight("strong") == 0.9


# ---------------------------------------------------------------------------
# Test 18 (TP-14) — Weight alias: raw float passthrough
# ---------------------------------------------------------------------------


class TestWeightAliasRawFloat:
    def test_raw_float_string_resolves_correctly(self):
        """TP-14: resolve_lora_weight('0.75') == 0.75."""
        from presets import resolve_lora_weight  # noqa: PLC0415

        assert resolve_lora_weight("0.75") == 0.75

    def test_float_instance_passthrough(self):
        """TP-14: resolve_lora_weight(0.8) returns 0.8 (float instance passthrough)."""
        from presets import resolve_lora_weight  # noqa: PLC0415

        assert resolve_lora_weight(0.8) == 0.8


# ---------------------------------------------------------------------------
# Test 19 (TP-15) — Unknown intensity raises ValueError
# ---------------------------------------------------------------------------


class TestWeightAliasUnknown:
    def test_unknown_alias_raises_value_error(self):
        """TP-15: resolve_lora_weight('very-strong') raises ValueError."""
        from presets import resolve_lora_weight  # noqa: PLC0415

        with pytest.raises(ValueError, match="Unknown LoRA weight"):
            resolve_lora_weight("very-strong")

