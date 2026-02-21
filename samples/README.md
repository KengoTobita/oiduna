# Oiduna Sample Files

Sample patterns and SynthDefs for testing Oiduna.

## Pattern Files

Located in `patterns/`:

### basic_kick.json
Simple kick drum pattern using Euclidean rhythm (4 hits in 16 steps).

```bash
oiduna play submit samples/patterns/basic_kick.json
```

### basic_hihat.json
Simple hi-hat pattern using Euclidean rhythm (8 hits in 16 steps).

```bash
oiduna play submit samples/patterns/basic_hihat.json
```

### simple_beat.json
Basic drum pattern with kick, snare, and hi-hat.

```bash
oiduna play submit samples/patterns/simple_beat.json
```

### complex_pattern.json
Multi-track pattern with polyrhythmic elements (kick: 5/16, snare: 3/16, etc.).

```bash
oiduna play submit samples/patterns/complex_pattern.json
```

## SynthDef Files

Located in `synthdefs/`:

### acid.scd
TB-303 style acid bass with resonant filter.

```bash
oiduna synthdef load samples/synthdefs/acid.scd
```

### pad.scd
Warm pad sound with multiple detuned oscillators.

```bash
oiduna synthdef load samples/synthdefs/pad.scd
```

### kick.scd
Synthesized kick drum with pitch envelope.

```bash
oiduna synthdef load samples/synthdefs/kick.scd
```

## Usage Example

```bash
# 1. Start Oiduna API
cd oiduna && python -m oiduna_api.main

# 2. Load SynthDefs
oiduna synthdef load samples/synthdefs/kick.scd
oiduna synthdef load samples/synthdefs/acid.scd

# 3. Play a pattern
oiduna play submit samples/patterns/simple_beat.json

# 4. Stop playback
oiduna play stop
```

## Pattern Format

All patterns use Oiduna IR format:

```json
{
  "version": "1.0",
  "type": "pattern",
  "metadata": {
    "name": "Pattern Name",
    "description": "Description",
    "bpm": 120
  },
  "tracks": [
    {
      "track_id": "unique_id",
      "instrument": "synthdef_name",
      "pattern": {
        "type": "euclidean",
        "steps": 16,
        "hits": 4,
        "rotation": 0
      },
      "params": {
        "gain": 1.0
      }
    }
  ]
}
```

## License

MIT
