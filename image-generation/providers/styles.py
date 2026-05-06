"""Style Transfer preset registry for SDXL img2img with LoRA adapters.

Each preset maps a style name to:
- lora_id: Hugging Face model ID for the LoRA adapter
- strength: default denoising strength for img2img
- guidance_scale: recommended CFG scale
- lora_weight: LoRA adapter weight
- negative_prompt_additions: extra negative prompt terms for the style
- description: human-readable description shown in --list-styles
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class StylePreset:
    """A single style transfer preset."""

    name: str
    lora_id: str
    description: str
    strength: float = 0.75
    guidance_scale: float = 7.5
    lora_weight: float = 0.8
    negative_prompt_additions: str = ""


# ---------------------------------------------------------------------------
# Style Registry — data-driven, no per-style code
#
# All LoRA models are open-source SDXL LoRAs hosted on Hugging Face.
# ---------------------------------------------------------------------------

STYLE_PRESETS: dict[str, StylePreset] = {
    "watercolor": StylePreset(
        name="watercolor",
        lora_id="ostris/watercolor_style_lora_sdxl",
        description="Soft watercolor / aquarelle painting look",
        strength=0.70,
        guidance_scale=7.0,
        lora_weight=0.85,
        negative_prompt_additions="photograph, photorealistic, sharp edges, digital art",
    ),
    "oil-painting": StylePreset(
        name="oil-painting",
        lora_id="TheLastBen/Oil_Painting_SDXL_LoRA",
        description="Classical oil paint texture with visible brushstrokes",
        strength=0.72,
        guidance_scale=7.5,
        lora_weight=0.80,
        negative_prompt_additions="photograph, photorealistic, flat colors, digital art",
    ),
    "sketch": StylePreset(
        name="sketch",
        lora_id="SvenN/sdxl-pencil-sketch",
        description="Pencil or charcoal drawing / sketch style",
        strength=0.68,
        guidance_scale=7.0,
        lora_weight=0.80,
        negative_prompt_additions="color, photograph, photorealistic, painting",
    ),
    "anime": StylePreset(
        name="anime",
        lora_id="Linaqruf/anime-detailer-xl-lora",
        description="Anime / manga illustration style",
        strength=0.75,
        guidance_scale=8.0,
        lora_weight=0.85,
        negative_prompt_additions="photograph, photorealistic, 3d render, western cartoon",
    ),
    "pixel-art": StylePreset(
        name="pixel-art",
        lora_id="nerijs/pixel-art-xl",
        description="Retro pixel art style (8-bit / 16-bit aesthetic)",
        strength=0.78,
        guidance_scale=7.5,
        lora_weight=0.90,
        negative_prompt_additions="photograph, photorealistic, smooth, anti-aliased, high resolution",
    ),
}


def get_style(name: str) -> StylePreset:
    """Look up a style preset by name. Raises ValueError if not found."""
    preset = STYLE_PRESETS.get(name)
    if preset is None:
        available = ", ".join(sorted(STYLE_PRESETS.keys()))
        raise ValueError(
            f"Unknown style '{name}'. Available styles: {available}"
        )
    return preset


def list_styles() -> list[StylePreset]:
    """Return all available style presets sorted by name."""
    return sorted(STYLE_PRESETS.values(), key=lambda s: s.name)


def format_styles_table() -> str:
    """Format a human-readable table of available styles for CLI output."""
    lines = ["Available styles:", ""]
    for preset in list_styles():
        lines.append(f"  {preset.name:<14} {preset.description}")
        lines.append(f"  {'':14} LoRA: {preset.lora_id}")
        lines.append(f"  {'':14} Defaults: strength={preset.strength}, "
                     f"guidance={preset.guidance_scale}, "
                     f"lora_weight={preset.lora_weight}")
        lines.append("")
    lines.append("Usage: python generate.py --style <name> --input <image>")
    return "\n".join(lines)
