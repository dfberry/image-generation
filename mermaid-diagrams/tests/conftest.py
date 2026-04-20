"""Shared test fixtures for mermaid-diagrams tests.

Neo's test fixtures -- matched against Trinity's actual implementation.
"""

import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Raw syntax constants
# ---------------------------------------------------------------------------

VALID_FLOWCHART = """\
flowchart TD
    A["Start"] --> B["Process"]
    B --> C{Decision?}
    C -->|Yes| D["End Yes"]
    C -->|No| E["End No"]
"""

VALID_SEQUENCE = """\
sequenceDiagram
    participant Client
    participant Server
    Client->>Server: GET /api/data
    Server-->>Client: 200 OK
"""

VALID_CLASS = """\
classDiagram
    class Animal
    class Dog
    class Cat
    Animal <|-- Dog
    Animal <|-- Cat
"""

VALID_ER = """\
erDiagram
    USER {
        string id
        string name
    }
    POST {
        string id
        string title
    }
    USER ||--o{ POST : has
"""

INVALID_SYNTAX = "this is not valid mermaid syntax"
EMPTY_SYNTAX = ""


# ---------------------------------------------------------------------------
# Fixtures: syntax samples
# ---------------------------------------------------------------------------


@pytest.fixture
def valid_flowchart_syntax():
    """Sample valid flowchart mermaid code."""
    return VALID_FLOWCHART


@pytest.fixture
def valid_sequence_syntax():
    """Sample valid sequence diagram code."""
    return VALID_SEQUENCE


@pytest.fixture
def valid_class_syntax():
    """Sample valid class diagram code."""
    return VALID_CLASS


@pytest.fixture
def valid_er_syntax():
    """Sample valid ER diagram code."""
    return VALID_ER


@pytest.fixture
def invalid_syntax():
    """Known-bad mermaid code (missing diagram type)."""
    return INVALID_SYNTAX


@pytest.fixture
def empty_syntax():
    """Empty string."""
    return EMPTY_SYNTAX


# ---------------------------------------------------------------------------
# Fixtures: temp directory
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_output_dir(tmp_path):
    """Temp directory for test outputs, cleaned up after."""
    out = tmp_path / "test_outputs"
    out.mkdir()
    return out


# ---------------------------------------------------------------------------
# Fixtures: mocked mmdc subprocess
# ---------------------------------------------------------------------------

# Minimal valid-ish PNG header bytes
_FAKE_PNG = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x08\x00\x00\x00\x08"
    b"\x08\x02\x00\x00\x00Km)\xdc\x00\x00\x00\x00IEND\xaeB`\x82"
)
_FAKE_SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8"></svg>'


@pytest.fixture
def mock_mmdc():
    """Mock that simulates mmdc subprocess.

    When subprocess.run is called with a command starting with the mmdc
    binary, the mock intercepts it and creates a small valid PNG or SVG
    file at the -o output path.
    """
    original_run = subprocess.run

    def _fake_run(cmd, **kwargs):
        if isinstance(cmd, list) and len(cmd) >= 5:
            binary = os.path.basename(cmd[0])
            if binary == "mmdc" or cmd[0] == "mmdc":
                try:
                    out_idx = cmd.index("-o") + 1
                    output_path = Path(cmd[out_idx])
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    # Pick content based on format flag
                    fmt_content = _FAKE_PNG
                    try:
                        fmt_idx = cmd.index("-e") + 1
                        if cmd[fmt_idx] == "svg":
                            fmt_content = _FAKE_SVG
                    except (ValueError, IndexError):
                        pass
                    output_path.write_bytes(fmt_content)
                except (ValueError, IndexError):
                    pass
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        return original_run(cmd, **kwargs)

    with patch("mermaidgen.generator.subprocess.run", side_effect=_fake_run) as mock_obj:
        yield mock_obj


@pytest.fixture
def generator(mock_mmdc, tmp_output_dir):
    """MermaidGenerator with mocked mmdc and temp output directory."""
    from mermaidgen.generator import MermaidGenerator

    return MermaidGenerator(output_dir=str(tmp_output_dir), mmdc_binary="mmdc")
