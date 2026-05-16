"""
Tests for _save_with_metadata() PNG metadata embedding.

Tests TPM-01 through TPM-08 per PRD §9.2.
Uses real PIL images and temp files — no GPU required.
"""

import json
from pathlib import Path

from PIL import Image

from generate import _save_with_metadata


def _make_test_image(width=64, height=64):
    """Create a minimal test PNG image."""
    return Image.new("RGB", (width, height), color=(100, 150, 200))


def _make_test_params(seed=42):
    return {
        "prompt": "Test prompt for metadata",
        "negative_prompt": "blurry, bad quality",
        "seed": seed,
        "steps": 22,
        "guidance": 6.5,
        "width": 64,
        "height": 64,
        "model": "precise",
        "scheduler": "DPMSolverMultistepScheduler",
        "loras": [],
        "refine": False,
        "refiner_steps": 10,
        "generated_at": "2026-05-16T06:48:00",
    }


class TestSaveWithMetadata:
    """_save_with_metadata() embeds generation parameters in PNG tEXt chunk."""

    def test_saved_png_has_generate_params_text_chunk(self, tmp_path):
        """TPM-01: Open saved PNG, read tEXt chunk, verify key 'generate_params' exists."""
        img = _make_test_image()
        out = str(tmp_path / "test.png")
        _save_with_metadata(img, out, _make_test_params())
        reopened = Image.open(out)
        assert "generate_params" in reopened.info

    def test_generate_params_is_valid_json(self, tmp_path):
        """TPM-02: json.loads(chunk) succeeds without exception."""
        img = _make_test_image()
        out = str(tmp_path / "test.png")
        _save_with_metadata(img, out, _make_test_params())
        reopened = Image.open(out)
        chunk = reopened.info["generate_params"]
        parsed = json.loads(chunk)
        assert isinstance(parsed, dict)

    def test_generate_params_contains_required_fields(self, tmp_path):
        """TPM-03: JSON includes: prompt, seed, steps, guidance, width, height, generated_at."""
        img = _make_test_image()
        out = str(tmp_path / "test.png")
        _save_with_metadata(img, out, _make_test_params())
        reopened = Image.open(out)
        parsed = json.loads(reopened.info["generate_params"])
        for field in ["prompt", "seed", "steps", "guidance", "width", "height", "generated_at"]:
            assert field in parsed, f"Missing field: {field}"

    def test_generate_params_seed_matches_effective_seed(self, tmp_path):
        """TPM-04: When args.seed=42, metadata 'seed' is 42."""
        img = _make_test_image()
        out = str(tmp_path / "test.png")
        _save_with_metadata(img, out, _make_test_params(seed=42))
        reopened = Image.open(out)
        parsed = json.loads(reopened.info["generate_params"])
        assert parsed["seed"] == 42

    def test_generate_params_loras_is_list(self, tmp_path):
        """TPM-05: 'loras' field is a list (not None, not a string)."""
        img = _make_test_image()
        params = _make_test_params()
        params["loras"] = [["hf/model-a", 0.8]]
        out = str(tmp_path / "test.png")
        _save_with_metadata(img, out, params)
        reopened = Image.open(out)
        parsed = json.loads(reopened.info["generate_params"])
        assert isinstance(parsed["loras"], list)

    def test_png_without_metadata_still_valid(self, tmp_path):
        """TPM-06: PNG saved without metadata (plain save) is still openable."""
        img = _make_test_image()
        out = str(tmp_path / "plain.png")
        img.save(out)
        reopened = Image.open(out)
        assert reopened.size == (64, 64)

    def test_metadata_overhead_is_acceptable(self, tmp_path):
        """TPM-07: Saving with metadata vs without: both succeed, no exception raised."""
        img = _make_test_image()
        with_meta = str(tmp_path / "with_meta.png")
        without_meta = str(tmp_path / "without_meta.png")
        _save_with_metadata(img, with_meta, _make_test_params())
        img.save(without_meta)
        # Both files exist and are valid
        assert Path(with_meta).exists()
        assert Path(without_meta).exists()
        Image.open(with_meta)
        Image.open(without_meta)

    def test_batch_images_have_metadata(self, tmp_path):
        """TPM-08: Each image in a simulated batch run has valid generate_params tEXt chunk."""
        for i in range(3):
            img = _make_test_image()
            params = _make_test_params(seed=42 + i)
            params["prompt"] = f"Batch prompt {i}"
            out = str(tmp_path / f"batch_{i}.png")
            _save_with_metadata(img, out, params)
            reopened = Image.open(out)
            assert "generate_params" in reopened.info
            parsed = json.loads(reopened.info["generate_params"])
            assert parsed["seed"] == 42 + i
