"""LLM client tests for manim-animation."""

from unittest.mock import MagicMock, patch

import pytest

from manim_gen.errors import LLMError
from manim_gen.llm_client import LLMClient


class TestLLMClientOllama:

    def test_ollama_client_initializes(self):
        client = LLMClient(provider="ollama")
        assert client.provider == "ollama"

    @patch("manim_gen.llm_client.LLMClient._get_client")
    def test_ollama_returns_code(self, mock_get_client):
        mock_api = MagicMock()
        mock_api.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="from manim import *"))]
        )
        mock_get_client.return_value = mock_api
        client = LLMClient(provider="ollama")
        result = client.generate_scene_code("test prompt", 10)
        assert "manim" in result

    @patch("manim_gen.llm_client.LLMClient._get_client")
    def test_api_error_raises_llm_error(self, mock_get_client):
        mock_api = MagicMock()
        mock_api.chat.completions.create.side_effect = Exception("timeout")
        mock_get_client.return_value = mock_api
        client = LLMClient(provider="ollama")
        with pytest.raises(LLMError, match="LLM API call failed"):
            client.generate_scene_code("test", 10)

class TestLLMClientOpenAI:

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_openai_client_initializes(self):
        client = LLMClient(provider="openai")
        assert client.provider == "openai"
        assert client.api_key == "test-key"

    def test_openai_missing_api_key_raises_error(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(LLMError, match="OPENAI_API_KEY"):
                LLMClient(provider="openai")

class TestLLMClientAzure:

    @patch.dict(
        "os.environ",
        {
            "AZURE_OPENAI_KEY": "key",
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
            "AZURE_OPENAI_DEPLOYMENT": "gpt-4",
        },
    )
    def test_azure_client_initializes(self):
        client = LLMClient(provider="azure")
        assert client.provider == "azure"

    def test_azure_missing_credentials_raises_error(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(LLMError, match="Azure OpenAI requires"):
                LLMClient(provider="azure")

    def test_unknown_provider_raises_error(self):
        with pytest.raises(LLMError, match="Unknown provider"):
            LLMClient(provider="gemini")
