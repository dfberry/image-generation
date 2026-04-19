"""
TDD tests for batch_generate() security and device auto-detection.

Covers:
    Issue #20 - Directory traversal prevention in batch output paths
    Issue #23 - Default device auto-detection instead of hardcoded "mps"

Mocking strategy: patch generate_with_retry so no real model loads.
"""

import os
from unittest.mock import patch

from generate import batch_generate

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_prompts(*items):
    """Build a prompts list from (prompt, output[, seed]) tuples."""
    result = []
    for item in items:
        d = {"prompt": item[0], "output": item[1]}
        if len(item) > 2:
            d["seed"] = item[2]
        result.append(d)
    return result


# ---------------------------------------------------------------------------
# Issue #20 - Directory traversal prevention
# ---------------------------------------------------------------------------


class TestPathTraversalRejection:
    """batch_generate must reject output paths that escape the working directory."""

    def test_dotdot_path_rejected(self):
        """Output path containing '..' segments must be rejected."""
        prompts = _make_prompts(("a sunset", "../../etc/passwd"))

        with patch("generate.generate_with_retry") as mock_gen:
            results = batch_generate(prompts, device="cpu")

        mock_gen.assert_not_called()
        assert len(results) == 1
        assert results[0]["status"] == "error"
        assert "traversal" in results[0]["error"].lower() or ".." in results[0]["error"]

    def test_absolute_path_rejected(self):
        """Absolute output paths must be rejected."""
        abs_path = os.path.join(os.sep, "absolute", "path.png")
        prompts = _make_prompts(("a sunset", abs_path))

        with patch("generate.generate_with_retry") as mock_gen:
            results = batch_generate(prompts, device="cpu")

        mock_gen.assert_not_called()
        assert len(results) == 1
        assert results[0]["status"] == "error"
        assert "absolute" in results[0]["error"].lower() or "Absolute" in results[0]["error"]

    def test_unix_absolute_path_rejected(self):
        """Unix-style absolute path /tmp/evil.png must be rejected."""
        prompts = _make_prompts(("a sunset", "/tmp/evil.png"))

        with patch("generate.generate_with_retry") as mock_gen:
            results = batch_generate(prompts, device="cpu")

        mock_gen.assert_not_called()
        assert len(results) == 1
        assert results[0]["status"] == "error"

    def test_normal_relative_path_accepted(self):
        """Normal relative paths like 'outputs/image.png' must be accepted."""
        prompts = _make_prompts(("a sunset", "outputs/normal.png"))

        with patch("generate.generate_with_retry", return_value="outputs/normal.png"):
            results = batch_generate(prompts, device="cpu")

        assert len(results) == 1
        assert results[0]["status"] == "ok"
        assert results[0]["output"] == "outputs/normal.png"

    def test_nested_relative_path_accepted(self):
        """Deeper relative paths like 'outputs/blog/2024/img.png' are fine."""
        prompts = _make_prompts(("a sunset", "outputs/blog/2024/img.png"))

        with patch("generate.generate_with_retry", return_value="outputs/blog/2024/img.png"):
            results = batch_generate(prompts, device="cpu")

        assert len(results) == 1
        assert results[0]["status"] == "ok"

    def test_dotdot_in_middle_of_path_rejected(self):
        """Paths like 'outputs/../../../etc/shadow' must be rejected."""
        prompts = _make_prompts(("a sunset", "outputs/../../../etc/shadow"))

        with patch("generate.generate_with_retry") as mock_gen:
            results = batch_generate(prompts, device="cpu")

        mock_gen.assert_not_called()
        assert results[0]["status"] == "error"

    def test_mixed_batch_rejects_bad_continues_good(self):
        """Bad paths get error entries; good paths still generate."""
        prompts = _make_prompts(
            ("good prompt", "outputs/ok.png"),
            ("evil prompt", "../../etc/passwd"),
            ("another good", "outputs/also_ok.png"),
        )

        with patch("generate.generate_with_retry", side_effect=lambda a: a.output):
            results = batch_generate(prompts, device="cpu")

        assert len(results) == 3
        assert results[0]["status"] == "ok"
        assert results[1]["status"] == "error"
        assert results[2]["status"] == "ok"


# ---------------------------------------------------------------------------
# Issue #23 - Device auto-detection default
# ---------------------------------------------------------------------------


class TestDeviceAutoDetection:
    """batch_generate default device must auto-detect instead of hardcoding 'mps'."""

    @patch("generate.get_device", return_value="cpu")
    def test_none_device_calls_get_device(self, mock_get_device):
        """When device=None, batch_generate calls get_device() to auto-detect."""
        prompts = _make_prompts(("a sunset", "outputs/test.png"))

        with patch("generate.generate_with_retry", return_value="outputs/test.png"):
            batch_generate(prompts, device=None)

        mock_get_device.assert_called_once_with(force_cpu=False)

    @patch("generate.get_device", return_value="cpu")
    def test_default_device_is_none(self, mock_get_device):
        """batch_generate() with no device arg must auto-detect (default=None)."""
        prompts = _make_prompts(("a sunset", "outputs/test.png"))

        with patch("generate.generate_with_retry", return_value="outputs/test.png"):
            batch_generate(prompts)

        mock_get_device.assert_called_once_with(force_cpu=False)

    def test_explicit_device_used_directly(self):
        """When device is explicitly provided, get_device() is NOT called."""
        prompts = _make_prompts(("a sunset", "outputs/test.png"))

        captured_args = []

        def capture(args):
            captured_args.append(args)
            return args.output

        with patch("generate.generate_with_retry", side_effect=capture), \
             patch("generate.get_device") as mock_get_device:
            batch_generate(prompts, device="cuda")

        mock_get_device.assert_not_called()
        assert captured_args[0].cpu is False

    @patch("generate.get_device", return_value="cuda")
    def test_autodetected_device_passed_to_batch_args(self, mock_get_device):
        """Auto-detected device must be reflected in batch_args.cpu flag."""
        prompts = _make_prompts(("a sunset", "outputs/test.png"))

        captured_args = []

        def capture(args):
            captured_args.append(args)
            return args.output

        with patch("generate.generate_with_retry", side_effect=capture):
            batch_generate(prompts, device=None)

        assert captured_args[0].cpu is False
