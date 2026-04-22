"""LLM client tests for remotion-animation.

Tests cover:
- _extract_code_block() extracts TSX from markdown fences
- _create_client() for each provider (ollama, openai, azure)
- _create_client() missing credentials → LLMError
- _create_client() unknown provider → LLMError
- generate_component() happy path with mocked LLM
- generate_component() retry logic on structural errors
- generate_component() API failure → LLMError
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from remotion_gen.errors import LLMError
from remotion_gen.llm_client import (
    _create_client,
    _extract_code_block,
    generate_component,
)


class TestExtractCodeBlock:
    """Test TSX code extraction from LLM responses."""

    def test_extracts_from_tsx_fence(self):
        """Should extract code between ```tsx and ``` markers."""
        response = "```tsx\nconst x = 1;\n```"
        assert _extract_code_block(response) == "const x = 1;"

    def test_extracts_from_generic_fence(self):
        """Should extract code between ``` markers without language tag."""
        response = "```\nconst x = 1;\n```"
        assert _extract_code_block(response) == "const x = 1;"

    def test_returns_raw_when_no_fences(self):
        """No code fences → return entire response stripped."""
        response = "const x = 1;"
        assert _extract_code_block(response) == "const x = 1;"

    def test_handles_only_opening_fence(self):
        """Only opening fence → return everything after it."""
        response = "```tsx\nconst x = 1;\nconst y = 2;"
        result = _extract_code_block(response)
        assert "const x = 1;" in result
        assert "const y = 2;" in result

    def test_strips_whitespace(self):
        """Should strip leading/trailing whitespace from extracted code."""
        response = "```tsx\n  \n  const x = 1;\n  \n```"
        result = _extract_code_block(response)
        assert result.strip() == result

    def test_empty_response(self):
        """Empty string should return empty string."""
        assert _extract_code_block("") == ""

    def test_multiline_code(self):
        """Should preserve multiple lines of code."""
        response = "```tsx\nimport {AbsoluteFill} from 'remotion';\n\nexport default function GeneratedScene() {\n  return <AbsoluteFill />;\n}\n```"
        result = _extract_code_block(response)
        assert "import" in result
        assert "export default" in result
        assert "AbsoluteFill" in result


