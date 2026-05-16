"""presets.py — Data module for simple_config.py.

Defines PRESETS, MODIFIERS, STYLES, SIZES, and PROMPT_TEMPLATES mapping tables,
plus helper functions for resolving and applying them.
"""

from __future__ import annotations

import re

_REQUIRED_PRESET_KEYS = frozenset({"steps", "refine", "refiner_steps", "guidance", "refiner_guidance", "scheduler"})

PRESETS: dict[str, dict] = {
    "quick-draft": {
        "steps": 15,
        "refine": False,
        "refiner_steps": 10,
        "guidance": 6.5,
        "refiner_guidance": 5.0,
        "scheduler": "DPMSolverMultistepScheduler",
    },
    "standard": {
        "steps": 22,
        "refine": False,
        "refiner_steps": 10,
        "guidance": 6.5,
        "refiner_guidance": 5.0,
        "scheduler": "DPMSolverMultistepScheduler",
    },
    "high-quality": {
        "steps": 35,
        "refine": False,
        "refiner_steps": 10,
        "guidance": 6.5,
        "refiner_guidance": 5.0,
        "scheduler": "DPMSolverMultistepScheduler",
    },
    "production": {
        "steps": 35,
        "refine": True,
        "refiner_steps": 15,
        "guidance": 6.5,
        "refiner_guidance": 5.0,
        "scheduler": "DPMSolverMultistepScheduler",
    },
}

MODIFIERS: dict[str, dict] = {
    "dreamier": {"guidance": 4.0},
    "softer": {"guidance": 5.0},
    "crisper": {"guidance": 7.5},
    "sharper": {"guidance": 8.0},
    "photorealistic": {"guidance": 9.0, "model": "precise"},
    "more-detailed": {"steps_delta": +10, "refine_if_steps_gte": 30},
    "less-detailed": {"steps_delta": -5, "steps_min": 10},
    "artistic": {"model": "creative"},
    "fast": {"steps": 15, "refine": False},
}

STYLES: dict[str, dict] = {
    "watercolor": {
        "tokens": "Watercolor illustration, soft wet-on-wet washes, visible paper texture, warm muted tones, loose brushwork,",
        "lora": "joachim_s/aether-watercolor-and-ink-sdxl",
        "lora_weight": 0.8,
    },
    "folk-art": {
        "tokens": "Latin American folk art style, magical realism illustration,",
        "lora": None,
        "lora_weight": None,
    },
    "oil-painting": {"passthrough": True},
    "sketch": {"passthrough": True},
    "anime": {"passthrough": True},
}

SIZES: dict[str, dict] = {
    "square": {"width": 1024, "height": 1024},
    "blog-hero": {"width": 1200, "height": 632},
    "wide": {"width": 1280, "height": 720},
    "portrait": {"width": 768, "height": 1024},
    "tall": {"width": 832, "height": 1216},
}

PROMPT_TEMPLATES: dict[str, str] = {
    "blog-hero": "[SUBJECT] in a [SETTING], [LIGHTING] light, [MOOD] atmosphere, no text",
    "section-illustration": "[CONCEPT] represented as [VISUAL METAPHOR], [COLOR PALETTE] colors, no text",
    "concept-diagram": "[PROCESS OR RELATIONSHIP] shown as [DIAGRAM STYLE], clean composition, no text",
    "portrait": "[PERSON OR CHARACTER] at [LOCATION], [EXPRESSION], [LIGHTING], no text",
}

_VAGUE_COLOR_WORDS = frozenset({
    "blue",
    "red",
    "green",
    "yellow",
    "purple",
    "orange",
    "pink",
    "brown",
    "black",
    "white",
    "gray",
    "grey",
})


def _validate_presets() -> None:
    """Raise ValueError at import time if any preset is missing a required key."""
    for name, preset in PRESETS.items():
        missing = _REQUIRED_PRESET_KEYS - preset.keys()
        if missing:
            raise ValueError(f"Preset '{name}' is missing required keys: {missing}")


