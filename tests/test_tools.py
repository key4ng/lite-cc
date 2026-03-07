# tests/test_tools.py
import os
from cc.tools import get_all_tools, execute_tool
from cc.safety import SafetyChecker


def test_get_all_tools_returns_six():
    tools = get_all_tools(skill_descriptions=[])
    names = [t["function"]["name"] for t in tools]
    assert "bash" in names
    assert "read_file" in names
    assert "write_file" in names
    assert "list_files" in names
    assert "grep" in names
    assert "use_skill" in names


def test_bash_executes(tmp_path):
    sc = SafetyChecker(project_dir=str(tmp_path))
    result = execute_tool("bash", {"command": "echo hello"}, sc, str(tmp_path))
    assert "hello" in result


def test_bash_blocked_command(tmp_path):
    sc = SafetyChecker(project_dir=str(tmp_path))
    result = execute_tool("bash", {"command": "rm -rf /"}, sc, str(tmp_path))
    assert "Blocked" in result


def test_read_file(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("line1\nline2\nline3\n")
    sc = SafetyChecker(project_dir=str(tmp_path))
    result = execute_tool("read_file", {"path": str(f)}, sc, str(tmp_path))
    assert "line1" in result
    assert "line3" in result


def test_read_file_outside_project(tmp_path):
    sc = SafetyChecker(project_dir=str(tmp_path))
    result = execute_tool("read_file", {"path": "/etc/passwd"}, sc, str(tmp_path))
    assert "denied" in result.lower() or "outside" in result.lower()


def test_write_file(tmp_path):
    sc = SafetyChecker(project_dir=str(tmp_path))
    target = str(tmp_path / "output.txt")
    result = execute_tool("write_file", {"path": target, "content": "hello"}, sc, str(tmp_path))
    assert "ok" in result.lower() or "wrote" in result.lower()
    assert (tmp_path / "output.txt").read_text() == "hello"


def test_write_file_outside_project(tmp_path):
    sc = SafetyChecker(project_dir=str(tmp_path))
    result = execute_tool("write_file", {"path": "/tmp/evil.txt", "content": "bad"}, sc, str(tmp_path))
    assert "denied" in result.lower() or "outside" in result.lower()


def test_list_files(tmp_path):
    (tmp_path / "a.py").write_text("")
    (tmp_path / "b.txt").write_text("")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.py").write_text("")
    sc = SafetyChecker(project_dir=str(tmp_path))
    result = execute_tool("list_files", {"pattern": "**/*.py"}, sc, str(tmp_path))
    assert "a.py" in result
    assert "c.py" in result


def test_grep(tmp_path):
    (tmp_path / "file.py").write_text("def hello():\n    return 'world'\n")
    sc = SafetyChecker(project_dir=str(tmp_path))
    result = execute_tool("grep", {"pattern": "hello", "path": "."}, sc, str(tmp_path))
    assert "hello" in result
