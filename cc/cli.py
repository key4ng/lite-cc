"""CLI entry point for cc."""

import click
from cc.config import load_config
from cc.llm import LLMClient
from cc.agent import run_agent
from cc.plugins.loader import load_plugins


@click.group()
def main():
    """litecc — lightweight multi-model coding agent."""
    pass


@main.command()
@click.argument("prompt")
@click.option("--plugin-dir", multiple=True, help="Plugin directory (can specify multiple)")
@click.option("--model", default=None, help="LiteLLM model string")
@click.option("--max-iterations", default=None, type=int, help="Max tool loop iterations")
@click.option("--project-dir", default=None, help="Project directory (default: cwd)")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Show detailed tool output")
def run(prompt, plugin_dir, model, max_iterations, project_dir, verbose):
    """Run a task and exit."""
    config = load_config(
        model=model,
        max_iterations=max_iterations,
        project_dir=project_dir,
        plugin_dirs=list(plugin_dir) if plugin_dir else [],
        verbose=verbose,
    )

    plugins = load_plugins(config.plugin_dirs)
    if config.plugin_dirs and not plugins:
        click.echo(
            f"Warning: --plugin-dir specified but no plugins found. "
            f"Checked: {', '.join(config.plugin_dirs)}",
            err=True,
        )
    llm = LLMClient(config)

    run_agent(
        prompt=prompt,
        config=config,
        llm=llm,
        plugins=plugins,
    )
