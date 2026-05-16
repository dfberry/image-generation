"""test_consistency_integration.py — Integration tests for Phase 2 consistency.

These tests invoke simple_config.py as a subprocess with --preview-prompts.
--preview-prompts is pure Python prompt assembly (no generate.py invocation).

Covers PRD §11 Tier 2 test specifications T2.1–T2.3.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_IMAGE_GEN_DIR = Path(__file__).parent.parent
_SIMPLE_CONFIG = str(_IMAGE_GEN_DIR / "simple_config.py")


def _run(*args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    """Run simple_config.py with given args in the image-generation/ directory."""
    cmd = [sys.executable, _SIMPLE_CONFIG, *args]
    return subprocess.run(
        cmd,
        cwd=str(_IMAGE_GEN_DIR),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# T2.1 — --preview-prompts with woodshop-blog profile
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_preview_prompts_with_profile_woodshop_blog(tmp_path):
    """--preview-prompts with v2 batch assembles prompts, does not invoke generate.py."""
    batch = {
        "profile": "woodshop-blog",
        "images": [
            {
                "prompt_core": "Two men at a maple workbench building a dovetail joint",
                "characters": [
                    {"name": "protagonist", "position": "left", "action": "holding a mallet"},
                    {"name": "ai-agent", "position": "right", "action": "steadying the joint"},
                ],
                "expression": "focused",
                "seed": 71,
                "output": "outputs/series/level-1.png",
            },
            {
                "prompt_core": "One man arranging custom jigs in labeled drawers",
                "characters": [{"name": "protagonist"}],
                "expression": "focused",
                "seed": 54,
                "output": "outputs/series/level-2.png",
            },
        ],
    }
    batch_file = tmp_path / "batch_woodshop_test.json"
    batch_file.write_text(json.dumps(batch), encoding="utf-8")

    result = _run("--batch-file", str(batch_file), "--preview-prompts", "--allow-over-budget")

    assert result.returncode == 0, f"Expected exit 0, got {result.returncode}\nstderr: {result.stderr}"
    assert "Assembled prompt" in result.stdout, "Expected 'Assembled prompt' in stdout"

    # Both images should produce output
    assert result.stdout.count("Assembled prompt") >= 2

    # woodshop scene token present
    assert "brick walls" in result.stdout, "Expected woodshop scene token 'brick walls' in stdout"

    # protagonist token present
    assert "bright cobalt blue" in result.stdout, "Expected protagonist color token in stdout"

    # generate.py was NOT invoked (no subprocess output, explicit message)
    assert "generate.py calls made" in result.stdout or "preview-prompts" in result.stdout.lower()
    assert "Resolved command" not in result.stdout, "generate.py should not be invoked"


# ---------------------------------------------------------------------------
# T2.2 — All images in batch receive profile tokens
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_batch_all_images_get_profile_tokens(tmp_path):
    """Every image in a 3-image v2 batch contains profile style + scene tokens."""
    batch = {
        "profile": "woodshop-blog",
        "images": [
            {
                "prompt_core": f"Scene {i}: men working in the shop",
                "characters": [{"name": "protagonist", "position": "left"}],
                "expression": "focused",
                "seed": 100 + i,
                "output": f"outputs/test/scene-{i}.png",
            }
            for i in range(3)
        ],
    }
    batch_file = tmp_path / "batch_3images.json"
    batch_file.write_text(json.dumps(batch), encoding="utf-8")

    result = _run("--batch-file", str(batch_file), "--preview-prompts", "--allow-over-budget")

    assert result.returncode == 0, f"Expected exit 0\nstderr: {result.stderr}"

    # Count assembled prompts: should be 3
    prompt_count = result.stdout.count("Assembled prompt")
    assert prompt_count >= 3, f"Expected 3 assembled prompts, got {prompt_count}"

    # Every image should contain watercolor (from profile.style) and brick walls (from profile.scene)
    # Split output into per-image sections and check each
    sections = result.stdout.split("[simple_config] Image ")
    image_sections = [s for s in sections if s and s[0].isdigit()]
    assert len(image_sections) >= 3, f"Expected 3 image sections, got {len(image_sections)}"

    for section in image_sections:
        assert "Watercolor illustration" in section or "watercolor" in section.lower(), (
            f"Expected watercolor style tokens in:\n{section[:300]}"
        )
        assert "brick walls" in section, f"Expected 'brick walls' in:\n{section[:300]}"


# ---------------------------------------------------------------------------
# T2.3 — v1 batch JSON passes through unchanged
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_v1_batch_json_passthrough_unchanged(tmp_path):
    """Legacy flat batch array passes through --preview-prompts with original prompts intact."""
    original_prompts = [
        "A developer working at a computer, warm light, no text",
        "Two people reviewing code on a whiteboard, no text",
    ]
    legacy_batch = [
        {
            "prompt": p,
            "seed": 42 + i,
            "output": f"outputs/legacy/image-{i}.png",
            "negative_prompt": "blurry, low quality",
        }
        for i, p in enumerate(original_prompts)
    ]
    batch_file = tmp_path / "legacy_batch.json"
    batch_file.write_text(json.dumps(legacy_batch), encoding="utf-8")

    result = _run("--batch-file", str(batch_file), "--preview-prompts")

    assert result.returncode == 0, f"Expected exit 0\nstderr: {result.stderr}"

    # Original prompts appear unchanged in stdout
    for prompt in original_prompts:
        assert prompt in result.stdout, f"Expected original prompt in stdout: {prompt!r}"

    # No scene or character tokens injected
    assert "brick walls" not in result.stdout, "Scene tokens should not appear in v1 passthrough"
    assert "cobalt blue" not in result.stdout, "Character tokens should not appear in v1 passthrough"

    # generate.py was NOT invoked
    assert "generate.py calls made" in result.stdout or "preview-prompts" in result.stdout.lower()
