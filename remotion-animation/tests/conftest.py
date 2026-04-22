"""Shared test fixtures for remotion-animation tests.

Follows pattern from mermaid-diagrams and image-generation tests.
Mock OpenAI API, provide temp directories.
"""

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
