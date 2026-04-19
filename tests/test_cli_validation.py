"""
CLI Argument Validation tests (Issues #5, #43, #44).

Validation rules:
    --steps    : must be > 0   (positive integer)
    --guidance : must be >= 0  (non-negative float)
    --width    : must be >= 64 (reasonable pixel minimum)
    --height   : must be >= 64 (reasonable pixel minimum)

Direct validator unit tests (Issue #43):
    _positive_int()       : argparse type for positive integers (> 0)
    _non_negative_float() : argparse type for non-negative floats (>= 0)

CLI flag tests (Issue #44):
    --seed, --output, --refine, --refiner-steps
"""

import argparse
import sys
from unittest.mock import patch

import pytest

from generate import _non_negative_float, _positive_int, parse_args


def _parse_with_args(cli_args: list[str]):
    with patch.object(sys, "argv", ["generate.py"] + cli_args):
        return parse_args()


# =====================================================================
# Original Issue #5 tests - steps, dimensions, guidance
# =====================================================================


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


# =====================================================================
# Issue #43 -- Direct unit tests for _positive_int() and
#              _non_negative_float() validator functions
# =====================================================================


class TestPositiveIntValidator:
    """Direct unit tests for _positive_int() argparse type function."""

    # --- Valid inputs ---
    def test_one_is_minimum_valid(self):
        assert _positive_int("1") == 1

    def test_typical_value(self):
        assert _positive_int("42") == 42

    def test_large_value(self):
        assert _positive_int("999999") == 999999

    def test_very_large_value(self):
        """Ensure no artificial upper bound exists."""
        assert _positive_int("2147483647") == 2147483647  # INT32_MAX

    # --- Zero / negative (must reject) ---
    def test_zero_rejected(self):
        with pytest.raises(argparse.ArgumentTypeError, match="must be > 0"):
            _positive_int("0")

    def test_negative_one_rejected(self):
        with pytest.raises(argparse.ArgumentTypeError, match="must be > 0"):
            _positive_int("-1")

    def test_large_negative_rejected(self):
        with pytest.raises(argparse.ArgumentTypeError, match="must be > 0"):
            _positive_int("-9999")

    # --- Non-numeric / type-error inputs ---
    def test_non_numeric_string_rejected(self):
        with pytest.raises(ValueError):
            _positive_int("abc")

    def test_empty_string_rejected(self):
        with pytest.raises(ValueError):
            _positive_int("")

    def test_float_string_rejected(self):
        """int('3.5') raises ValueError -- floats are not valid integers."""
        with pytest.raises(ValueError):
            _positive_int("3.5")

    def test_whitespace_only_rejected(self):
        with pytest.raises(ValueError):
            _positive_int("   ")

    # --- Return type ---
    def test_return_type_is_int(self):
        result = _positive_int("10")
        assert isinstance(result, int)


class TestNonNegativeFloatValidator:
    """Direct unit tests for _non_negative_float() argparse type function."""

    # --- Valid inputs ---
    def test_zero_is_accepted(self):
        assert _non_negative_float("0") == 0.0

    def test_zero_point_zero_accepted(self):
        assert _non_negative_float("0.0") == 0.0

    def test_typical_value(self):
        assert _non_negative_float("6.5") == 6.5

    def test_integer_string_accepted(self):
        """float('10') is valid -- integers are valid floats."""
        assert _non_negative_float("10") == 10.0

    def test_large_value(self):
        assert _non_negative_float("1000.5") == 1000.5

    def test_very_small_positive(self):
        assert _non_negative_float("0.001") == 0.001

    # --- Negative (must reject) ---
    def test_negative_one_rejected(self):
        with pytest.raises(argparse.ArgumentTypeError, match="must be >= 0"):
            _non_negative_float("-1")

    def test_small_negative_rejected(self):
        with pytest.raises(argparse.ArgumentTypeError, match="must be >= 0"):
            _non_negative_float("-0.001")

    def test_large_negative_rejected(self):
        with pytest.raises(argparse.ArgumentTypeError, match="must be >= 0"):
            _non_negative_float("-100.5")

    # --- Non-numeric / type-error inputs ---
    def test_non_numeric_string_rejected(self):
        with pytest.raises(ValueError):
            _non_negative_float("abc")

    def test_empty_string_rejected(self):
        with pytest.raises(ValueError):
            _non_negative_float("")

    def test_whitespace_only_rejected(self):
        with pytest.raises(ValueError):
            _non_negative_float("   ")

    # --- Edge: special float values ---
    def test_inf_accepted(self):
        """float('inf') is non-negative -- validator should allow it."""
        result = _non_negative_float("inf")
        assert result == float("inf")

    def test_negative_inf_rejected(self):
        with pytest.raises(argparse.ArgumentTypeError, match="must be >= 0"):
            _non_negative_float("-inf")

    # --- Return type ---
    def test_return_type_is_float(self):
        result = _non_negative_float("5.0")
        assert isinstance(result, float)


