"""Tests for stream-json output format."""

import json
from io import StringIO
from unittest.mock import patch, MagicMock

from cc.stream import StreamEmitter
from cc.agent import run_agent
from cc.config import Config
from cc.llm import LLMResponse, ToolCall


class TestStreamEmitter:
    def test_system_init(self):
        emitter = StreamEmitter()
        buf = StringIO()
        with patch("sys.stdout", buf):
            emitter.system_init("oci/xai.grok-4-1-fast-reasoning", ["code-analyst"])
        event = json.loads(buf.getvalue().strip())
        assert event["type"] == "system"
        assert event["subtype"] == "init"
        assert event["model"] == "oci/xai.grok-4-1-fast-reasoning"
        assert event["plugins"] == ["code-analyst"]

    def test_system_done(self):
        emitter = StreamEmitter()
        buf = StringIO()
        with patch("sys.stdout", buf):
            emitter.system_done(5)
        event = json.loads(buf.getvalue().strip())
        assert event["type"] == "system"
        assert event["subtype"] == "done"
        assert event["iterations"] == 5

    def test_system_error(self):
        emitter = StreamEmitter()
        buf = StringIO()
        with patch("sys.stdout", buf):
            emitter.system_error("max iterations reached")
        event = json.loads(buf.getvalue().strip())
        assert event["type"] == "system"
        assert event["subtype"] == "error"
        assert event["message"] == "max iterations reached"

    def test_assistant(self):
        emitter = StreamEmitter()
        buf = StringIO()
        with patch("sys.stdout", buf):
            emitter.assistant([{"type": "text", "text": "Hello"}])
        event = json.loads(buf.getvalue().strip())
        assert event["type"] == "assistant"
        assert event["message"]["role"] == "assistant"
        assert event["message"]["content"][0]["text"] == "Hello"

    def test_tool_use(self):
        emitter = StreamEmitter()
        buf = StringIO()
        with patch("sys.stdout", buf):
            emitter.tool_use("tool_01", "bash", {"command": "ls"})
        event = json.loads(buf.getvalue().strip())
        assert event["type"] == "tool_use"
        assert event["name"] == "bash"
        assert event["id"] == "tool_01"
        assert event["input"] == {"command": "ls"}

    def test_tool_result(self):
        emitter = StreamEmitter()
        buf = StringIO()
        with patch("sys.stdout", buf):
            emitter.tool_result("tool_01", "bash", "file1\nfile2", error=False)
        event = json.loads(buf.getvalue().strip())
        assert event["type"] == "tool_result"
        assert event["id"] == "tool_01"
        assert event["output"] == "file1\nfile2"
        assert event["error"] is False

    def test_result(self):
        emitter = StreamEmitter()
        buf = StringIO()
        with patch("sys.stdout", buf):
            emitter.result("Done!", is_error=False, duration_ms=1234, iterations=3)
        event = json.loads(buf.getvalue().strip())
        assert event["type"] == "result"
        assert event["result"] == "Done!"
        assert event["is_error"] is False
        assert event["duration_ms"] == 1234
        assert event["iterations"] == 3

    def test_ndjson_one_line_per_event(self):
        emitter = StreamEmitter()
        buf = StringIO()
        with patch("sys.stdout", buf):
            emitter.system_init("model", [])
            emitter.assistant([{"type": "text", "text": "Hi"}])
            emitter.system_done(1)
        lines = buf.getvalue().strip().split("\n")
        assert len(lines) == 3
        for line in lines:
            json.loads(line)  # each line must be valid JSON


