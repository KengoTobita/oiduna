"""Sample command - sample management"""

import click
import asyncio
from oiduna_client import OidunaClient


@click.group()
def sample():
    """Sample management commands"""
    pass


@sample.command()
@click.argument('category')
@click.argument('path', type=click.Path(exists=True))
@click.pass_context
def load(ctx, category: str, path: str):
    """Load samples from a directory

    Example:
        oiduna sample load custom /path/to/samples/custom
    """
    formatter = ctx.obj['formatter']

    try:
        result = asyncio.run(_load_sample_async(
            ctx.obj['url'],
            ctx.obj['timeout'],
            category,
            path
        ))

        if result.loaded:
            formatter.success(f"Samples '{category}' loaded")
        else:
            formatter.error(f"Samples '{category}' failed to load", result.message)
            raise click.Abort()

    except Exception as e:
        formatter.error("Failed to load samples", str(e))
        raise click.Abort()


async def _load_sample_async(url: str, timeout: float, category: str, path: str):
    """Load samples asynchronously"""
    async with OidunaClient(base_url=url, timeout=timeout) as client:
        return await client.samples.load(category=category, path=path)


@sample.command('list')
@click.pass_context
def list_buffers(ctx):
    """List loaded sample buffers

    Example:
        oiduna sample list
        oiduna --json sample list
    """
    formatter = ctx.obj['formatter']

    try:
        result = asyncio.run(_list_buffers_async(
            ctx.obj['url'],
            ctx.obj['timeout']
        ))

        formatter.success("Loaded buffers", {
            "count": result.count,
            "buffers": ", ".join(result.buffers) if result.buffers else "none"
        })

    except Exception as e:
        formatter.error("Failed to list buffers", str(e))
        raise click.Abort()


async def _list_buffers_async(url: str, timeout: float):
    """List buffers asynchronously"""
    async with OidunaClient(base_url=url, timeout=timeout) as client:
        return await client.samples.list_buffers()
