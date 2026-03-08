# lite-cc — MVP Plan

## Goal

A working `litecc run "do something"` that:
1. Connects to OCI-hosted OpenAI models via LiteLLM
2. Runs an automatic tool loop (LLM calls tools, we execute, repeat)
3. Has built-in tools: bash, read_file, write_file, list_files, grep
4. Loads Claude-style plugins and skills from a directory
5. Blocks dangerous commands (rm, sudo, etc.) — no user prompts, just deny
6. Runs fully autonomously until task is done or max iterations hit

## Language

**Python 3.11+**

Why:
- LiteLLM is Python
- Existing OCI auth code is Python
- Plugin scripts are Python
- Fast to iterate, easy to read
- No compilation step

## Dependencies (minimal)

```
litellm          # Multi-model LLM client
oci              # OCI SDK (auth)
click            # CLI framework (lightweight)
pyyaml           # Parse skill frontmatter
```

No FastAPI/uvicorn — we're a CLI, not a server.

## Project Structure

```
lite-cc/
  cc/
    __init__.py
    __main__.py          # `python -m cc` entry point
    cli.py               # Click CLI: `litecc run "prompt"`
    agent.py             # The tool loop
    llm.py               # LiteLLM wrapper + OCI auth
    safety.py            # Command deny list + path checks
    config.py            # Config loading
    tools/
      __init__.py
      bash.py
      read_file.py
      write_file.py
      list_files.py
      grep.py
    plugins/
      __init__.py
      loader.py          # Load plugin dirs, register tools, load skills
  pyproject.toml
  docs/
    MVP.md
    VISION.md
```

## MVP Scope — What to Build

### 1. CLI (`cli.py`)

```bash
litecc run "fix the failing tests"
litecc run "fix the failing tests" --plugin-dir ~/my-plugin
litecc run "fix the failing tests" --model oci/openai.gpt-5.2
```

Options:
- `prompt` (required) — what to do
- `--plugin-dir` — path to plugin directory (can specify multiple)
- `--model` — LiteLLM model string (default from config or env)
- `--max-iterations` — tool loop limit (default: 50)
- `--project-dir` — working directory (default: cwd)

### 2. LLM Client (`llm.py`)

Wraps `litellm.completion()` with:
- Tool definitions passed as `tools=` parameter
- OCI auth (signer, region, compartment) from env/config
- Returns normalized response: `{text, tool_calls, stop_reason}`

Config via env vars:
```
CC_MODEL=oci/openai.gpt-5.2
CC_OCI_REGION=us-chicago-1
CC_OCI_COMPARTMENT=ocid1.tenancy...
CC_OCI_CONFIG_PROFILE=DEFAULT
```

Apply the OCIChatConfig patch from codex-oci proxy for max_completion_tokens.

### 3. Agent Loop (`agent.py`)

```python
def run(prompt, tools, llm, safety, max_iterations=50):
    messages = [system_prompt, user_prompt]
    for i in range(max_iterations):
        response = llm.chat(messages, tools)
        messages.append(response.message)

        if not response.tool_calls:
            break  # Done — final answer

        for call in response.tool_calls:
            result = execute_tool(call, safety)
            messages.append(tool_result(call.id, result))

    return messages[-1].content
```

That's it. Simple loop. No async needed for MVP.

### 4. Built-in Tools

Each tool is a dict (OpenAI function calling format) + an execute function.

| Tool | What it does |
|------|-------------|
| `bash` | Run shell command with safety checks, timeout, output limits |
| `read_file` | Read file contents (with line range support) |
| `write_file` | Write content to a file (project dir only) |
| `list_files` | Glob pattern matching for files |
| `grep` | Search file contents with pattern |

Tool schema example:
```python
BASH_TOOL = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": "Run a shell command",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The command to run"}
            },
            "required": ["command"]
        }
    }
}
```

### 5. Safety (`safety.py`)

