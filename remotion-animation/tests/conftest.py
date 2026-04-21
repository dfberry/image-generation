"""Shared test fixtures for remotion-animation tests.

Follows pattern from mermaid-diagrams and image-generation tests.
Mock subprocess.run for Remotion CLI (npx remotion render), mock OpenAI API, provide temp directories.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

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
def tmp_project_dir(tmp_path):
    """Temp directory simulating remotion-project/ structure."""
    project = tmp_path / "remotion-project"
    project.mkdir()
    (project / "src").mkdir()
    return project


# ---------------------------------------------------------------------------
# Fixtures: LLM mocking
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response with valid Remotion component code."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content="""```tsx
import { AbsoluteFill, useCurrentFrame } from 'remotion';

export const GeneratedScene: React.FC = () => {
  const frame = useCurrentFrame();
  const opacity = Math.min(1, frame / 30);

  return (
    <AbsoluteFill style={{ backgroundColor: 'blue' }}>
      <h1 style={{ opacity }}>Hello World</h1>
    </AbsoluteFill>
  );
};
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
# Fixtures: subprocess mocking (Remotion CLI)
# ---------------------------------------------------------------------------


# Minimal valid MP4 header bytes (fake video file)
_FAKE_MP4 = (
    b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2mp41"
    b"\x00\x00\x00\x08free"
    b"\x00\x00\x00\x00mdat"
)


@pytest.fixture
def mock_subprocess_success():
    """Mock subprocess.run that simulates successful Remotion render.

    Creates a fake MP4 file at the expected output path.
    """
    original_run = subprocess.run

    def _fake_run(cmd, **kwargs):
        # Detect Remotion CLI calls: ["npx", "remotion", "render", ...]
        if isinstance(cmd, list) and len(cmd) >= 4 and cmd[1] == "remotion" and cmd[2] == "render":
            # Output path is usually the last argument
            output_path = Path(cmd[-1])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(_FAKE_MP4)

            return subprocess.CompletedProcess(cmd, 0, stdout="Render complete", stderr="")

        return original_run(cmd, **kwargs)

    return _fake_run


@pytest.fixture
def mock_subprocess_failure():
    """Mock subprocess.run that simulates Remotion render failure."""

    def _fake_run(cmd, **kwargs):
        if isinstance(cmd, list) and len(cmd) >= 4 and cmd[1] == "remotion":
            return subprocess.CompletedProcess(
                cmd,
                1,
                stdout="",
                stderr="Error: Component not found\nTypeError: Cannot read property 'map' of undefined",
            )
        return subprocess.run(cmd, **kwargs)

    return _fake_run


@pytest.fixture
def mock_subprocess_remotion_not_found():
    """Mock subprocess.run that simulates Remotion CLI not installed."""

    def _fake_run(cmd, **kwargs):
        if isinstance(cmd, list) and cmd[0] == "npx" and cmd[1] == "remotion":
            raise FileNotFoundError("npx command not found")
        return subprocess.run(cmd, **kwargs)

    return _fake_run
