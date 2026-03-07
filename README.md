# lite-cc

A lightweight, multi-model coding agent CLI that runs tool loops safely and learns new tricks through plugins.

## Install

```bash
pip install -e .
```

Requires Python 3.11+.

## Usage

```bash
# Run a task
cc run "fix the failing tests"

# Use a specific model
cc run "refactor this module" --model anthropic/claude-3

# Load a plugin
cc run "triage the latest ticket" --plugin-dir ~/my-plugin

# Multiple plugins
cc run "check k8s health" --plugin-dir ~/plugin-a --plugin-dir ~/plugin-b

# Override project directory
cc run "list all files" --project-dir ~/other-repo

# Limit iterations
cc run "explore the codebase" --max-iterations 20
```

## Configuration

Config resolution (highest wins):

1. CLI flags
2. Environment variables
3. `~/.cc/config.yaml`
4. Defaults

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CC_MODEL` | `oci/openai.gpt-5.2` | LiteLLM model string |
| `CC_OCI_REGION` | `us-chicago-1` | OCI region |
| `CC_OCI_COMPARTMENT` | | OCI compartment OCID |
| `CC_OCI_CONFIG_PROFILE` | `DEFAULT` | OCI config profile |
| `CC_MAX_ITERATIONS` | `50` | Max tool loop iterations |
| `CC_TIMEOUT` | `120` | Command timeout (seconds) |

### YAML Config

```yaml
# ~/.cc/config.yaml
model: oci/openai.gpt-5.2
oci_region: us-chicago-1
oci_compartment: ocid1.tenancy.oc1..xxx
max_iterations: 50
timeout: 120
```

## Model Support

Any model supported by [LiteLLM](https://docs.litellm.ai/docs/providers):

```bash
cc run "hello" --model openai/gpt-4o
cc run "hello" --model anthropic/claude-3
cc run "hello" --model oci/openai.gpt-5.2
```

For OCI models, ensure your session token is configured at `~/.oci/config`.

## Built-in Tools

| Tool | Description |
|------|-------------|
| `bash` | Run shell commands (with safety checks) |
| `read_file` | Read file contents |
| `write_file` | Write/create files |
| `list_files` | Glob pattern file search |
| `grep` | Search file contents |
| `use_skill` | Load a plugin skill on demand |

## Plugins

Plugins follow the Claude plugin format:

```
my-plugin/
  .claude-plugin/
    plugin.json       # {"name": "...", "description": "...", "version": "..."}
  CLAUDE.md           # Instructions injected into system prompt
  pipeline/
    my-skill/
      SKILL.md        # Skill with YAML frontmatter
  commands/
    deploy.md         # Command skill
```

Skills use YAML frontmatter:

```markdown
---
name: my-skill
description: When to trigger this skill
---
# Instructions
Do the thing using bash and read_file tools.
```

Skills are loaded on demand when the model calls `use_skill`.

## Safety

Commands are blocked in full-auto mode (no prompts, just denied):

- File deletion: `rm`, `rmdir`, `unlink`
- Privilege escalation: `sudo`, `su`
- System control: `shutdown`, `reboot`
- Disk ops: `mkfs`, `fdisk`, `dd`
- Destructive git: `git push --force`, `git clean`
- Remote code exec: `curl ... | sh`

File access is restricted to the project directory. Sensitive paths (`~/.ssh`, `~/.aws`, `/etc`) are blocked.

## Development

```bash
# Install dev dependencies
pip install -e .

# Run tests
pytest -v
```
