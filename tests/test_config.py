import os
from cc.config import load_config


def test_defaults(monkeypatch, tmp_path):
    # Isolate from user's ~/.cc/config.yaml and env vars
    monkeypatch.setattr("cc.config.Path.home", lambda: tmp_path)
    monkeypatch.delenv("CC_MODEL", raising=False)
    config = load_config()
    assert config.model == "oci/xai.grok-4-1-fast-reasoning"
    assert config.max_iterations == 100
    assert config.timeout == 120
    assert config.project_dir is not None


def test_env_override(monkeypatch):
    monkeypatch.setenv("CC_MODEL", "oci/xai.grok-4-1-fast-reasoning")
    config = load_config()
    assert config.model == "oci/xai.grok-4-1-fast-reasoning"


def test_kwargs_override(monkeypatch):
    monkeypatch.setenv("CC_MODEL", "oci/xai.grok-4-1-fast-reasoning")
    config = load_config(model="anthropic/claude-3")
    assert config.model == "anthropic/claude-3"
