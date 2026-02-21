"""Play command - pattern execution"""

import click
import asyncio
import json
from pathlib import Path
from oiduna_client import OidunaClient


@click.group()
def play():
    """Pattern playback commands"""
    pass


@play.command('submit')
@click.argument('pattern_file', type=click.Path(exists=True))
@click.pass_context
def play_submit(ctx, pattern_file: str):
    """Execute a pattern file

    Example:
        oiduna play submit pattern.json
    """
    formatter = ctx.obj['formatter']

    try:
        # Load pattern from file
        pattern = json.loads(Path(pattern_file).read_text())

        result = asyncio.run(_submit_pattern_async(
            ctx.obj['url'],
            ctx.obj['timeout'],
            pattern
        ))

        formatter.success(f"Pattern submitted: {result.track_id}", {
            "track_id": result.track_id,
            "message": result.message
        })

    except json.JSONDecodeError as e:
        formatter.error("Invalid JSON in pattern file", str(e))
        raise click.Abort()
    except Exception as e:
        formatter.error("Failed to submit pattern", str(e))
        raise click.Abort()


async def _submit_pattern_async(url: str, timeout: float, pattern: dict):
    """Submit pattern asynchronously"""
    async with OidunaClient(base_url=url, timeout=timeout) as client:
        return await client.patterns.submit(pattern)


@play.command('validate')
@click.argument('pattern_file', type=click.Path(exists=True))
@click.pass_context
def validate_pattern(ctx, pattern_file: str):
    """Validate a pattern file without executing

    Example:
        oiduna play validate pattern.json
    """
    formatter = ctx.obj['formatter']

    try:
        # Load pattern from file
        pattern = json.loads(Path(pattern_file).read_text())

        result = asyncio.run(_validate_pattern_async(
            ctx.obj['url'],
            ctx.obj['timeout'],
            pattern
        ))

        if result.valid:
            formatter.success("Pattern is valid")
        else:
            formatter.error("Pattern validation failed", "\n".join(result.errors or []))
            raise click.Abort()

    except json.JSONDecodeError as e:
        formatter.error("Invalid JSON in pattern file", str(e))
        raise click.Abort()
    except Exception as e:
        formatter.error("Failed to validate pattern", str(e))
        raise click.Abort()


async def _validate_pattern_async(url: str, timeout: float, pattern: dict):
    """Validate pattern asynchronously"""
    async with OidunaClient(base_url=url, timeout=timeout) as client:
        return await client.patterns.validate(pattern)


@play.command('stop')
@click.argument('track_id', required=False)
@click.pass_context
def stop_pattern(ctx, track_id: str = None):
    """Stop pattern playback

    Example:
        oiduna play stop           # Stop all
        oiduna play stop track-1   # Stop specific track
    """
    formatter = ctx.obj['formatter']

    try:
        asyncio.run(_stop_pattern_async(
            ctx.obj['url'],
            ctx.obj['timeout'],
            track_id
        ))

        if track_id:
            formatter.success(f"Stopped track: {track_id}")
        else:
            formatter.success("Stopped all patterns")

    except Exception as e:
        formatter.error("Failed to stop pattern", str(e))
        raise click.Abort()


async def _stop_pattern_async(url: str, timeout: float, track_id: str = None):
    """Stop pattern asynchronously"""
    async with OidunaClient(base_url=url, timeout=timeout) as client:
        return await client.patterns.stop(track_id=track_id)
