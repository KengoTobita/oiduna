# oiduna_client

Python client library for Oiduna API.

## Installation

```bash
pip install -e packages/oiduna_client
```

## Quick Start

```python
import asyncio
from oiduna_client import OidunaClient

async def main():
    async with OidunaClient() as client:
        # Check health
        health = await client.health.check()
        print(f"Status: {health.status}")

        # Submit a pattern
        pattern = {
            "version": "1.0",
            "type": "pattern",
            "tracks": [...]
        }
        result = await client.patterns.submit(pattern)
        print(f"Playing: {result.track_id}")

asyncio.run(main())
```

## API Reference

### OidunaClient

Main client class providing access to all API endpoints.

```python
client = OidunaClient(
    base_url="http://localhost:57122",
    timeout=30.0
)
```

### Health Client

```python
# Check system health
health = await client.health.check()

# Wait for system to be ready
health = await client.health.wait_ready(timeout=60.0)
```

### Pattern Client

```python
# Submit a pattern
result = await client.patterns.submit(pattern)

# Validate a pattern without executing
validation = await client.patterns.validate(pattern)

# Get active patterns
active = await client.patterns.get_active()

# Stop patterns
await client.patterns.stop()  # Stop all
await client.patterns.stop(track_id="...")  # Stop specific
```

### SynthDef Client

```python
# Load a SynthDef from code
code = 'SynthDef(\\acid, { |out=0| Out.ar(out, SinOsc.ar(440)) }).add;'
result = await client.synthdef.load("acid", code)

# Load a SynthDef from file
result = await client.synthdef.load_from_file("acid.scd")
```

### Sample Client

```python
# Load samples from directory
result = await client.samples.load(
    category="custom",
    path="/path/to/samples/custom"
)

# List loaded buffers
buffers = await client.samples.list_buffers()
```

## Exception Handling

```python
from oiduna_client import OidunaAPIError, ValidationError, TimeoutError

try:
    result = await client.patterns.submit(pattern)
except ValidationError as e:
    print(f"Invalid pattern: {e}")
except TimeoutError as e:
    print(f"Request timed out: {e}")
except OidunaAPIError as e:
    print(f"API error: {e}")
```

## Type Safety

All request and response models are defined using Pydantic for type safety:

```python
from oiduna_client.models import (
    PatternSubmitRequest,
    PatternSubmitResponse,
    HealthResponse,
)
```

## Testing

```bash
pytest tests/
```

## License

MIT
