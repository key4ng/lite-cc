"""Tests for subagent core module."""

from unittest.mock import MagicMock, patch
from cc.subagent import SubagentTask, SubagentResult, run_subagent, run_subagents_parallel
from cc.llm import LLMResponse, ToolCall, Usage
from cc.config import Config
from cc.agent import LoopResult


def test_subagent_task_defaults():
    task = SubagentTask(prompt="do stuff")
    assert task.model is None
    assert task.tools is None
    assert task.max_iterations == 10
    assert task.max_output_tokens == 50_000
    assert task.timeout == 120
    assert task.context is None
    assert task.system_prompt is None


def test_subagent_result_defaults():
    result = SubagentResult(text="ok", model="test", usage=Usage(), iterations_used=1)
    assert result.success is True
    assert result.error is None


def test_subagent_result_error():
    result = SubagentResult(text=None, model="test", usage=Usage(), iterations_used=0, success=False, error="boom")
    assert result.success is False
    assert result.error == "boom"


def test_run_subagent_simple():
    """Subagent returns text result from a simple prompt."""
    task = SubagentTask(prompt="say hi", model="test-model", project_dir="/tmp")

    mock_response = LLMResponse(text="Hello!", tool_calls=[], usage=Usage(input_tokens=10, output_tokens=5))

    with patch("cc.subagent.LLMClient") as MockLLM:
        mock_client = MagicMock()
        mock_client.chat.return_value = mock_response
        MockLLM.return_value = mock_client

        result = run_subagent(task)
        assert result.success is True
        assert result.text == "Hello!"
        assert result.model == "test-model"
        assert result.iterations_used == 1


def test_run_subagent_with_context():
    """Context messages should be injected before the prompt."""
    task = SubagentTask(
        prompt="review it",
        model="test-model",
        project_dir="/tmp",
        context=[{"role": "user", "content": "Here is the diff: ..."}],
    )

    mock_response = LLMResponse(text="Looks good", tool_calls=[], usage=Usage())

    with patch("cc.subagent.LLMClient") as MockLLM:
        mock_client = MagicMock()
        mock_client.chat.return_value = mock_response
        MockLLM.return_value = mock_client

        result = run_subagent(task)
        assert result.success is True

        # Check messages passed to chat: system, context, user prompt
        messages = mock_client.chat.call_args[0][0]
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "diff" in messages[1]["content"]
        assert messages[2]["role"] == "user"
        assert messages[2]["content"] == "review it"


def test_run_subagent_error_handling():
    """Subagent should catch exceptions and return error result."""
    task = SubagentTask(prompt="fail", model="test-model", project_dir="/tmp")

    with patch("cc.subagent.LLMClient") as MockLLM:
        MockLLM.side_effect = RuntimeError("connection failed")

        result = run_subagent(task)
        assert result.success is False
        assert "connection failed" in result.error


def test_run_subagent_default_model():
    """When model is None, should use default from Config."""
    task = SubagentTask(prompt="hi", project_dir="/tmp")

    mock_response = LLMResponse(text="yo", tool_calls=[], usage=Usage())

    with patch("cc.subagent.LLMClient") as MockLLM:
        mock_client = MagicMock()
        mock_client.chat.return_value = mock_response
        MockLLM.return_value = mock_client

        result = run_subagent(task)
        assert result.success is True
        assert result.model == Config().model


def test_run_subagent_tool_filtering():
    """Subagent should only get requested tools, never spawn_subagent."""
    task = SubagentTask(prompt="read files", model="test-model", project_dir="/tmp", tools=["read_file", "grep"])

    mock_response = LLMResponse(text="done", tool_calls=[], usage=Usage())

    with patch("cc.subagent.LLMClient") as MockLLM:
        mock_client = MagicMock()
        mock_client.chat.return_value = mock_response
        MockLLM.return_value = mock_client

        result = run_subagent(task)
        assert result.success is True

        # Check tool defs passed to chat
        tools = mock_client.chat.call_args[0][1]
        tool_names = [t["function"]["name"] for t in tools]
        assert "read_file" in tool_names
        assert "grep" in tool_names
        assert "bash" not in tool_names
        assert "spawn_subagent" not in tool_names


