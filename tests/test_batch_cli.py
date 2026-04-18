"""
TDD Red Phase — --batch-file CLI flag tests.

These tests are written BEFORE the implementation exists.
ALL tests are expected to FAIL until Trinity implements --batch-file in generate.py.

Feature contract under test:
    --batch-file <path>: read JSON file of prompt dicts, call batch_generate(), print summary
    --prompt becomes optional when --batch-file is used (mutually exclusive paths)

Mocking strategy:
    - parse_args() tests: patch sys.argv, call generate.parse_args() directly
    - integration tests: call generate.main() — does not exist yet → AttributeError
    - No real GPU, no real diffusers model loaded

Decision note:
    A main() function refactor is REQUIRED for testability. Currently the __main__ block
    cannot be unit-tested without subprocess. Trinity must extract a main() function from
    the if __name__ == "__main__" block in generate.py.
"""

import json
from unittest.mock import patch

import pytest

import generate

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_with_args(arg_list):
    """Call parse_args() with a controlled sys.argv."""
    with patch("sys.argv", ["generate.py"] + arg_list):
        return generate.parse_args()


def _run_main(arg_list):
    """
    Call generate.main() with controlled sys.argv.
    Will raise AttributeError until Trinity implements main().
    """
    with patch("sys.argv", ["generate.py"] + arg_list):
        return generate.main()


# ---------------------------------------------------------------------------
# Test 1 — parse_args accepts --batch-file without error
# ---------------------------------------------------------------------------

def test_batch_file_arg_accepted(tmp_path):
    """parse_args() should accept --batch-file <path> without raising SystemExit."""
    json_file = tmp_path / "prompts.json"
    json_file.write_text("[]")
    # Currently fails: SystemExit(2) "unrecognized arguments: --batch-file"
    args = _parse_with_args(["--batch-file", str(json_file)])
    assert args.batch_file == str(json_file)


# ---------------------------------------------------------------------------
# Test 2 — --batch-file and --prompt are mutually exclusive
# ---------------------------------------------------------------------------

def test_batch_file_and_prompt_mutually_exclusive(tmp_path):
    """Providing both --batch-file and --prompt should raise SystemExit."""
    json_file = tmp_path / "prompts.json"
    json_file.write_text("[]")

    # First: --batch-file alone must be accepted (no error). Currently fails here
    # because --batch-file is unrecognized → SystemExit(2) escapes the test.
    args = _parse_with_args(["--batch-file", str(json_file)])
    assert hasattr(args, "batch_file")

    # Then: both together must be rejected.
    with pytest.raises(SystemExit):
        _parse_with_args([
            "--batch-file", str(json_file),
            "--prompt", "a sunset over the ocean",
        ])


# ---------------------------------------------------------------------------
# Test 3 — reads JSON and calls batch_generate with file contents
# ---------------------------------------------------------------------------

def test_batch_file_reads_json_and_calls_batch_generate(tmp_path):
    """When --batch-file given, batch_generate() is called with the JSON file contents."""
    prompts = [
        {"prompt": "a sunset", "output": "out1.png"},
        {"prompt": "a forest", "output": "out2.png"},
    ]
    json_file = tmp_path / "prompts.json"
    json_file.write_text(json.dumps(prompts))

    with patch("generate.batch_generate") as mock_batch:
        mock_batch.return_value = [
            {"prompt": "a sunset", "output": "out1.png", "status": "ok", "error": None},
            {"prompt": "a forest", "output": "out2.png", "status": "ok", "error": None},
        ]
        # AttributeError until generate.main() exists
        _run_main(["--batch-file", str(json_file)])

    mock_batch.assert_called_once()
    actual_prompts = mock_batch.call_args[0][0]
    assert actual_prompts == prompts


# ---------------------------------------------------------------------------
# Test 4 — non-existent file path raises SystemExit or FileNotFoundError
# ---------------------------------------------------------------------------

def test_batch_file_missing_file_exits(tmp_path):
    """Non-existent --batch-file path should raise SystemExit or FileNotFoundError."""
    missing = str(tmp_path / "does_not_exist.json")
    # AttributeError until generate.main() exists
    with pytest.raises((SystemExit, FileNotFoundError)):
        _run_main(["--batch-file", missing])


# ---------------------------------------------------------------------------
# Test 5 — malformed JSON raises SystemExit, ValueError, or JSONDecodeError
# ---------------------------------------------------------------------------

def test_batch_file_malformed_json_exits(tmp_path):
    """Malformed JSON in --batch-file should raise SystemExit, ValueError, or JSONDecodeError."""
    json_file = tmp_path / "bad.json"
    json_file.write_text("{this is not: valid json]]]")
    # AttributeError until generate.main() exists
    with pytest.raises((SystemExit, ValueError, json.JSONDecodeError)):
        _run_main(["--batch-file", str(json_file)])


