# lite-cc MVP Design

**Date:** 2026-03-07
**Status:** Approved

## Summary

A lightweight CLI (`cc`) that runs an automatic tool loop with any LLM provider via LiteLLM, loads Claude-style plugins and skills, and blocks dangerous commands.

## Architecture

```
cc run "prompt" --plugin-dir ~/plugin
        |
        v
   CLI (click) — parse args, load config
        |
        v
   Plugin Loader — scan plugin dir, parse CLAUDE.md + skill frontmatter
        |
        v
   Build system prompt + tool definitions
        |
        v
   Agent Loop:
     1. Send messages + tools to litellm.completion()
     2. If tool_calls → execute each through safety layer → append results → goto 1
     3. If no tool_calls → print final text → exit
```

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| LLM integration | Direct LiteLLM calls | No proxy needed, we're a CLI |
| Model support | Any LiteLLM model, OCI auth when `oci/*` | Barely more work, full flexibility |
| Skill loading | On-demand via `use_skill` tool | Avoids context bloat from pre-loading |
| Output | Progress logging (tool calls + results) | Not token streaming; structured status updates |
| Safety | Deny list + path restrict, no prompts | Full auto mode, deny and tell model why |
| Plugins | CLAUDE.md → system prompt, skills → registry | No plugin-defined tools in MVP |

## CLI Interface

```bash
cc run "prompt"
cc run "prompt" --plugin-dir ~/my-plugin     # repeatable
cc run "prompt" --model anthropic/claude-3
cc run "prompt" --max-iterations 30
cc run "prompt" --project-dir ~/other-repo
```

## Config Resolution (highest wins)

1. CLI flags
2. Env vars: `CC_MODEL`, `CC_OCI_REGION`, `CC_OCI_COMPARTMENT`, `CC_OCI_CONFIG_PROFILE`
3. `~/.cc/config.yaml`
4. Defaults: model `oci/openai.gpt-5.2`, max_iterations 50, timeout 120s

## Tools

| Tool | Purpose |
|------|---------|
| `bash` | Shell command with safety checks, timeout, output limits |
| `read_file` | Read file contents with optional line range |
| `write_file` | Write content to file (project dir only) |
| `list_files` | Glob pattern file search |
| `grep` | Search file contents |
| `use_skill` | Load skill markdown into conversation on demand |

## Safety

**Hard deny (no override):**
- `rm`, `rmdir`, `unlink` — file deletion
- `sudo`, `su`, `doas` — privilege escalation
- `shutdown`, `reboot`, `halt` — system control
- `mkfs`, `fdisk`, `dd` — disk ops
- `git push --force`, `git clean` — destructive git
- `curl|wget` piped to `sh|bash` — remote code exec

**Path restrictions:**
- `read_file`/`write_file`: resolve inside project dir only
- `bash`: cwd forced to project dir
- Blocked: `~/.ssh`, `~/.aws`, `/etc`, `/private`

**Limits:**
- Timeout: 120s per command
- Output: 2000 lines or 100KB

Blocked commands return error to model (not crash). Model can adapt.

## Plugin & Skill System

**Plugin loading:**
1. Scan `--plugin-dir` for `.claude-plugin/plugin.json`
2. Read manifest (name, description)
3. Read `CLAUDE.md` → append to system prompt
4. Scan for `SKILL.md` and `commands/*.md`
5. Parse YAML frontmatter (name, description)
6. Build skill registry

**Skill invocation:**
- System prompt lists: "Available skills: [name — description]"
- Model calls `use_skill(skill_name="...")`
- Full skill markdown injected as system message
- Model follows instructions using built-in tools

Multiple `--plugin-dir` supported. Name collisions: last wins.

## Output Format

```
[cc] Using model: oci/openai.gpt-5.2
[cc] Loaded plugin: squire (12 skills)
[cc] Starting task...

[tool] bash: pytest --tb=short
[result] 3 failed, 12 passed (truncated)

[tool] read_file: tests/test_auth.py
[result] (142 lines)

[assistant] Fixed 3 failing tests...
```

## Project Structure

```
cc/
  __init__.py
  __main__.py
  cli.py              # Click CLI
  agent.py            # Tool loop
  llm.py              # LiteLLM wrapper + OCI auth
  safety.py           # Deny list + path checks
  config.py           # Config loading
  tools/
    __init__.py
    bash.py
    read_file.py
    write_file.py
    list_files.py
    grep.py
  plugins/
    __init__.py
    loader.py          # Plugin + skill loading
pyproject.toml
```

## Not in MVP

- Interactive/REPL mode
- Token-level streaming
- Conversation persistence
- MCP support
- Sandbox/Docker
- User approval prompts
- Multi-agent
- Token counting/budget
