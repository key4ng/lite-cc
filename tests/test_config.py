import os
from cc.config import load_config


def test_defaults():
    config = load_config()
    assert config.model == "oci/openai.gpt-5.2"
    assert config.max_iterations == 100
    assert config.timeout == 120
    assert config.project_dir is not None


def test_env_override(monkeypatch):
    monkeypatch.setenv("CC_MODEL", "openai/gpt-4o")
    config = load_config()
    assert config.model == "openai/gpt-4o"


def test_kwargs_override(monkeypatch):
    monkeypatch.setenv("CC_MODEL", "openai/gpt-4o")
    config = load_config(model="anthropic/claude-3")
    assert config.model == "anthropic/claude-3"
