"""Plugin and skill loader — reads Claude-style plugin directories."""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class SkillInfo:
    name: str
    description: str
    content: str
    file_path: str


@dataclass
class PluginInfo:
    name: str
    description: str
    version: str
    claude_md: str = ""
    skills: dict[str, SkillInfo] = field(default_factory=dict)


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown. Returns (metadata, body)."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)", text, re.DOTALL)
    if not match:
        return {}, text
    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        meta = {}
    return meta, match.group(2)


def _scan_skills(plugin_dir: Path) -> dict[str, SkillInfo]:
    """Find all SKILL.md and commands/*.md files."""
    skills = {}

    for skill_file in plugin_dir.rglob("SKILL.md"):
        meta, body = _parse_frontmatter(skill_file.read_text())
        name = meta.get("name", skill_file.parent.name)
        skills[name] = SkillInfo(
            name=name,
            description=meta.get("description", ""),
            content=body,
            file_path=str(skill_file),
        )

    commands_dir = plugin_dir / "commands"
    if commands_dir.exists():
        for cmd_file in commands_dir.glob("*.md"):
            meta, body = _parse_frontmatter(cmd_file.read_text())
            name = cmd_file.stem
            skills[name] = SkillInfo(
                name=name,
                description=meta.get("description", ""),
                content=body,
                file_path=str(cmd_file),
            )

    return skills


def load_plugins(plugin_dirs: list[str]) -> list[PluginInfo]:
    """Load plugins from a list of directories."""
    plugins = []

    for dir_path in plugin_dirs:
        root = Path(dir_path)
        manifest_path = root / ".claude-plugin" / "plugin.json"

        if not manifest_path.exists():
            continue

        try:
            manifest = json.loads(manifest_path.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        claude_md = ""
        claude_md_path = root / "CLAUDE.md"
        if claude_md_path.exists():
            claude_md = claude_md_path.read_text()

        skills = _scan_skills(root)

        plugins.append(PluginInfo(
            name=manifest.get("name", root.name),
            description=manifest.get("description", ""),
            version=manifest.get("version", "0.0.0"),
            claude_md=claude_md,
            skills=skills,
        ))

    return plugins
