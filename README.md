<p align="center">
  <h1 align="center">lite-cc</h1>
  <p align="center">
    A minimal, multi-model coding agent runtime for the terminal.
  </p>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> &middot;
  <a href="#how-it-works">How It Works</a> &middot;
  <a href="#configuration">Configuration</a> &middot;
  <a href="#plugins--skills">Plugins & Skills</a> &middot;
  <a href="#safety">Safety</a>
</p>

---

**lite-cc** (`litecc`) is a lightweight CLI that connects to any LLM provider, runs an autonomous tool loop to complete coding tasks, and extends its capabilities through a plugin and skill system. It is designed to be safe by default, provider-agnostic, and easy to extend.

## Key Features

- **Multi-model** — Works with any provider supported by [LiteLLM](https://docs.litellm.ai/docs/providers): OpenAI, Anthropic, OCI, Gemini, Groq, Together, local models, and more.
- **Autonomous tool loop** — The model reasons, calls tools, observes results, and iterates until the task is done.
- **Plugin system** — Load Claude-compatible plugins to inject domain knowledge and custom workflows.
- **Skills on demand** — Skills are reusable playbooks that the model loads when needed, keeping context lean.
- **Safe by default** — Dangerous commands are blocked. File access is restricted to the project directory. No user prompts needed.
- **Clean output** — Structured progress logging shows what the agent is doing at each step.

## Quick Start

### Prerequisites

- Python 3.11+
- An API key or session token for your chosen LLM provider

### Installation

```bash
git clone https://github.com/your-org/lite-cc.git
cd lite-cc
pip install -e .
```

### First Run

```bash
litecc run "list all Python files in this directory and describe what each one does"
```

You should see structured output like:

```
14:32:05 [cc] Using model: oci/openai.gpt-5.2
14:32:05 [cc] Starting task...
14:32:06 [tool] list_files: **/*.py
14:32:07 [tool] read_file: cc/agent.py
14:32:08 [gpt-5.2] I'll describe each file...
14:32:09 [cc] Here are the Python files...
```

## How It Works

```
litecc run "fix the failing tests"
        |
        v
  Load config, plugins, skills
        |
        v
  Build system prompt + tool definitions
        |
        v
  Agent Loop:
    1. Send messages + tools to LLM
    2. LLM returns tool calls → execute safely → append results
    3. LLM returns text → print and exit
```

The loop runs until the model produces a final answer or the maximum iteration count is reached.

## Usage

### Run Mode (autonomous)

```bash
# Basic task
litecc run "fix the failing tests"

# Specify a model
litecc run "refactor this module" --model anthropic/claude-3-sonnet-20240229

# Load one or more plugins
litecc run "triage the latest ticket" --plugin-dir ~/my-plugin
litecc run "check k8s health" --plugin-dir ~/plugin-a --plugin-dir ~/plugin-b

# Target a different project directory
litecc run "explain the architecture" --project-dir ~/other-repo

# Limit the tool loop
litecc run "explore the codebase" --max-iterations 20
```

### CLI Reference

```
Usage: litecc run [OPTIONS] PROMPT

Options:
  --plugin-dir TEXT      Plugin directory (repeatable)
  --model TEXT           LiteLLM model string
  --max-iterations INT   Max tool loop iterations (default: 50)
  --project-dir TEXT     Working directory (default: cwd)
  --help                 Show this message and exit
```

## Configuration

Configuration is resolved in order of precedence (highest wins):

| Priority | Source | Example |
|----------|--------|---------|
| 1 (highest) | CLI flags | `--model openai/gpt-4o` |
| 2 | Environment variables | `CC_MODEL=openai/gpt-4o` |
| 3 | YAML config file | `~/.cc/config.yaml` |
| 4 (lowest) | Built-in defaults | `oci/openai.gpt-5.2` |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CC_MODEL` | `oci/openai.gpt-5.2` | LiteLLM model identifier |
| `CC_OCI_REGION` | `us-chicago-1` | OCI region for model inference |
| `CC_OCI_COMPARTMENT` | — | OCI compartment OCID (required for OCI models) |
| `CC_OCI_CONFIG_PROFILE` | `DEFAULT` | Profile name in `~/.oci/config` |
| `CC_MAX_ITERATIONS` | `50` | Maximum agent loop iterations |
| `CC_TIMEOUT` | `120` | Per-command timeout in seconds |

### YAML Configuration

Create `~/.cc/config.yaml` for persistent settings:

```yaml
model: oci/openai.gpt-5.2
oci_region: us-chicago-1
oci_compartment: ocid1.tenancy.oc1..aaaaaaaexample
max_iterations: 50
timeout: 120
```

## Model Support

lite-cc uses [LiteLLM](https://docs.litellm.ai/docs/providers) for model routing. Any provider LiteLLM supports works out of the box:

| Provider | Model Example | Auth |
|----------|--------------|------|
| OpenAI | `openai/gpt-4o` | `OPENAI_API_KEY` env var |
| Anthropic | `anthropic/claude-3-sonnet-20240229` | `ANTHROPIC_API_KEY` env var |
| OCI GenAI | `oci/openai.gpt-5.2` | `~/.oci/config` session token |
| Gemini | `gemini/gemini-pro` | `GEMINI_API_KEY` env var |
| Groq | `groq/llama3-70b-8192` | `GROQ_API_KEY` env var |
| Local (Ollama) | `ollama/llama3` | Local server at `localhost:11434` |

### OCI Setup

For OCI-hosted models, ensure you have a valid session token:

```bash
oci session authenticate --profile-name DEFAULT --region us-chicago-1
oci session validate --profile DEFAULT
```

## Built-in Tools

The agent has access to these tools during task execution:

| Tool | Description | Safety |
|------|-------------|--------|
| `bash` | Execute shell commands in the project directory | Commands checked against deny list; output truncated at 2000 lines / 100KB; configurable timeout |
| `read_file` | Read file contents with optional line range (`offset`, `limit`) | Path must resolve inside project directory |
| `write_file` | Create or overwrite files, auto-creates parent directories | Path must resolve inside project directory |
| `list_files` | Find files by glob pattern (e.g., `**/*.py`) | Scoped to project directory; max 500 results |
| `grep` | Search file contents recursively with regex | Scoped to project directory; max 200 matches |
| `use_skill` | Load a skill's instructions into the conversation | Skill must be registered from a loaded plugin |

## Plugins & Skills

lite-cc supports a plugin system compatible with the Claude Code plugin format. Plugins provide domain knowledge and reusable workflows to the agent.

### Plugin Structure

```
my-plugin/
  .claude-plugin/
    plugin.json            # Plugin manifest (required)
  CLAUDE.md                # Plugin-wide instructions (injected into system prompt)
  pipeline/                # Skills organized by topic
    deploy-check/
      SKILL.md             # Skill definition
    health-check/
      SKILL.md
  commands/                # Command-style skills
    triage.md
    rollback.md
```

### Plugin Manifest

`.claude-plugin/plugin.json`:

```json
{
  "name": "my-plugin",
  "description": "Production operations toolkit",
  "version": "1.0.0"
}
```

### Skill Format

Skills are Markdown files with YAML frontmatter. The `name` and `description` fields help the model decide when to load the skill.

```markdown
---
name: deploy-check
description: Verify a deployment is healthy by checking pod status, logs, and metrics.
---

# Deploy Check

## Input
The user provides a region and namespace.

## Steps

1. Check pod status:
   ```bash
   kubectl get pods -n <NAMESPACE> -o wide
   ```

2. Review recent events:
   ```bash
   kubectl get events -n <NAMESPACE> --sort-by='.lastTimestamp' | tail -20
   ```

3. Summarize findings.
```

### How Skills Work

1. On startup, lite-cc scans `--plugin-dir` directories for `.claude-plugin/plugin.json`
2. `CLAUDE.md` content is injected into the system prompt
3. All `SKILL.md` and `commands/*.md` files are indexed by name and description
4. The model sees a list of available skills in its system prompt
5. When relevant, the model calls `use_skill("deploy-check")` to load the full instructions
6. The skill's Markdown content is injected into the conversation as guidance
7. The model follows the skill's steps using the built-in tools

This on-demand loading keeps context lean — only the skills needed for the current task are loaded.

## Safety

lite-cc enforces safety guardrails at the tool execution layer. In run mode (full autonomy), dangerous operations are denied without prompting.

### Command Deny List

The following command patterns are blocked:

| Category | Blocked Patterns |
|----------|-----------------|
| File deletion | `rm`, `rmdir`, `unlink` |
| Privilege escalation | `sudo`, `su`, `doas` |
| System control | `shutdown`, `reboot`, `halt` |
| Disk operations | `mkfs`, `fdisk`, `dd` |
| Process control | `kill`, `killall`, `pkill` |
| Destructive git | `git push --force`, `git clean` |
| Remote code execution | `curl ... \| sh`, `wget ... \| bash` |
| Device writes | `> /dev/sd*` |

When a command is blocked, the agent receives an error message explaining why. It can then adapt its approach.

### Path Restrictions

- `read_file` and `write_file` only operate on files inside the project directory
- `bash` commands execute with `cwd` set to the project directory
- Path traversal attempts (e.g., `../../etc/passwd`) are resolved and blocked
- Sensitive directories are always blocked: `~/.ssh`, `~/.aws`, `/etc`, `/private`

### Output Limits

- Command output is truncated at **2000 lines** or **100KB** (whichever comes first)
- Command timeout defaults to **120 seconds** (configurable via `CC_TIMEOUT`)

### Design Philosophy

The safety layer is a guardrail, not a security boundary. It prevents the most common destructive operations in an autonomous agent loop. It does not attempt to sandbox arbitrary code execution.

## Architecture

```
cc/
  cli.py              # Click CLI entry point
  config.py           # Layered configuration (CLI > env > yaml > defaults)
  agent.py            # Core tool loop with progress logging
  llm.py              # LiteLLM wrapper with OCI auth support
  safety.py           # Command deny list + path restrictions
  tools/
    bash.py            # Shell execution with safety checks
    read_file.py       # File reading with line ranges
    write_file.py      # File writing with path validation
    list_files.py      # Glob-based file search
    grep.py            # Recursive content search
  plugins/
    loader.py          # Plugin discovery + skill indexing
```

## Development

```bash
# Install in development mode
pip install -e .

# Run the test suite
pytest -v

# Run a specific test file
pytest tests/test_safety.py -v
```

### Test Coverage

| Module | Tests | What's Covered |
|--------|-------|----------------|
| `config` | 3 | Defaults, env override, CLI override precedence |
| `safety` | 9 | Command blocking, path validation, traversal attacks, sensitive paths |
| `tools` | 9 | All 6 tools: execution, safety enforcement, edge cases |
| `llm` | 3 | Response parsing, tool call decoding, OCI signer injection |
| `plugins` | 4 | Manifest loading, skill discovery, command parsing, missing manifests |
| `agent` | 3 | No-tool response, tool loop, max iteration enforcement |
| `cli` | 1 | End-to-end CLI invocation |

## License

MIT
