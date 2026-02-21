"""Main CLI entry point"""

import click
from rich.console import Console
from oiduna_cli.utils.output import OutputFormatter
from oiduna_cli.commands.status import status
from oiduna_cli.commands.play import play
from oiduna_cli.commands.synthdef import synthdef
from oiduna_cli.commands.sample import sample


@click.group()
@click.option('--url', default='http://localhost:57122', help='Oiduna API URL')
@click.option('--timeout', default=30.0, help='Request timeout in seconds')
@click.option('--json', 'json_mode', is_flag=True, help='Output as JSON')
@click.option('--verbose', is_flag=True, help='Verbose output')
@click.pass_context
def cli(ctx, url: str, timeout: float, json_mode: bool, verbose: bool):
    """Oiduna CLI - Command-line interface for Oiduna API

    Examples:
        oiduna status
        oiduna play submit pattern.json
        oiduna synthdef load acid.scd
        oiduna --json status
    """
    # Initialize context
    ctx.ensure_object(dict)
    ctx.obj['url'] = url
    ctx.obj['timeout'] = timeout
    ctx.obj['verbose'] = verbose

    # Initialize output formatter
    console = Console()
    ctx.obj['console'] = console
    ctx.obj['formatter'] = OutputFormatter(json_mode=json_mode, console=console)


# Register commands
cli.add_command(status)
cli.add_command(play)
cli.add_command(synthdef)
cli.add_command(sample)


if __name__ == '__main__':
    cli()
