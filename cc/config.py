"""Configuration loading: CLI flags > env vars > yaml > defaults."""

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Config:
    model: str = "oci/openai.gpt-5.2"
    max_iterations: int = 50
    timeout: int = 120
    max_output_lines: int = 2000
    max_output_bytes: int = 100_000
    project_dir: str = ""
    plugin_dirs: list[str] = field(default_factory=list)
    oci_region: str = "us-chicago-1"
    oci_compartment: str = ""
    oci_config_profile: str = "DEFAULT"


def _load_yaml_config() -> dict:
    path = Path.home() / ".cc" / "config.yaml"
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f) or {}
    return {}


def load_config(**kwargs) -> Config:
    """Load config: kwargs (CLI) > env vars > yaml > defaults."""
    yaml_conf = _load_yaml_config()
    config = Config()

    # Layer 1: yaml
    for key in ("model", "max_iterations", "timeout", "project_dir",
                "oci_region", "oci_compartment", "oci_config_profile"):
        if key in yaml_conf:
            setattr(config, key, yaml_conf[key])

    # Layer 2: env vars
    env_map = {
        "CC_MODEL": "model",
        "CC_OCI_REGION": "oci_region",
        "CC_OCI_COMPARTMENT": "oci_compartment",
        "CC_OCI_CONFIG_PROFILE": "oci_config_profile",
        "CC_MAX_ITERATIONS": "max_iterations",
        "CC_TIMEOUT": "timeout",
    }
    for env_key, attr in env_map.items():
        val = os.environ.get(env_key)
        if val is not None:
            expected_type = type(getattr(config, attr))
            setattr(config, attr, expected_type(val))

    # Layer 3: CLI kwargs (highest priority)
    for key, val in kwargs.items():
        if val is not None and hasattr(config, key):
            setattr(config, key, val)

    if not config.project_dir:
        config.project_dir = os.getcwd()

    return config