# ---------------------------------------------------------------------------
# Test 6 — empty JSON array calls batch_generate([]) without error
# ---------------------------------------------------------------------------

def test_batch_file_empty_array_returns_empty(tmp_path):
    """Empty JSON array should call batch_generate([]) without error."""
    json_file = tmp_path / "empty.json"
    json_file.write_text("[]")

    with patch("generate.batch_generate") as mock_batch:
        mock_batch.return_value = []
        # AttributeError until generate.main() exists
        _run_main(["--batch-file", str(json_file)])

    mock_batch.assert_called_once()
    actual_prompts = mock_batch.call_args[0][0]
    assert actual_prompts == []


# ---------------------------------------------------------------------------
# Test 7 — --cpu flag passes device="cpu" to batch_generate
# ---------------------------------------------------------------------------

def test_batch_file_device_passed_to_batch_generate(tmp_path):
    """--cpu flag should cause batch_generate() to be called with device='cpu'."""
    prompts = [{"prompt": "a river delta", "output": "out.png"}]
    json_file = tmp_path / "prompts.json"
    json_file.write_text(json.dumps(prompts))

    with patch("generate.batch_generate") as mock_batch:
        mock_batch.return_value = [
            {"prompt": "a river delta", "output": "out.png", "status": "ok", "error": None}
        ]
        # AttributeError until generate.main() exists
        _run_main(["--batch-file", str(json_file), "--cpu"])

    mock_batch.assert_called_once()
    bound = mock_batch.call_args
    # device can arrive as positional arg [1] or keyword
    actual_device = (
        bound[1].get("device")
        if "device" in bound[1]
        else (bound[0][1] if len(bound[0]) > 1 else None)
    )
    assert actual_device == "cpu"


# ---------------------------------------------------------------------------
# Test 8 — results are printed (at least one line of output per item)
# ---------------------------------------------------------------------------

def test_batch_file_results_printed(tmp_path, capsys):
    """main() should print a result summary — at minimum, one output line per item."""
    prompts = [
        {"prompt": "a mountain range", "output": "out1.png"},
        {"prompt": "a coastal village", "output": "out2.png"},
    ]
    json_file = tmp_path / "prompts.json"
    json_file.write_text(json.dumps(prompts))

    results = [
        {"prompt": "a mountain range", "output": "out1.png", "status": "ok", "error": None},
        {"prompt": "a coastal village", "output": "out2.png", "status": "ok", "error": None},
    ]

    with patch("generate.batch_generate") as mock_batch:
        mock_batch.return_value = results
        # AttributeError until generate.main() exists
        _run_main(["--batch-file", str(json_file)])

    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert len(output.strip()) > 0, "Expected at least one printed summary line"


# ---------------------------------------------------------------------------
# Test 9 — partial failure: main() does not crash if one item errors
# ---------------------------------------------------------------------------

def test_batch_file_partial_failure_continues(tmp_path):
    """If one batch item errors, main() should still complete without raising."""
    prompts = [
        {"prompt": "good prompt", "output": "out1.png"},
        {"prompt": "bad prompt", "output": "out2.png"},
        {"prompt": "another good prompt", "output": "out3.png"},
    ]
    json_file = tmp_path / "prompts.json"
    json_file.write_text(json.dumps(prompts))

    results = [
        {"prompt": "good prompt", "output": "out1.png", "status": "ok", "error": None},
        {"prompt": "bad prompt", "output": "out2.png", "status": "error", "error": "OOM"},
        {"prompt": "another good prompt", "output": "out3.png", "status": "ok", "error": None},
    ]

    with patch("generate.batch_generate") as mock_batch:
        mock_batch.return_value = results
        # Should complete without raising. AttributeError until generate.main() exists.
        _run_main(["--batch-file", str(json_file)])


# ---------------------------------------------------------------------------
# Test 10 — --prompt is NOT required when --batch-file is given
# ---------------------------------------------------------------------------

def test_batch_file_prompt_not_required_when_batch_file_given(tmp_path):
    """parse_args() should not require --prompt when --batch-file is provided."""
    json_file = tmp_path / "prompts.json"
    json_file.write_text("[]")

    # Currently fails: SystemExit(2) "unrecognized arguments: --batch-file"
    try:
        args = _parse_with_args(["--batch-file", str(json_file)])
    except SystemExit as exc:
        pytest.fail(
            f"parse_args() raised SystemExit({exc.code}) when --batch-file was given "
            f"without --prompt. Expected --prompt to be optional in batch-file mode."
        )

    assert hasattr(args, "batch_file")
    assert args.batch_file == str(json_file)