def test_run_subagent_invalid_tool_warns(capsys):
    """Unknown tool names should be warned and ignored."""
    task = SubagentTask(prompt="hi", model="test-model", project_dir="/tmp", tools=["read_file", "nonexistent_tool"])

    mock_response = LLMResponse(text="ok", tool_calls=[], usage=Usage())

    with patch("cc.subagent.LLMClient") as MockLLM:
        mock_client = MagicMock()
        mock_client.chat.return_value = mock_response
        MockLLM.return_value = mock_client

        result = run_subagent(task)
        assert result.success is True
        captured = capsys.readouterr()
        assert "nonexistent_tool" in captured.err


def test_run_subagent_no_valid_tools():
    """Should return error if all tools are invalid."""
    task = SubagentTask(prompt="hi", model="test-model", project_dir="/tmp", tools=["fake_tool"])

    result = run_subagent(task)
    assert result.success is False
    assert "No valid tools" in result.error


def test_run_subagents_parallel():
    """Multiple subagents should run and all return results."""
    tasks = [
        SubagentTask(prompt="task 1", model="model-a", project_dir="/tmp"),
        SubagentTask(prompt="task 2", model="model-b", project_dir="/tmp"),
    ]

    mock_response = LLMResponse(text="done", tool_calls=[], usage=Usage(input_tokens=10, output_tokens=5))

    with patch("cc.subagent.LLMClient") as MockLLM:
        mock_client = MagicMock()
        mock_client.chat.return_value = mock_response
        MockLLM.return_value = mock_client

        results = run_subagents_parallel(tasks)
        assert len(results) == 2
        assert all(r.success for r in results)


def test_run_subagents_parallel_partial_failure():
    """If one subagent fails, others should still complete."""
    tasks = [
        SubagentTask(prompt="ok task", model="model-a", project_dir="/tmp"),
        SubagentTask(prompt="fail task", model="model-b", project_dir="/tmp"),
    ]

    mock_response = LLMResponse(text="done", tool_calls=[], usage=Usage())

    with patch("cc.subagent.LLMClient") as MockLLM:
        good_client = MagicMock()
        good_client.chat.return_value = mock_response

        bad_client = MagicMock()
        bad_client.chat.side_effect = RuntimeError("model unavailable")

        MockLLM.side_effect = [good_client, bad_client]

        results = run_subagents_parallel(tasks)
        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False
        assert "model unavailable" in results[1].error


def test_subagent_in_agent_loop():
    """Agent loop should execute spawn_subagent tool calls."""
    from cc.agent import run_agent

    config = Config(model="test-model", max_iterations=5, project_dir="/tmp")
    mock_client = MagicMock()

    # First response: agent calls spawn_subagent
    first_response = LLMResponse(
        text="Let me spawn a subagent",
        tool_calls=[ToolCall(
            id="call_1",
            name="spawn_subagent",
            arguments={"prompt": "say hi", "model": "test-model"},
        )],
        usage=Usage(input_tokens=100, output_tokens=20),
    )
    # Second response: agent returns final answer
    second_response = LLMResponse(text="Subagent said hello", tool_calls=[], usage=Usage())

    mock_client.chat.side_effect = [first_response, second_response]

    with patch("cc.subagent.LLMClient") as MockSubLLM:
        sub_client = MagicMock()
        sub_response = LLMResponse(text="hello from subagent", tool_calls=[], usage=Usage(input_tokens=10, output_tokens=5))
        sub_client.chat.return_value = sub_response
        MockSubLLM.return_value = sub_client

        result = run_agent(prompt="use a subagent", config=config, llm=mock_client, plugins=[])
        assert "Subagent said hello" in result
