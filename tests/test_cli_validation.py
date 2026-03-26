"""
CLI Argument Validation tests (Issue #5).

Validation rules:
    --steps    : must be > 0   (positive integer)
    --guidance : must be >= 0  (non-negative float)
    --width    : must be >= 64 (reasonable pixel minimum)
    --height   : must be >= 64 (reasonable pixel minimum)
"""

import sys
from unittest.mock import patch

import pytest

from generate import parse_args


def _parse_with_args(cli_args: list[str]):
    with patch.object(sys, "argv", ["generate.py"] + cli_args):
        return parse_args()


class TestStepsValidation:
    def test_steps_zero_rejected(self):
        with pytest.raises((SystemExit, ValueError)):
            _parse_with_args(["--prompt", "test", "--steps", "0"])

    def test_steps_negative_rejected(self):
        with pytest.raises((SystemExit, ValueError)):
            _parse_with_args(["--prompt", "test", "--steps", "-5"])


class TestDimensionValidation:
    def test_width_zero_rejected(self):
        with pytest.raises((SystemExit, ValueError)):
            _parse_with_args(["--prompt", "test", "--width", "0"])

    def test_height_zero_rejected(self):
        with pytest.raises((SystemExit, ValueError)):
            _parse_with_args(["--prompt", "test", "--height", "0"])

    def test_width_below_minimum_rejected(self):
        with pytest.raises((SystemExit, ValueError)):
            _parse_with_args(["--prompt", "test", "--width", "7"])

    def test_height_below_minimum_rejected(self):
        with pytest.raises((SystemExit, ValueError)):
            _parse_with_args(["--prompt", "test", "--height", "7"])


class TestGuidanceValidation:
    def test_guidance_negative_rejected(self):
        with pytest.raises((SystemExit, ValueError)):
            _parse_with_args(["--prompt", "test", "--guidance", "-1"])

    def test_guidance_large_negative_rejected(self):
        with pytest.raises((SystemExit, ValueError)):
            _parse_with_args(["--prompt", "test", "--guidance", "-100.5"])


class TestValidEdgeCases:
    def test_steps_one_accepted(self):
        args = _parse_with_args(["--prompt", "test", "--steps", "1"])
        assert args.steps == 1

    def test_guidance_zero_accepted(self):
        args = _parse_with_args(["--prompt", "test", "--guidance", "0.0"])
        assert args.guidance == 0.0

    def test_width_minimum_accepted(self):
        args = _parse_with_args(["--prompt", "test", "--width", "64"])
        assert args.width == 64

    def test_height_minimum_accepted(self):
        args = _parse_with_args(["--prompt", "test", "--height", "64"])
        assert args.height == 64

    def test_all_edge_values_together(self):
        args = _parse_with_args([
            "--prompt", "test",
            "--steps", "1",
            "--guidance", "0.0",
            "--width", "64",
            "--height", "64",
        ])
        assert args.steps == 1
        assert args.guidance == 0.0
        assert args.width == 64
        assert args.height == 64
