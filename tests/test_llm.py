import json
from unittest.mock import MagicMock, patch
import openai
import pytest
from agent.config import LLMConfig
from agent.llm import LLMSession, QuotaExhausted, StageError, generate, generate_json, _extract_json

@pytest.fixture
def dummy_cfg():
    return LLMConfig(
        base_url="https://api.openai.com/v1",
        api_key="sk-dummy",
        model="dummy-model",
        min_interval_s=0.01  # fast for tests
    )

def test_extract_json_clean_and_fenced():
    raw_fenced = "```json\n{\"queries\": [\"test 1\", \"test 2\"]}\n```"
    data = _extract_json(raw_fenced)
    assert data == {"queries": ["test 1", "test 2"]}

    raw_plain = "{\"name\": \"value\"}"
    assert _extract_json(raw_plain) == {"name": "value"}

    raw_array = "[{\"id\": 1}]"
    assert _extract_json(raw_array) == [{"id": 1}]

@patch("agent.llm.OpenAI")
def test_generate_success(mock_openai_cls, dummy_cfg):
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="Hello world"))]
    mock_client.chat.completions.create.return_value = mock_resp
    mock_openai_cls.return_value = mock_client

    result = generate("Test prompt", dummy_cfg)
    assert result == "Hello world"
    mock_client.chat.completions.create.assert_called_once()
    kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert "response_format" not in kwargs

@patch("agent.llm.OpenAI")
def test_generate_json_mode_adds_response_format(mock_openai_cls, dummy_cfg):
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content='{"status": "ok"}'))]
    mock_client.chat.completions.create.return_value = mock_resp
    mock_openai_cls.return_value = mock_client

    result = generate_json("Return status", dummy_cfg)
    assert result == {"status": "ok"}
    kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert kwargs.get("response_format") == {"type": "json_object"}

@patch("agent.llm.OpenAI")
def test_generate_transient_rate_limit_retries_and_succeeds(mock_openai_cls, dummy_cfg):
    mock_client = MagicMock()
    err = openai.RateLimitError(
        message="Rate limit reached: 15 requests per minute",
        response=MagicMock(status_code=429),
        body={}
    )
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="Recovered"))]
    mock_client.chat.completions.create.side_effect = [err, mock_resp]
    mock_openai_cls.return_value = mock_client

    result = generate("Prompt", dummy_cfg)
    assert result == "Recovered"
    assert mock_client.chat.completions.create.call_count == 2

@patch("agent.llm.OpenAI")
def test_generate_daily_quota_fails_fast(mock_openai_cls, dummy_cfg):
    mock_client = MagicMock()
    daily_err = openai.RateLimitError(
        message="You exceeded your current quota per day",
        response=MagicMock(status_code=429),
        body={}
    )
    mock_client.chat.completions.create.side_effect = daily_err
    mock_openai_cls.return_value = mock_client

    with pytest.raises(QuotaExhausted) as exc_info:
        generate("Prompt", dummy_cfg)
    assert "Daily API quota exhausted" in str(exc_info.value)
    # Failed fast without retry loop
    assert mock_client.chat.completions.create.call_count == 1

@patch("agent.llm.OpenAI")
def test_llm_session_tracks_calls(mock_openai_cls, dummy_cfg):
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="Result"))]
    mock_client.chat.completions.create.return_value = mock_resp
    mock_openai_cls.return_value = mock_client

    session = LLMSession(dummy_cfg)
    session.generate("Prompt 1")
    session.generate("Prompt 2")
    assert session.call_count == 2
    assert session.elapsed_seconds >= 0.0
