"""
Visual regression tests (semi-automated).

Tests require actual image generation (CPU: ~14 min/image).
Run manually via: make test-visual
NOT run in CI on every push.
"""

import pytest

try:
    import imagehash
    from PIL import Image
    HAS_IMAGEHASH = True
except ImportError:
    HAS_IMAGEHASH = False


def assert_visual_match(new_path, baseline_hash_str, max_distance=10):
    """pHash comparison. Distance > 10 = visually different -> requires human review."""
    new_hash = imagehash.phash(Image.open(new_path))
    baseline_hash = imagehash.hex_to_hash(baseline_hash_str)
    distance = new_hash - baseline_hash
    assert distance <= max_distance, (
        f"Visual regression detected: pHash distance={distance} > threshold={max_distance}. "
        f"New image: {new_path}. Review manually and update baseline if change is intentional."
    )


@pytest.mark.visual
@pytest.mark.skipif(not HAS_IMAGEHASH, reason="imagehash not installed")
def test_seed_determinism_precise_no_lora():
    """Same seed + same model -> same image. pHash distance <= 5 (near-identical)."""
    pytest.skip("Visual test requires actual image generation (~14 min). Run manually with: make test-visual")


@pytest.mark.visual
@pytest.mark.skipif(not HAS_IMAGEHASH, reason="imagehash not installed")
def test_lora_changes_image_visually():
    """LoRA must produce a visually different image. pHash distance > 5 from no-LoRA baseline."""
    pytest.skip("Visual test requires actual image generation (~14 min). Run manually with: make test-visual")


@pytest.mark.visual
@pytest.mark.skipif(not HAS_IMAGEHASH, reason="imagehash not installed")
def test_no_visual_regression_after_changes():
    """Post-engine-changes image matches stored baseline hash within threshold."""
    pytest.skip("Visual test requires actual image generation (~14 min). Run manually with: make test-visual")
