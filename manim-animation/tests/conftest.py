"""Shared test fixtures for manim-animation tests.

Follows pattern from mermaid-diagrams and image-generation tests.
Mock subprocess.run for Manim CLI, mock OpenAI API, provide temp directories.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Fixtures: temp directories
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_output_dir(tmp_path):
    """Temp directory for test outputs, cleaned up after."""
    out = tmp_path / "test_outputs"
    out.mkdir()
    return out

@pytest.fixture
def tmp_code_dir(tmp_path):
    """Temp directory for intermediate scene code files."""
    code = tmp_path / "scene_code"
    code.mkdir()
    return code

# ---------------------------------------------------------------------------
# Fixtures: LLM mocking
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response with valid Manim scene code."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content="""```python
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        text = Text("Hello World")
        self.play(Write(text))
        self.wait(1)
```"""
            )
        )
    ]
    return mock_response

@pytest.fixture
def mock_openai_empty_response():
    """Mock OpenAI API response with empty content."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=""))]
    return mock_response

@pytest.fixture
def mock_openai_non_code_response():
    """Mock OpenAI API response with non-code content."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="I cannot generate that animation."))
    ]
    return mock_response

# ---------------------------------------------------------------------------
# Fixtures: subprocess mocking (Manim CLI)
# ---------------------------------------------------------------------------

# Minimal valid MP4 header bytes (fake video file)
_FAKE_MP4 = (
    b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2mp41"
    b"\x00\x00\x00\x08free"
    b"\x00\x00\x00\x00mdat"
)

@pytest.fixture
def mock_subprocess_success():
    """Mock subprocess.run that simulates successful Manim render.

    Creates a fake MP4 file at the expected output path.
    """
    original_run = subprocess.run

    def _fake_run(cmd, **kwargs):
        # Detect Manim CLI calls: ["manim", "render", ...]
        if isinstance(cmd, list) and len(cmd) >= 3 and cmd[0] == "manim":
            # Extract output path (usually last arg or after -o)
            output_path = None
            for i, arg in enumerate(cmd):
                if arg == "-o" and i + 1 < len(cmd):
                    output_path = Path(cmd[i + 1])
                    break
            # If no -o, Manim writes to media/ by default; construct expected path
            if not output_path and len(cmd) >= 4:
                # Scene file is cmd[2], scene class is cmd[3]
                scene_file = Path(cmd[2])
                output_path = Path("media") / "videos" / scene_file.stem / "1080p60" / f"{cmd[3]}.mp4"

            if output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(_FAKE_MP4)

            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        return original_run(cmd, **kwargs)

    return _fake_run

@pytest.fixture
def mock_subprocess_failure():
    """Mock subprocess.run that simulates Manim render failure."""

    def _fake_run(cmd, **kwargs):
        if isinstance(cmd, list) and len(cmd) >= 3 and cmd[0] == "manim":
            return subprocess.CompletedProcess(
                cmd,
                1,
                stdout="",
                stderr="Error: Invalid scene code\nSyntaxError: unexpected EOF",
            )
        return subprocess.run(cmd, **kwargs)

    return _fake_run

@pytest.fixture
def mock_subprocess_manim_not_found():
    """Mock subprocess.run that simulates Manim CLI not installed."""

    def _fake_run(cmd, **kwargs):
        if isinstance(cmd, list) and cmd[0] == "manim":
            raise FileNotFoundError("manim command not found")
        return subprocess.run(cmd, **kwargs)

    return _fake_run