**Hard deny list** (blocked always, no override in MVP):
```
rm, rmdir, unlink          # file deletion
sudo, su, doas             # privilege escalation
shutdown, reboot, halt     # system control
mkfs, fdisk, dd            # disk operations
chmod, chown (recursive)   # permission changes on /
kill, killall, pkill       # process killing
curl|wget + pipe to sh     # remote code execution
git push --force           # destructive git
> /dev/sda, > /dev/null    # device writes
```

**Path restrictions**:
- `read_file`, `write_file`: must resolve inside project directory
- `bash`: cwd set to project directory
- No access to `~/.ssh`, `~/.aws`, `/etc`, `/private`

**Output limits**:
- Max 2000 lines or 100KB per command output
- Timeout: 120 seconds default

Implementation: regex/substring matching on command string. Simple and effective.

### 6. Plugin & Skill Loading (`plugins/loader.py`)

On startup:
1. Scan `--plugin-dir` for `.claude-plugin/plugin.json`
2. Read `CLAUDE.md` from plugin root → append to system prompt
3. Scan for `SKILL.md` and `commands/*.md` files
4. Parse YAML frontmatter (name, description) from each skill
5. Make skills available as: skill name + description list in system prompt
6. When model references a skill, inject the full skill markdown into context

Skills are **prompt content**, not tools. They guide the model's behavior.
The model sees: "Available skills: [list]" and can request to use one.

We can also implement skills as a tool:
```python
USE_SKILL_TOOL = {
    "type": "function",
    "function": {
        "name": "use_skill",
        "description": "Load and follow a skill's instructions",
        "parameters": {
            "type": "object",
            "properties": {
                "skill_name": {"type": "string"}
            },
            "required": ["skill_name"]
        }
    }
}
```

When called, inject the skill's markdown content as a system message.

### 7. System Prompt

```
You are cc, a coding agent. You help with software engineering tasks.

You have these tools: bash, read_file, write_file, list_files, grep, use_skill

## Safety
- You cannot delete files or run destructive commands
- You can only access files in the project directory: {project_dir}

## Plugins
{plugin_claude_md_content}

## Available Skills
{skill_list_with_descriptions}

## Task
Complete the user's request. Use tools as needed. Be concise.
```

### 8. Config (`config.py`)

Load from (in priority order):
1. CLI flags
2. Environment variables (`CC_MODEL`, `CC_OCI_REGION`, etc.)
3. `~/.cc/config.yaml` (if exists)
4. Defaults

## What's NOT in MVP

- Interactive/REPL mode
- Streaming output to terminal (just print final result + tool outputs)
- Conversation persistence
- MCP support
- Sandbox/Docker
- User approval prompts
- Multiple concurrent agents
- Token counting/budget

## Concerns & Mitigations

| Concern | Mitigation |
|---------|-----------|
| LiteLLM tool calling may not work perfectly with OCI models | Test early; fall back to prompt-based tool calling if needed |
| Safety regex can be bypassed (e.g., `r m -rf`) | Good enough for MVP; not a security boundary, just a guardrail |
| Skills are large markdown — may consume context | Only inject when explicitly requested via use_skill tool |
| OCI session tokens expire | Reuse oci_auth.py pattern; fail with clear error |
| Max iterations hit before task done | Default 50 is generous; make configurable |

## Success Criteria

MVP is done when:
```bash
litecc run "list all Python files in this directory" --plugin-dir ~/workspace/squire-cli/src/squire/plugin
```
...correctly loads the plugin, uses list_files + grep tools, and returns the answer.

And:
```bash
litecc run "check k8s health for namespace X in region Y" --plugin-dir ~/workspace/squire-cli/src/squire/plugin
```
...loads the k8s-runtime-health skill and follows its instructions using bash.

## Build Order

1. `config.py` + `cli.py` — get `litecc run "hello"` working
2. `llm.py` — connect to OCI model, get a text response
3. `tools/` — implement 5 built-in tools
4. `agent.py` — wire up the tool loop
5. `safety.py` — add command filtering
6. `plugins/loader.py` — load plugins and skills
7. Test end-to-end with squire plugin
