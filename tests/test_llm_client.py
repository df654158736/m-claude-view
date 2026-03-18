import pytest
from unittest.mock import Mock, patch
from src.llm_client import LLMClient


def test_llm_client_initialization():
    """Test LLM client can be initialized with config."""
    config = Mock()
    config.api_key = "test-key"
    config.base_url = "https://api.example.com"
    config.model = "test-model"
    config.temperature = 0.7

    client = LLMClient(config)
    assert client.model == "test-model"
    assert client.api_key == "test-key"


def test_llm_client_chat_returns_response():
    """Test LLM client chat method returns a response."""
    config = Mock()
    config.api_key = "test-key"
    config.base_url = "https://api.example.com"
    config.model = "test-model"
    config.temperature = 0.7

    # Mock the OpenAI client
    with patch('src.llm_client.OpenAI') as mock_openai:
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Hello"
        mock_response.choices[0].message.tool_calls = None

        mock_openai.return_value.chat.completions.create.return_value = mock_response

        client = LLMClient(config)
        result = client.chat([{"role": "user", "content": "hi"}])

        assert result is not None