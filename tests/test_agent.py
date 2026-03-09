from unittest.mock import MagicMock
from cc.agent import run_agent
from cc.config import Config
from cc.llm import LLMResponse, ToolCall


def test_simple_response_no_tools():
    config = Config(model="oci/xai.grok-4-1-fast-reasoning", max_iterations=10)
    mock_client = MagicMock()
    mock_client.chat.return_value = LLMResponse(text="Hello!", tool_calls=[])

    result = run_agent(
        prompt="say hi",
        config=config,
        llm=mock_client,
        plugins=[],
    )
    assert result == "Hello!"
    assert mock_client.chat.call_count == 1


def test_tool_call_then_response():
    config = Config(model="oci/xai.grok-4-1-fast-reasoning", max_iterations=10)
    mock_client = MagicMock()

    first_response = LLMResponse(
        text=None,
        tool_calls=[ToolCall(id="call_1", name="bash", arguments={"command": "echo hello"})],
    )
    second_response = LLMResponse(text="Done! Output was hello.", tool_calls=[])
    mock_client.chat.side_effect = [first_response, second_response]

    result = run_agent(
        prompt="run echo hello",
        config=config,
        llm=mock_client,
        plugins=[],
    )
    assert "Done" in result
    assert mock_client.chat.call_count == 2


def test_max_iterations_stops_loop():
    config = Config(model="oci/xai.grok-4-1-fast-reasoning", max_iterations=2)
    mock_client = MagicMock()
    mock_client.chat.return_value = LLMResponse(
        text=None,
        tool_calls=[ToolCall(id="call_1", name="bash", arguments={"command": "echo loop"})],
    )

    result = run_agent(
        prompt="loop forever",
        config=config,
        llm=mock_client,
        plugins=[],
    )
    assert mock_client.chat.call_count == 2