_validate_presets()


def resolve_preset(name: str) -> dict:
    """Return a mutable copy of the named preset's parameters.

    Raises ValueError if name is not a known preset.
    """
    if name not in PRESETS:
        raise ValueError(f"Unknown preset '{name}'. Available: {sorted(PRESETS)}")
    return dict(PRESETS[name])


def apply_modifier(params: dict, modifier_name: str) -> None:
    """Apply a single named modifier to params in-place.

    Raises ValueError if modifier_name is unknown.
    """
    if modifier_name not in MODIFIERS:
        raise ValueError(f"Unknown modifier '{modifier_name}'. Available: {sorted(MODIFIERS)}")
    mod = MODIFIERS[modifier_name]
    if "guidance" in mod:
        params["guidance"] = mod["guidance"]
    if "model" in mod:
        params["model"] = mod["model"]
    if "steps" in mod:
        params["steps"] = mod["steps"]
    if "refine" in mod:
        params["refine"] = mod["refine"]
    if "steps_delta" in mod:
        params["steps"] = params["steps"] + mod["steps_delta"]
        if "steps_min" in mod:
            params["steps"] = max(params["steps"], mod["steps_min"])
        if "refine_if_steps_gte" in mod and params["steps"] >= mod["refine_if_steps_gte"]:
            params["refine"] = True


def check_guidance_warning(params: dict) -> list[str]:
    """Return list of warning strings for the current resolved params."""
    warnings = []
    guidance = params.get("guidance", 0)
    model = params.get("model")
    if guidance > 7.5 and model != "precise":
        warnings.append(
            f"⚠️  guidance={guidance} > 7.5 without --model precise may cause over-saturation artifacts.\n"
            f"   Use --modifier photorealistic or --model precise to suppress this warning."
        )
    return warnings


def apply_style_tokens(
    user_prompt: str,
    style_name: str | None,
    *,
    no_default_style: bool = False,
) -> tuple[str, str | None, float | None, str | None]:
    """Prepend style tokens to user_prompt and return LoRA details.

    Args:
        user_prompt: The raw user-provided prompt text.
        style_name: Name from STYLES, or None to use folk-art default.
        no_default_style: When True, suppresses the folk-art default; passes prompt through unchanged.

    Returns:
        (final_prompt, lora_id, lora_weight, passthrough_style_name)

        passthrough_style_name is non-None when the style should be forwarded to
        generate.py as ``--style <name>`` rather than handled by this function.
    """
    if no_default_style or (style_name is not None and style_name.lower() == "none"):
        return user_prompt, None, None, None

    effective_style = style_name if style_name is not None else "folk-art"

    if effective_style not in STYLES:
        raise ValueError(f"Unknown style '{effective_style}'. Available: {sorted(STYLES)}")

    style_data = STYLES[effective_style]

    if style_data.get("passthrough"):
        return user_prompt, None, None, effective_style

    tokens = style_data.get("tokens", "")
    lora = style_data.get("lora")
    lora_weight = style_data.get("lora_weight")

    if tokens and user_prompt:
        final_prompt = f"{tokens} {user_prompt}"
    elif tokens:
        final_prompt = tokens
    else:
        final_prompt = user_prompt

    return final_prompt, lora, lora_weight, None


def estimate_tokens(text: str) -> int:
    """Estimate CLIP token count using whitespace+punctuation splitting.

    Accuracy: ±5 tokens relative to the CLIP tokenizer. No external dependencies required.
    See: OQ-8 in prd-wrapper-core.md.
    """
    return len(re.findall(r"\w+|[^\w\s]", text))


def check_vague_colors(prompt: str) -> list[str]:
    """Return sorted list of vague color words found in the prompt."""
    words = set(re.findall(r"\b\w+\b", prompt.lower()))
    return sorted(w for w in words if w in _VAGUE_COLOR_WORDS)
