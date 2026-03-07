import click


@click.group()
def main():
    """cc — lightweight multi-model coding agent."""
    pass


@main.command()
@click.argument("prompt")
def run(prompt):
    """Run a task and exit."""
    click.echo(f"[cc] Prompt: {prompt}")