class TestStreamJsonAgent:
    def test_simple_response_emits_stream_json(self):
        config = Config(
            model="oci/xai.grok-4-1-fast-reasoning",
            max_iterations=10,
            verbose=True,
            output_format="stream-json",
        )
        mock_client = MagicMock()
        mock_client.chat.return_value = LLMResponse(text="Hello!", tool_calls=[])

        buf = StringIO()
        with patch("sys.stdout", buf):
            result = run_agent(prompt="say hi", config=config, llm=mock_client, plugins=[])

        assert result == "Hello!"
        lines = buf.getvalue().strip().split("\n")
        events = [json.loads(line) for line in lines]

        types = [e["type"] for e in events]
        assert types[0] == "system"  # init
        assert "assistant" in types
        assert "result" in types
        assert types[-1] == "system"  # done

        # Check init event
        init = events[0]
        assert init["subtype"] == "init"
        assert init["model"] == "oci/xai.grok-4-1-fast-reasoning"

        # Check result event
        result_event = [e for e in events if e["type"] == "result"][0]
        assert result_event["result"] == "Hello!"
        assert result_event["is_error"] is False
        assert result_event["iterations"] == 1

    def test_tool_call_emits_tool_events(self):
        config = Config(
            model="oci/xai.grok-4-1-fast-reasoning",
            max_iterations=10,
            verbose=True,
            output_format="stream-json",
        )
        mock_client = MagicMock()
        first_response = LLMResponse(
            text=None,
            tool_calls=[ToolCall(id="call_1", name="bash", arguments={"command": "echo hello"})],
        )
        second_response = LLMResponse(text="Done!", tool_calls=[])
        mock_client.chat.side_effect = [first_response, second_response]

        buf = StringIO()
        with patch("sys.stdout", buf):
            run_agent(prompt="run echo", config=config, llm=mock_client, plugins=[])

        lines = buf.getvalue().strip().split("\n")
        events = [json.loads(line) for line in lines]
        types = [e["type"] for e in events]

        assert "tool_use" in types
        assert "tool_result" in types

        tool_use = [e for e in events if e["type"] == "tool_use"][0]
        assert tool_use["name"] == "bash"
        assert tool_use["id"] == "call_1"

    def test_max_iterations_emits_error(self):
        config = Config(
            model="oci/xai.grok-4-1-fast-reasoning",
            max_iterations=2,
            verbose=True,
            output_format="stream-json",
        )
        mock_client = MagicMock()
        mock_client.chat.return_value = LLMResponse(
            text=None,
            tool_calls=[ToolCall(id="call_1", name="bash", arguments={"command": "echo loop"})],
        )

        buf = StringIO()
        with patch("sys.stdout", buf):
            run_agent(prompt="loop", config=config, llm=mock_client, plugins=[])

        lines = buf.getvalue().strip().split("\n")
        events = [json.loads(line) for line in lines]

        error_events = [e for e in events if e.get("subtype") == "error"]
        assert len(error_events) == 1
        assert error_events[0]["message"] == "max iterations reached"

        result_events = [e for e in events if e["type"] == "result"]
        assert len(result_events) == 1
        assert result_events[0]["is_error"] is True

    def test_exception_emits_error_event(self):
        config = Config(
            model="oci/xai.grok-4-1-fast-reasoning",
            max_iterations=10,
            verbose=True,
            output_format="stream-json",
        )
        mock_client = MagicMock()
        mock_client.chat.side_effect = RuntimeError("connection failed")

        buf = StringIO()
        with patch("sys.stdout", buf):
            try:
                run_agent(prompt="hello", config=config, llm=mock_client, plugins=[])
            except RuntimeError:
                pass

        lines = buf.getvalue().strip().split("\n")
        events = [json.loads(line) for line in lines]

        # Should have init, then error events
        assert events[0]["type"] == "system"
        assert events[0]["subtype"] == "init"

        error_events = [e for e in events if e.get("subtype") == "error"]
        assert len(error_events) == 1
        assert "connection failed" in error_events[0]["message"]

        result_events = [e for e in events if e["type"] == "result"]
        assert len(result_events) == 1
        assert result_events[0]["is_error"] is True

    def test_text_format_no_stdout(self):
        """Regular text format should not emit anything to stdout."""
        config = Config(model="oci/xai.grok-4-1-fast-reasoning", max_iterations=10, output_format="text")
        mock_client = MagicMock()
        mock_client.chat.return_value = LLMResponse(text="Hello!", tool_calls=[])

        buf = StringIO()
        with patch("sys.stdout", buf):
            run_agent(prompt="say hi", config=config, llm=mock_client, plugins=[])

        assert buf.getvalue() == ""
