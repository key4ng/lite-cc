# lite-cc — Long-Term Vision

## What is lite-cc?

A lightweight, multi-model coding agent CLI (`cc`) that runs tool loops safely, loads plugins/skills as first-class citizens, and works with any LLM provider.

## Architecture

```
cc (CLI entry point)
|
+-- core/
|   +-- agent_loop.py      # The tool loop: prompt -> LLM -> tool calls -> execute -> repeat
|   +-- session.py          # Conversation state (message history, context)
|   +-- tool_registry.py    # Registry of all available tools (built-in + plugin)
|   +-- safety.py           # Command validation, path restrictions, deny lists
|   +-- config.py           # Config loading (~/.cc/config.yaml, env vars)
|
+-- adapters/
|   +-- litellm_client.py   # LiteLLM wrapper (Chat Completions with tool calling)
|   +-- oci_auth.py         # OCI session token auth for LiteLLM
|
+-- tools/
|   +-- bash.py             # Shell execution with safety checks
|   +-- read_file.py        # Read file contents
|   +-- write_file.py       # Write/patch files
|   +-- list_files.py       # Glob/list directory
|   +-- grep.py             # Search file contents
|
+-- plugins/
|   +-- loader.py           # Load .claude-plugin/plugin.json dirs
|   +-- registry.py         # Register plugin tools into tool_registry
|
+-- skills/
|   +-- loader.py           # Parse SKILL.md / command .md files
|   +-- runner.py           # Inject skill content into conversation
|
+-- cli/
    +-- main.py             # CLI entry: `cc` (interactive), `cc run "..."` (one-shot)
    +-- output.py           # Terminal output formatting
```

## Core Principles

1. **Simple over clever** — no abstractions until needed twice
2. **Safe by default** — deny dangerous commands, restrict to project dir
3. **Plugins and skills are first-class** — not afterthoughts
4. **Provider-agnostic** — LiteLLM handles model routing
5. **One tool loop** — same loop for interactive and run mode

## Model Support Strategy

All model interaction goes through LiteLLM's `completion()` with `tools=` parameter.
This gives us Chat Completions tool calling for all providers LiteLLM supports.

For OCI-hosted OpenAI models specifically:
- Use `oci_signer`, `oci_region_name`, `oci_compartment_id` params
- Patch OCIChatConfig for max_completion_tokens (from existing codex-oci proxy)

No need to implement Responses API internally — that's an OpenAI-specific protocol.
We normalize everything to messages + tool_calls internally.

## Plugin Format (Claude-compatible)

```
my-plugin/
  .claude-plugin/
    plugin.json          # { "name": "...", "description": "...", "version": "..." }
  CLAUDE.md              # Plugin-level instructions (injected into system prompt)
  pipeline/              # or skills/, commands/ — flexible
    my-skill/
      SKILL.md           # Skill definition with YAML frontmatter + markdown body
    my-command/
      command-name.md    # Command definition
```

Skills have YAML frontmatter:
```yaml
---
name: skill-name
description: When to trigger this skill
---
# Skill body (markdown with instructions)
```

## Safety Model

Four layers:
1. **Command deny list** — block `rm -rf`, `sudo`, `shutdown`, `mkfs`, `dd`, etc.
2. **Path restrictions** — tools only access project directory (configurable)
3. **Output limits** — truncate stdout after N lines/bytes
4. **Timeouts** — kill commands after configurable duration

In "run mode" (full auto), safety is enforced programmatically — no prompts.
In "interactive mode" (future), dangerous commands can optionally prompt.

## Future Roadmap

- Interactive mode with REPL
- Streaming output display
- Conversation persistence/resume
- MCP (Model Context Protocol) server support
- Sandbox mode (Docker/firejail)
- Multi-agent orchestration
- Custom tool definitions in YAML/JSON
- Token budget management
- Configurable safety policies per project (.cc/safety.yaml)
