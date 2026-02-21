"""SynthDef command - SynthDef management"""

import click
import asyncio
from oiduna_client import OidunaClient


@click.group()
def synthdef():
    """SynthDef management commands"""
    pass


@synthdef.command()
@click.argument('file', type=click.Path(exists=True))
@click.option('--name', help='SynthDef name (default: filename)')
@click.pass_context
def load(ctx, file: str, name: str = None):
    """Load a SynthDef from file

    Example:
        oiduna synthdef load acid.scd
        oiduna synthdef load custom.scd --name mysynth
    """
    formatter = ctx.obj['formatter']

    try:
        result = asyncio.run(_load_synthdef_async(
            ctx.obj['url'],
            ctx.obj['timeout'],
            file,
            name
        ))

        if result.loaded:
            formatter.success(f"SynthDef '{result.name}' loaded")
        else:
            formatter.error(f"SynthDef '{result.name}' failed to load", result.message)
            raise click.Abort()

    except Exception as e:
        formatter.error("Failed to load SynthDef", str(e))
        raise click.Abort()


async def _load_synthdef_async(url: str, timeout: float, file: str, name: str = None):
    """Load SynthDef asynchronously"""
    async with OidunaClient(base_url=url, timeout=timeout) as client:
        return await client.synthdef.load_from_file(file, name=name)
