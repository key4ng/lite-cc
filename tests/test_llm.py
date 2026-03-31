from unittest.mock import patch, MagicMock
from cc.llm import LLMClient, LLMResponse, ToolCall
from cc.config import Config


def test_chat_calls_litellm():
    config = Config(model="xai.grok-4-1-fast-reasoning")
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
    config = Config(model="xai.grok-4-1-fast-reasoning")
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
    """OCI non-Responses-API models go through litellm with signer."""
    config = Config(model="oci/meta.llama-3.3-70b-instruct", oci_region="us-chicago-1", oci_compartment="ocid1.test")
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


def test_oci_responses_api_routing():
    """OCI xai.* and openai.* models use the Responses API."""
    config = Config(model="oci/xai.grok-4-1-fast-reasoning", oci_region="us-chicago-1", oci_compartment="ocid1.test")
    client = LLMClient(config)
    assert client._use_responses_api() is True

    config2 = Config(model="oci/openai.gpt-4o", oci_region="us-chicago-1", oci_compartment="ocid1.test")
    client2 = LLMClient(config2)
    assert client2._use_responses_api() is True

    config3 = Config(model="oci/meta.llama-3.3-70b-instruct", oci_region="us-chicago-1", oci_compartment="ocid1.test")
    client3 = LLMClient(config3)
    assert client3._use_responses_api() is False


def test_oci_responses_api_fc_ids():
    """Responses API conversion generates fc-prefixed IDs."""
    from cc.llm import _convert_messages_to_responses_input
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": None, "tool_calls": [
            {"id": "call_abc123", "type": "function", "function": {"name": "bash", "arguments": '{"command": "ls"}'}},
        ]},
        {"role": "tool", "tool_call_id": "call_abc123", "content": "file1.txt"},
    ]
    system, items = _convert_messages_to_responses_input(messages)
    assert system == "You are helpful."
    # function_call item should have fc-prefixed id
    fc_item = [i for i in items if i["type"] == "function_call"][0]
    assert fc_item["id"].startswith("fc_")
    assert fc_item["call_id"].startswith("fc_")
    # function_call_output should reference the same fc id
    out_item = [i for i in items if i["type"] == "function_call_output"][0]
    assert out_item["call_id"] == fc_item["call_id"]
