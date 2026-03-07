from cc.plugins.loader import load_plugins, PluginInfo


def test_load_plugin_with_manifest(tmp_path):
    plugin_dir = tmp_path / "my-plugin"
    plugin_dir.mkdir()
    (plugin_dir / ".claude-plugin").mkdir()
    (plugin_dir / ".claude-plugin" / "plugin.json").write_text(
        '{"name": "test-plugin", "description": "A test", "version": "1.0"}'
    )
    (plugin_dir / "CLAUDE.md").write_text("You are a helpful plugin.")

    plugins = load_plugins([str(plugin_dir)])
    assert len(plugins) == 1
    assert plugins[0].name == "test-plugin"
    assert plugins[0].claude_md == "You are a helpful plugin."


def test_load_skills_from_plugin(tmp_path):
    plugin_dir = tmp_path / "my-plugin"
    plugin_dir.mkdir()
    (plugin_dir / ".claude-plugin").mkdir()
    (plugin_dir / ".claude-plugin" / "plugin.json").write_text(
        '{"name": "test-plugin", "description": "A test", "version": "1.0"}'
    )
    skill_dir = plugin_dir / "pipeline" / "my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: Does a thing\n---\n# My Skill\nDo the thing."
    )

    plugins = load_plugins([str(plugin_dir)])
    assert len(plugins[0].skills) == 1
    assert plugins[0].skills["my-skill"].name == "my-skill"
    assert "Do the thing" in plugins[0].skills["my-skill"].content


def test_load_commands(tmp_path):
    plugin_dir = tmp_path / "my-plugin"
    plugin_dir.mkdir()
    (plugin_dir / ".claude-plugin").mkdir()
    (plugin_dir / ".claude-plugin" / "plugin.json").write_text(
        '{"name": "test-plugin", "description": "A test", "version": "1.0"}'
    )
    cmd_dir = plugin_dir / "commands"
    cmd_dir.mkdir()
    (cmd_dir / "deploy.md").write_text(
        "---\ndescription: Deploy the app\n---\n# Deploy\nRun deploy steps."
    )

    plugins = load_plugins([str(plugin_dir)])
    assert "deploy" in plugins[0].skills


def test_no_manifest_skips(tmp_path):
    plugin_dir = tmp_path / "not-a-plugin"
    plugin_dir.mkdir()
    plugins = load_plugins([str(plugin_dir)])
    assert len(plugins) == 0
