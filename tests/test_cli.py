from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from cc.cli import main
from cc.llm import LLMResponse


def test_run_command_basic():
    runner = CliRunner()
    mock_response = LLMResponse(text="Done!", tool_calls=[])

    with patch("cc.cli.LLMClient") as MockClient:
        MockClient.return_value.chat.return_value = mock_response
        result = runner.invoke(main, ["run", "say hello"])
        assert result.exit_code == 0