class TestCreateClient:
    """Test LLM client factory for different providers."""

    def test_ollama_creates_client(self):
        """Ollama should create a client without API keys."""
        client, model = _create_client("ollama")
        assert client is not None
        assert model == "llama3"

    def test_ollama_respects_host_env(self):
        """Ollama should use OLLAMA_HOST env var if set."""
        with patch.dict(os.environ, {"OLLAMA_HOST": "http://myhost:11434"}):
            client, model = _create_client("ollama")
            assert client is not None

    def test_openai_missing_key_raises(self):
        """OpenAI without OPENAI_API_KEY should raise LLMError."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove the key if it exists
            env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
            with patch.dict(os.environ, env, clear=True):
                with pytest.raises(LLMError, match="OPENAI_API_KEY"):
                    _create_client("openai")

    def test_azure_missing_credentials_raises(self):
        """Azure without required env vars should raise LLMError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(LLMError, match="AZURE_OPENAI"):
                _create_client("azure")

    def test_azure_partial_credentials_raises(self):
        """Azure with only endpoint (missing key) should raise LLMError."""
        env = {"AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(LLMError):
                _create_client("azure")

    def test_unknown_provider_raises(self):
        """Unknown provider name should raise LLMError."""
        with pytest.raises(LLMError, match="Unknown provider"):
            _create_client("anthropic")

    def test_provider_case_insensitive(self):
        """Provider name should be case-insensitive."""
        client, model = _create_client("OLLAMA")
        assert client is not None


class TestGenerateComponent:
    """Test component generation with mocked LLM calls."""

    VALID_TSX = (
        "import {AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate} "
        "from 'remotion';\n\n"
        "export default function GeneratedScene() {\n"
        "  const frame = useCurrentFrame();\n"
        "  const {fps, durationInFrames} = useVideoConfig();\n"
        "  const opacity = interpolate(frame, [0, 30], [0, 1], "
        "{extrapolateRight: 'clamp'});\n"
        "  return (\n"
        "    <AbsoluteFill style={{backgroundColor: '#0a0a2e'}}>\n"
        "      <h1 style={{color: '#fff', opacity}}>Hello</h1>\n"
        "    </AbsoluteFill>\n"
        "  );\n"
        "}"
    )

    @patch("remotion_gen.llm_client._call_llm")
    @patch("remotion_gen.llm_client._create_client")
    def test_happy_path(self, mock_create, mock_call):
        """Valid LLM response should return TSX code."""
        mock_create.return_value = (MagicMock(), "llama3")
        mock_call.return_value = self.VALID_TSX

        result = generate_component(
            "A blue circle",
            duration_seconds=5,
            fps=30,
            provider="ollama",
        )
        assert "GeneratedScene" in result
        assert "AbsoluteFill" in result

    @patch("remotion_gen.llm_client._call_llm")
    @patch("remotion_gen.llm_client._create_client")
    def test_api_failure_raises_llm_error(self, mock_create, mock_call):
        """LLM API failure should propagate as LLMError."""
        mock_create.return_value = (MagicMock(), "llama3")
        mock_call.side_effect = LLMError("Connection refused")

        with pytest.raises(LLMError, match="Connection refused"):
            generate_component(
                "A blue circle",
                duration_seconds=5,
                fps=30,
            )

    @patch("remotion_gen.llm_client._call_llm")
    @patch("remotion_gen.llm_client._create_client")
    def test_includes_image_context_in_prompt(self, mock_create, mock_call):
        """Image context should be included in the LLM prompt."""
        mock_create.return_value = (MagicMock(), "llama3")
        mock_call.return_value = self.VALID_TSX

        generate_component(
            "Show my photo",
            duration_seconds=5,
            fps=30,
            image_context="Use staticFile('photo.png') to display the image.",
        )

        # Check that the user prompt passed to _call_llm includes image context
        call_args = mock_call.call_args
        user_prompt = call_args[0][3]  # positional arg 4: user_prompt
        assert "staticFile" in user_prompt

    @patch("remotion_gen.llm_client._call_llm")
    @patch("remotion_gen.llm_client._create_client")
    def test_retry_on_syntax_errors(self, mock_create, mock_call):
        """Should retry when TSX has structural errors and retries are enabled."""
        mock_create.return_value = (MagicMock(), "llama3")
        # First call returns bad code (missing closing paren), second returns good
        bad_tsx = "export default function GeneratedScene() { return (<div>unclosed"
        mock_call.side_effect = [bad_tsx, self.VALID_TSX]

        result = generate_component(
            "A circle",
            duration_seconds=5,
            fps=30,
            max_retries=1,
        )
        assert mock_call.call_count == 2
        assert "GeneratedScene" in result

    @patch("remotion_gen.llm_client._call_llm")
    @patch("remotion_gen.llm_client._create_client")
    def test_no_retry_by_default(self, mock_create, mock_call):
        """With max_retries=0, should return code even with syntax errors."""
        mock_create.return_value = (MagicMock(), "llama3")
        bad_tsx = "export default function GeneratedScene() { return (<div>unclosed"
        mock_call.return_value = bad_tsx

        result = generate_component(
            "A circle",
            duration_seconds=5,
            fps=30,
            max_retries=0,
        )
        # Returns the bad code (write_component will catch it later)
        assert mock_call.call_count == 1
        assert "unclosed" in result

    @patch("remotion_gen.llm_client._call_llm")
    @patch("remotion_gen.llm_client._create_client")
    def test_model_override(self, mock_create, mock_call):
        """Custom model name should be used instead of default."""
        mock_create.return_value = (MagicMock(), "llama3")
        mock_call.return_value = self.VALID_TSX

        generate_component(
            "A circle",
            duration_seconds=5,
            fps=30,
            model="codellama",
        )
        # _call_llm should be called with the overridden model
        call_args = mock_call.call_args
        assert call_args[0][1] == "codellama"
