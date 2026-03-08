from unittest.mock import patch, MagicMock
from cc.llm import LLMClient, LLMResponse, ToolCall
from cc.config import Config


def test_chat_calls_litellm():
    config = Config(model="openai/gpt-4o")
    client = LLMClient(config)
    messages = [{"role": "user", "content": "hello"}]
    tools = []

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Hi there"
    mock_response.choices[0].message.tool_calls = None
    mock_response.choices[0].finish_reason = "stop"

    with patch("litellm.completion", return_value=mock_response) as mock_comp:
        response = client.chat(messages, tools)
        mock_comp.assert_called_once()
        assert response.text == "Hi there"
        assert response.tool_calls == []


def test_chat_with_tool_calls():
    config = Config(model="openai/gpt-4o")
    client = LLMClient(config)

    mock_tc = MagicMock()
    mock_tc.id = "call_123"
    mock_tc.function.name = "bash"
    mock_tc.function.arguments = '{"command": "ls"}'

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = None
    mock_response.choices[0].message.tool_calls = [mock_tc]
    mock_response.choices[0].finish_reason = "tool_calls"

    with patch("litellm.completion", return_value=mock_response):
        response = client.chat(
            [{"role": "user", "content": "list files"}],
            [{"type": "function", "function": {"name": "bash"}}]
        )
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].name == "bash"
        assert response.tool_calls[0].arguments == {"command": "ls"}


def test_oci_model_adds_signer():
    config = Config(model="oci/openai.gpt-5.2", oci_region="us-chicago-1", oci_compartment="ocid1.test")
    client = LLMClient(config)

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "ok"
    mock_response.choices[0].message.tool_calls = None
    mock_response.choices[0].finish_reason = "stop"

    with patch("litellm.completion", return_value=mock_response) as mock_comp:
        with patch("cc.llm._get_oci_signer", return_value=MagicMock()):
            client.chat([{"role": "user", "content": "hi"}], [])
            call_kwargs = mock_comp.call_args.kwargs
            assert "oci_signer" in call_kwargs
            assert call_kwargs["oci_region"] == "us-chicago-1"