# =====================================================================
# Issue #44 -- Tests for 4 missing CLI flags:
#   --seed, --output, --refine, --refiner-steps
# =====================================================================


class TestSeedFlag:
    """Tests for the --seed CLI flag (type=int, default=None)."""

    def test_default_is_none(self):
        args = _parse_with_args(["--prompt", "test"])
        assert args.seed is None

    def test_valid_positive_seed(self):
        args = _parse_with_args(["--prompt", "test", "--seed", "42"])
        assert args.seed == 42

    def test_zero_seed_accepted(self):
        """Zero is a valid seed -- no positive-only constraint."""
        args = _parse_with_args(["--prompt", "test", "--seed", "0"])
        assert args.seed == 0

    def test_negative_seed_accepted(self):
        """Negative seeds are valid ints -- torch handles them."""
        args = _parse_with_args(["--prompt", "test", "--seed", "-1"])
        assert args.seed == -1

    def test_large_seed(self):
        args = _parse_with_args(["--prompt", "test", "--seed", "2147483647"])
        assert args.seed == 2147483647

    def test_non_numeric_seed_rejected(self):
        with pytest.raises(SystemExit):
            _parse_with_args(["--prompt", "test", "--seed", "abc"])

    def test_float_seed_rejected(self):
        """--seed type=int, so '3.5' should fail."""
        with pytest.raises(SystemExit):
            _parse_with_args(["--prompt", "test", "--seed", "3.5"])


class TestOutputFlag:
    """Tests for the --output CLI flag (default=None)."""

    def test_default_is_none(self):
        args = _parse_with_args(["--prompt", "test"])
        assert args.output is None

    def test_custom_output_path(self):
        args = _parse_with_args(["--prompt", "test", "--output", "my_image.png"])
        assert args.output == "my_image.png"

    def test_output_with_directory(self):
        args = _parse_with_args(["--prompt", "test", "--output", "outputs/blog/hero.png"])
        assert args.output == "outputs/blog/hero.png"

    def test_output_with_spaces_in_path(self):
        args = _parse_with_args(["--prompt", "test", "--output", "my folder/my image.png"])
        assert args.output == "my folder/my image.png"

    def test_output_empty_string(self):
        """Empty string is syntactically valid at the argparse level."""
        args = _parse_with_args(["--prompt", "test", "--output", ""])
        assert args.output == ""


class TestRefineFlag:
    """Tests for the --refine CLI flag (action='store_true')."""

    def test_default_is_false(self):
        args = _parse_with_args(["--prompt", "test"])
        assert args.refine is False

    def test_present_sets_true(self):
        args = _parse_with_args(["--prompt", "test", "--refine"])
        assert args.refine is True

    def test_refine_with_other_flags(self):
        args = _parse_with_args([
            "--prompt", "test",
            "--refine",
            "--steps", "30",
            "--seed", "42",
        ])
        assert args.refine is True
        assert args.steps == 30
        assert args.seed == 42

    def test_refine_does_not_accept_value(self):
        """store_true flags don't take a value argument."""
        with pytest.raises(SystemExit):
            _parse_with_args(["--prompt", "test", "--refine", "yes"])


class TestRefinerStepsFlag:
    """Tests for the --refiner-steps CLI flag (type=_positive_int, default=10)."""

    def test_default_is_10(self):
        args = _parse_with_args(["--prompt", "test"])
        assert args.refiner_steps == 10

    def test_custom_valid_value(self):
        args = _parse_with_args(["--prompt", "test", "--refiner-steps", "25"])
        assert args.refiner_steps == 25

    def test_minimum_one(self):
        args = _parse_with_args(["--prompt", "test", "--refiner-steps", "1"])
        assert args.refiner_steps == 1

    def test_zero_rejected(self):
        """Uses _positive_int, so 0 is invalid."""
        with pytest.raises((SystemExit, ValueError)):
            _parse_with_args(["--prompt", "test", "--refiner-steps", "0"])

    def test_negative_rejected(self):
        with pytest.raises((SystemExit, ValueError)):
            _parse_with_args(["--prompt", "test", "--refiner-steps", "-5"])

    def test_non_numeric_rejected(self):
        with pytest.raises(SystemExit):
            _parse_with_args(["--prompt", "test", "--refiner-steps", "abc"])

    def test_float_rejected(self):
        with pytest.raises(SystemExit):
            _parse_with_args(["--prompt", "test", "--refiner-steps", "10.5"])
