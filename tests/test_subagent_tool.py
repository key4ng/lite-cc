"""Tests for spawn_subagent tool."""

from unittest.mock import MagicMock, patch
from cc.tools.subagent import TOOL_DEF, execute
from cc.safety import SafetyChecker
from cc.config import Config
from cc.llm import LLMResponse, Usage
import tempfile


def test_tool_def_structure():
    assert TOOL_DEF["function"]["name"] == "spawn_subagent"
    params = TOOL_DEF["function"]["parameters"]
    assert "prompt" in params["properties"]
    assert "model" in params["properties"]
    assert "tools" in params["properties"]
    assert params["required"] == ["prompt"]


def test_execute_calls_run_subagent():
    """spawn_subagent tool should call run_subagent and return result text."""
    with tempfile.TemporaryDirectory() as tmp:
        safety = SafetyChecker(project_dir=tmp)
        config = Config(model="default-model", project_dir=tmp)

        mock_response = LLMResponse(
            text="review complete", tool_calls=[],
            usage=Usage(input_tokens=100, output_tokens=50),
        )

        with patch("cc.subagent.LLMClient") as MockLLM:
            mock_client = MagicMock()
            mock_client.chat.return_value = mock_response
            MockLLM.return_value = mock_client

            result = execute(
                {"prompt": "review this", "model": "oci/openai.gpt-5.4"},
                safety, tmp, config=config, plugins=[],
            )
            assert "review complete" in result
            assert "gpt-5.4" in result


def test_execute_returns_error_on_failure():
    """spawn_subagent tool should return error string on failure."""
    with tempfile.TemporaryDirectory() as tmp:
        safety = SafetyChecker(project_dir=tmp)
        config = Config(model="default-model", project_dir=tmp)

        with patch("cc.subagent.LLMClient") as MockLLM:
            MockLLM.side_effect = RuntimeError("model not found")

            result = execute(
                {"prompt": "fail", "model": "bad-model"},
                safety, tmp, config=config, plugins=[],
            )
            assert "Error" in result
            assert "model not found" in result


def test_execute_default_read_only_tools():
    """When no tools specified, should default to read-only."""
    with tempfile.TemporaryDirectory() as tmp:
        safety = SafetyChecker(project_dir=tmp)
        config = Config(model="default-model", project_dir=tmp)

        mock_response = LLMResponse(text="ok", tool_calls=[], usage=Usage())

        with patch("cc.subagent.LLMClient") as MockLLM:
            mock_client = MagicMock()
            mock_client.chat.return_value = mock_response
            MockLLM.return_value = mock_client

            result = execute(
                {"prompt": "read stuff"},
                safety, tmp, config=config, plugins=[],
            )

            # Verify the subagent got the right tools by checking chat was called
            # with only read-only tool defs
            tools = mock_client.chat.call_args[0][1]
            tool_names = [t["function"]["name"] for t in tools]
            assert "read_file" in tool_names
            assert "list_files" in tool_names
            assert "grep" in tool_names
            assert "bash" not in tool_names
            assert "write_file" not in tool_names
            assert "spawn_subagent" not in tool_names
