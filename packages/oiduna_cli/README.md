# oiduna_cli

Command-line interface for Oiduna API.

## Installation

```bash
pip install -e packages/oiduna_cli
```

This will install the `oiduna` command.

## Quick Start

```bash
# Check status
oiduna status

# Play a pattern
oiduna play submit pattern.json

# Load a SynthDef
oiduna synthdef load acid.scd

# Load samples
oiduna sample load custom /path/to/samples/custom
```

## Commands

### Global Options

```bash
--url TEXT          # Oiduna API URL (default: http://localhost:57122)
--timeout FLOAT     # Request timeout in seconds (default: 30.0)
--json              # Output as JSON
--verbose           # Verbose output
```

### status

Check Oiduna system status.

```bash
oiduna status
oiduna --json status
```

### play submit

Execute a pattern file.

```bash
oiduna play submit <pattern-file>

# Example
oiduna play submit pattern.json
oiduna --json play submit pattern.json
```

### play validate

Validate a pattern file without executing.

```bash
oiduna play validate <pattern-file>

# Example
oiduna play validate pattern.json
```

### play stop

Stop pattern playback.

```bash
oiduna play stop [track-id]

# Examples
oiduna play stop           # Stop all
oiduna play stop track-1   # Stop specific track
```

### synthdef load

Load a SynthDef from file.

```bash
oiduna synthdef load <file> [--name NAME]

# Examples
oiduna synthdef load acid.scd
oiduna synthdef load custom.scd --name mysynth
```

### sample load

Load samples from a directory.

```bash
oiduna sample load <category> <path>

# Example
oiduna sample load custom /path/to/samples/custom
```

### sample list

List loaded sample buffers.

```bash
oiduna sample list
oiduna --json sample list
```

## JSON Output Mode

The `--json` flag enables machine-readable JSON output:

```bash
oiduna --json status
```

Output format:

```json
{
  "status": "success",
  "message": "Oiduna status",
  "data": {
    "status": "ok",
    "superdirt": "connected",
    "midi": "connected"
  }
}
```

Error format:

```json
{
  "status": "error",
  "message": "Failed to get status",
  "details": "Connection refused"
}
```

## Exit Codes

- **0** - Success
- **1** - General error

## Examples

### Basic Workflow

```bash
# 1. Check if Oiduna is running
oiduna status

# 2. Load a SynthDef
oiduna synthdef load samples/synthdefs/acid.scd

# 3. Play a pattern
oiduna play submit samples/patterns/basic_kick.json

# 4. Stop playback
oiduna play stop
```

### Automation (from Claude Code)

```python
import subprocess
import json

# Execute pattern with JSON output
result = subprocess.run(
    ["oiduna", "--json", "play", "submit", "pattern.json"],
    capture_output=True,
    text=True
)

if result.returncode == 0:
    data = json.loads(result.stdout)
    print(f"Success: {data['message']}")
else:
    error = json.loads(result.stderr)
    print(f"Error: {error['message']}")
```

## License

MIT
