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


def test_oci_llama_model_uses_chat_completions():
    """OCI meta.llama models should use chat completions via litellm."""
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


def test_oci_xai_model_uses_responses_api():
    """OCI xai.* models should use the Responses API."""
    config = Config(model="oci/xai.grok-4-1-fast-reasoning", oci_region="us-chicago-1", oci_compartment="ocid1.test")
    client = LLMClient(config)

    mock_resp_json = {
        "status": "completed",
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": "ok"}],
            }
        ],
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }

    mock_http_resp = MagicMock()
    mock_http_resp.status_code = 200
    mock_http_resp.json.return_value = mock_resp_json

    mock_signer = MagicMock()

    with patch("cc.llm._get_oci_signer", return_value=mock_signer):
        with patch("requests.Request") as mock_req_cls:
            with patch("requests.Session") as mock_session_cls:
                mock_prepared = MagicMock()
                mock_req_cls.return_value.prepare.return_value = mock_prepared
                mock_session_cls.return_value.send.return_value = mock_http_resp

                response = client.chat([{"role": "user", "content": "hi"}], [])
                assert response.text == "ok"
                mock_signer.assert_called_once_with(mock_prepared)
