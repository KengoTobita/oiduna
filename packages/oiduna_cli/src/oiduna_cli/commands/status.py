"""Status command - health check"""

import click
import asyncio
from oiduna_client import OidunaClient


@click.command()
@click.pass_context
def status(ctx):
    """Check Oiduna system status

    Example:
        oiduna status
        oiduna --json status
    """
    formatter = ctx.obj['formatter']

    try:
        result = asyncio.run(_status_async(
            ctx.obj['url'],
            ctx.obj['timeout']
        ))

        formatter.success("Oiduna status", {
            "status": result.status,
            "superdirt": "connected" if result.superdirt else "disconnected",
            "midi": "connected" if result.midi else "disconnected",
        })

    except Exception as e:
        formatter.error("Failed to get status", str(e))
        raise click.Abort()


async def _status_async(url: str, timeout: float):
    """Get status asynchronously"""
    async with OidunaClient(base_url=url, timeout=timeout) as client:
        return await client.health.check()
