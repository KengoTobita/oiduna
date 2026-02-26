# Oiduna Glossary

Oidunaプロジェクトで使用される専門用語の定義集。

---

## Core Concepts

### Session
**Definition**: A complete set of scheduled messages representing one musical pattern, along with tempo and length metadata.

**Japanese**: セッション

**Structure**:
```json
{
  "messages": [
    {
      "destination_id": "superdirt",
      "cycle": 0.0,
      "step": 0,
      "params": {"s": "bd", "gain": 0.8}
    },
    ...
  ],
  "bpm": 120.0,
  "pattern_length": 4.0
}
```

**Lifecycle**:
1. Created by distribution (e.g., MARS)
2. Loaded via `POST /playback/session`
3. Optionally transformed by extensions (API layer)
4. Registered in MessageScheduler
5. Loops infinitely until replaced by new session

**Analogy**: Think of a session as a "musical score" for live coding.

**Related**: Message, ScheduledMessageBatch, Session Load, Pattern Length

---

### Message / ScheduledMessage
**Definition**: A single sound event within a session, scheduled at a specific timing position.

**Japanese**: メッセージ / スケジュールドメッセージ

**Structure**:
```python
@dataclass(frozen=True, slots=True)
class ScheduledMessage:
    destination_id: str  # Where to send (e.g., "superdirt", "midi_synth")
    cycle: float         # Position in cycles (e.g., 0.0, 0.5, 1.0)
    step: int            # Position in steps (0-255)
    params: dict         # Sound parameters (destination-specific)
```

**Example**:
```python
ScheduledMessage(
    destination_id="superdirt",
    cycle=0.0,
    step=0,
    params={"s": "bd", "gain": 0.8, "orbit": 0}
)
```

**Key Properties**:
- `destination_id`: Routes the message to the correct output
- `cycle` and `step`: Dual timing representation (see Cycle, Step)
- `params`: Generic dict (Oiduna is destination-agnostic)

**Related**: Session, Destination, Step, Cycle, Destination Router

---

### Pattern
**Definition**: The musical sequence represented by a session. Often used interchangeably with "session".

**Japanese**: パターン

**Usage**: "Load a new pattern" = "Load a new session"

**Related**: Session, Pattern Length

---

## Timing & Sequencing

### Step
**Definition**: The smallest timing unit in Oiduna, representing a 16th note subdivision.

**Japanese**: ステップ

**Range**: 0-255 (256 steps per loop maximum)

**Duration**: Depends on BPM
- BPM 120 → step duration ≈ 125ms
- BPM 140 → step duration ≈ 107ms

**Calculation**: `step_duration = 60.0 / bpm / 4`

**Relationship to Cycle**:
- 16 steps = 1 cycle (in 4/4 time)
- step 0 = cycle 0.0
- step 8 = cycle 0.5
- step 16 = cycle 1.0

**Usage in Code**:
```python
# MessageScheduler stores messages by step
messages_by_step = {
    0: [msg1, msg2],   # Messages at step 0
    16: [msg3],        # Messages at step 16
}

# Loop engine processes steps sequentially
current_step = self.state.position.step  # 0 → 1 → 2 → ... → 255 → 0
```

**Related**: Cycle, BPM, MessageScheduler, Step Loop

---

### Cycle
**Definition**: A musical measure or bar. Represents one complete iteration through the pattern at the cycle level.

**Japanese**: サイクル / 小節

**Format**: Floating-point number (e.g., 0.0, 0.5, 1.0, 1.25, 2.75)

**Relationship to Steps**:
- 1 cycle = 16 steps (in 4/4 time, 16th note resolution)
- cycle 0.0 = step 0 (downbeat)
- cycle 0.25 = step 4 (1st 16th after downbeat)
- cycle 0.5 = step 8 (halfway through bar)
- cycle 1.0 = step 16 (next bar)

**Conversion**:
```python
step = int(cycle * 16) % 256
cycle = step / 16.0
```

**Related**: Step, Pattern Length, Bar

---

### BPM (Beats Per Minute)
**Definition**: The tempo of the session.

**Japanese**: テンポ

**Range**: Typically 60-200 (though no hard limits in Oiduna)

**Impact**:
- Determines step duration
- Affects loop timing accuracy
- Used by extensions (e.g., SuperDirt's `cps` parameter)

**Example**:
- BPM 120 → 120 quarter notes per minute → 2 beats per second
- Step duration = 60 / 120 / 4 = 0.125s = 125ms

**Related**: Step, Cycle, CPS

---

### Pattern Length
**Definition**: The length of a session in cycles, after which it loops back to the beginning.

**Japanese**: パターン長

**Format**: Floating-point (e.g., 1.0, 2.0, 4.0, 8.0)

**Calculation**: Total steps = pattern_length × 16

**Examples**:
- pattern_length = 1.0 → 16 steps (1 bar)
- pattern_length = 4.0 → 64 steps (4 bars)
- pattern_length = 8.0 → 128 steps (8 bars)

**Looping Behavior**:
```
Step sequence with pattern_length = 4.0 (64 steps):
0 → 1 → 2 → ... → 63 → 0 → 1 → ... (infinite loop)
```

**Related**: Cycle, Step, Session

---

## Architecture Components

### Destination
**Definition**: An output target for messages (e.g., SuperDirt OSC server, MIDI device).

**Japanese**: デスティネーション / 送信先

**Configuration**: Defined in `destinations.yaml`

**Types**:
- `osc`: OSC server (e.g., SuperDirt, custom synths)
- `midi`: MIDI output device

**Example Configuration**:
```yaml
destinations:
  superdirt:
    id: superdirt
    type: osc
    host: 127.0.0.1
    port: 57120
    address: /dirt/play
    use_bundle: false

  midi_synth:
    id: midi_synth
    type: midi
    port_name: "USB MIDI 1"
    default_channel: 0
```

**Key Principle**: Oiduna is destination-agnostic. Messages are generic; each destination interprets `params` according to its own protocol.

**Related**: DestinationRouter, OscDestinationSender, MidiDestinationSender, Message

---

### Extension
**Definition**: A plugin that transforms session payloads at the API layer before they reach the loop engine.

**Japanese**: 拡張 / エクステンション

**Location**: API layer (`packages/oiduna_api/extensions/`)

**Scope**: Session transformation only (NOT runtime/loop processing)

**Purpose**:
- Add destination-specific logic (e.g., SuperDirt orbit assignment)
- Add distribution-specific logic (e.g., MARS MixerLine handling)
- Keep Oiduna core generic and agnostic

**Example Use Cases**:
- Orbit assignment for SuperDirt
- Parameter name conversion (snake_case → camelCase)
- MIDI channel routing
- Custom parameter injection

**Lifecycle**:
1. Loaded at API startup from `extensions.yaml`
2. Called on each `POST /playback/session` request
3. Transforms payload before passing to loop_engine

**Key Constraint**: Extensions do NOT have access to loop_engine internals or runtime state.

**Related**: SessionExtension, Pipeline, Session Load

---

### MessageScheduler
**Definition**: Component that stores and retrieves scheduled messages by step position.

**Japanese**: メッセージスケジューラ

**Location**: `packages/oiduna_scheduler/scheduler.py`

**Data Structure**:
```python
class MessageScheduler:
    def __init__(self):
        self._messages_by_step: dict[int, list[ScheduledMessage]] = {}
```

**Key Operations**:
```python
# Load a session
scheduler.load_messages(batch)  # Indexes messages by step

# Retrieve messages for current step
messages = scheduler.get_messages_at_step(42)
```

**Indexing Strategy**:
- Messages are grouped by `step` for O(1) lookup
- Empty steps have no entry (memory efficient)

**Related**: ScheduledMessage, Step, Session Load, Destination Router

---

### DestinationRouter
**Definition**: Component that groups messages by destination and sends them to the appropriate senders.

**Japanese**: デスティネーションルーター

**Location**: `packages/oiduna_scheduler/router.py`

**Process**:
1. Receive list of ScheduledMessage objects
2. Group by `destination_id`
3. Send each group to the registered sender

**Example**:
```python
router = DestinationRouter()
router.register_destination("superdirt", osc_sender)
router.register_destination("midi_synth", midi_sender)

# At runtime (called from loop_engine)
router.send_messages([msg1, msg2, msg3])
# → msg1, msg2 (destination_id="superdirt") sent via osc_sender
# → msg3 (destination_id="midi_synth") sent via midi_sender
```

**Related**: Destination, OscDestinationSender, MidiDestinationSender, Message

---

### Loop Engine
**Definition**: The core timing engine that processes steps, triggers messages, and manages playback state.

**Japanese**: ループエンジン

**Location**: `packages/oiduna_loop/engine/loop_engine.py`

**Responsibilities**:
- Step sequencing (16th note timing)
- MIDI clock generation
- Message retrieval and sending
- Playback state management (PLAYING/STOPPED/PAUSED)
- Drift correction

**Key Principle**: The loop engine is **completely agnostic** to:
- Destinations (doesn't know about SuperDirt, MIDI, etc.)
- Distributions (doesn't know about MARS, MixerLines, etc.)
- Extensions (doesn't know they exist)

**Main Loop** (`_step_loop`):
```python
while playing:
    current_step = self.state.position.step
    messages = self._message_scheduler.get_messages_at_step(current_step)
    self._destination_router.send_messages(messages)
    self.state.advance_step()
    await drift_corrected_sleep()
```

**Related**: MessageScheduler, DestinationRouter, Step, Playback State

---

## Data Formats

### ScheduledMessageBatch
**Definition**: The payload format for `POST /playback/session` (current API).

**Japanese**: スケジュールドメッセージバッチ

**Structure**:
```python
@dataclass
class ScheduledMessageBatch:
    messages: list[ScheduledMessage]
    bpm: float
    pattern_length: float
```

**JSON Format**:
```json
{
  "messages": [
    {
      "destination_id": "superdirt",
      "cycle": 0.0,
      "step": 0,
      "params": {"s": "bd", "gain": 0.8}
    }
  ],
  "bpm": 120.0,
  "pattern_length": 4.0
}
```

**Related**: Session, Message, Session Load

---

### CompiledSession
**Definition**: Legacy format used by `POST /playback/pattern` (old API).

**Japanese**: コンパイル済みセッション

**Status**: **Deprecated** - Being phased out in favor of ScheduledMessageBatch

**Structure** (for reference):
```json
{
  "environment": {"bpm": 120, "scale": "minor"},
  "tracks": [
    {
      "id": "bd",
      "sound": "bd",
      "orbit": 0,
      "sequence": [{"pitch": "0", "length": 1}]
    }
  ],
  "scenes": []
}
```

**Migration**: Use `POST /playback/session` with ScheduledMessageBatch instead.

**Related**: ScheduledMessageBatch, Legacy API

---

## Operations

### Session Load
**Definition**: The operation of registering a new session into Oiduna, replacing any existing session.

**Japanese**: セッションロード

**Endpoint**: `POST /playback/session`

**Complete Flow**:
```
1. MARS sends HTTP request
   POST /playback/session
   {messages: [...], bpm: 120, pattern_length: 4}

2. API layer receives request
   routes/playback.py: load_session()

3. Extensions transform payload
   SessionExtensionPipeline.transform(payload)

4. Pass to loop_engine
   engine._handle_session(transformed_payload)

5. Register in scheduler
   message_scheduler.load_messages(batch)

6. Session loaded (ready for playback)
```

**Behavior**:
- Replaces previous session completely
- Does NOT auto-start playback (call `POST /playback/start` separately)
- Old session is discarded

**Related**: Session, Extension, MessageScheduler

---

### Transform
**Definition**: The operation performed by extensions to modify a session payload.

**Japanese**: 変換

**Timing**: During session load, after API receives request, before loop_engine processes it

**Example**:
```python
class SuperDirtExtension(SessionExtension):
    def transform(self, payload: dict) -> dict:
        # Add orbit parameter
        # Convert parameter names
        # Filter messages
        return modified_payload
```

**Key Constraint**: Transformations happen at session load time, NOT at runtime.

**Related**: Extension, Session Load

---

## Distribution-Specific Concepts
(These are NOT part of Oiduna core, but handled by extensions)

### MixerLine (MARS Distribution)
**Definition**: A mixer channel in the MARS distribution, representing a track with associated effects and routing.

**Japanese**: ミキサーライン

**Purpose**: Group sounds with shared effects/routing in MARS

**Oiduna Integration**:
- MARS sends `mixer_line_id` parameter in messages
- SuperDirt extension maps `mixer_line_id` → `orbit`
- `mixer_line_id` is removed before sending to destination

**Example**:
```python
# MARS sends:
{"params": {"s": "bd", "mixer_line_id": "kick_track"}}

# SuperDirt extension transforms:
{"params": {"s": "bd", "orbit": 0}}  # mixer_line_id removed
```

**Note**: This is a MARS concept, not Oiduna core. Handled by extensions.

**Related**: Orbit, SuperDirt Extension

---

### Orbit (SuperDirt)
**Definition**: An effect chain in SuperDirt. Multiple sounds on the same orbit share effects (reverb, delay, etc.).

**Japanese**: オービット

**Range**: Typically 0-11 (12 orbits in default SuperDirt configuration)

**Assignment Strategies**:
- **Automatic**: SuperDirt extension assigns orbits based on `mixer_line_id`
- **Manual**: MARS explicitly sets `orbit` parameter
- **Default**: Fallback to orbit 0 if not specified

**Example**:
```python
# Messages with same orbit share effects
msg1 = {"orbit": 0, "s": "bd"}    # Kick on orbit 0
msg2 = {"orbit": 0, "s": "sn"}    # Snare on orbit 0 (shares effects)
msg3 = {"orbit": 1, "s": "hh"}    # Hi-hat on orbit 1 (separate effects)
```

**Note**: This is a SuperDirt-specific concept, not Oiduna core. Handled by SuperDirt extension.

**Related**: MixerLine, SuperDirt Extension, Destination

---

### CPS (Cycles Per Second) - SuperDirt
**Definition**: SuperDirt's tempo parameter, representing the number of cycles (bars) per second.

**Japanese**: サイクル毎秒

**Calculation**: `cps = bpm / 60.0 / 4.0`

**Example**:
- BPM 120 → cps = 120 / 60 / 4 = 0.5 (half a bar per second)
- BPM 140 → cps = 140 / 60 / 4 ≈ 0.583

**Oiduna Integration**:
- Oiduna uses BPM internally
- SuperDirt extension may add `cps` parameter to messages
- **Challenge**: BPM changes require recalculating cps (extension limitation)

**Note**: This is a SuperDirt-specific parameter.

**Related**: BPM, SuperDirt Extension

---

## Playback Control

### Playback State
**Definition**: The current state of the Oiduna playback engine.

**Japanese**: 再生状態

**States**:
- `STOPPED`: Not playing, position at 0
- `PLAYING`: Currently playing, advancing through steps
- `PAUSED`: Playback halted, position preserved

**State Transitions**:
```
STOPPED --[POST /playback/start]--> PLAYING
PLAYING --[POST /playback/pause]--> PAUSED
PAUSED  --[POST /playback/start]--> PLAYING (resume)
PLAYING --[POST /playback/stop]---> STOPPED (reset position)
```

**Related**: Playback Control Endpoints

---

### Playback Control Endpoints
**Definition**: HTTP endpoints for controlling playback.

**Japanese**: 再生制御エンドポイント

**Endpoints**:
- `POST /playback/start`: Start or resume playback
- `POST /playback/stop`: Stop and reset position to 0
- `POST /playback/pause`: Pause, keeping current position
- `GET /playback/status`: Get current playback state

**Behavior**:
- Session load does NOT auto-start playback
- Must explicitly call `/playback/start`

**Related**: Playback State, Session Load

---

## Internal Components

### Step Loop
**Definition**: The main timing loop in loop_engine that processes steps sequentially.

**Japanese**: ステップループ

**Location**: `loop_engine._step_loop()`

**Process**:
```python
while playing:
    # 1. Get messages for current step
    messages = scheduler.get_messages_at_step(current_step)

    # 2. Send to destinations
    router.send_messages(messages)

    # 3. Advance position
    state.advance_step()  # 0 → 1 → 2 → ... → 63 → 0

    # 4. Sleep until next step (drift-corrected)
    await drift_corrected_sleep(step_duration)
```

**Timing Accuracy**: Uses drift correction to maintain long-term timing precision.

**Related**: Step, MessageScheduler, DestinationRouter, Loop Engine

---

### Drift Correction
**Definition**: Technique to maintain accurate timing over long playback sessions by correcting accumulated timing errors.

**Japanese**: ドリフト補正

**Problem**: `asyncio.sleep()` is not perfectly accurate; small errors accumulate over time.

**Solution**: Use an anchor time and calculate expected step times:
```python
anchor_time = time.perf_counter()
expected_time = anchor_time + (step_count * step_duration)
wait_time = max(0, expected_time - time.perf_counter())
await asyncio.sleep(wait_time)
```

**Related**: Step Loop, Loop Engine

---

## Senders

### OscDestinationSender
**Definition**: Sends messages to OSC destinations using the pythonosc library.

**Japanese**: OSCデスティネーション送信機

**Location**: `packages/oiduna_scheduler/senders.py`

**Configuration**:
```python
OscDestinationSender(
    host="127.0.0.1",
    port=57120,
    address="/dirt/play",
    use_bundle=False
)
```

**Behavior**:
- Converts `params` dict to OSC message arguments
- Sends to configured host:port with specified address

**Related**: Destination, DestinationRouter

---

### MidiDestinationSender
**Definition**: Sends messages to MIDI destinations using the mido library.

**Japanese**: MIDIデスティネーション送信機

**Location**: `packages/oiduna_scheduler/senders.py`

**Configuration**:
```python
MidiDestinationSender(
    port_name="USB MIDI 1",
    default_channel=0
)
```

**Supported MIDI Messages**:
- Note On/Off
- Control Change (CC)
- Pitch Bend
- Aftertouch

**Related**: Destination, DestinationRouter

---

## Acronyms & Abbreviations

- **API**: Application Programming Interface
- **BPM**: Beats Per Minute
- **CPS**: Cycles Per Second (SuperDirt-specific)
- **MIDI**: Musical Instrument Digital Interface
- **OSC**: Open Sound Control
- **ABC**: Abstract Base Class (Python)
- **IPC**: Inter-Process Communication
- **PPQ**: Pulses Per Quarter note (MIDI clock)

---

## Architecture Principles

### Destination-Agnostic
**Definition**: Oiduna core does not have knowledge of specific destinations (SuperDirt, MIDI devices, etc.).

**Implementation**:
- Messages use generic `params` dict
- Destinations interpret params according to their protocol
- Destination-specific logic handled by extensions

**Benefits**:
- Oiduna core remains simple
- Easy to add new destinations
- Distribution-agnostic

---

### Distribution-Agnostic
**Definition**: Oiduna core does not have knowledge of specific distributions (MARS, etc.).

**Implementation**:
- Messages are generic ScheduledMessage objects
- Distribution-specific concepts (MixerLine) handled by extensions
- No distribution logic in loop_engine

**Benefits**:
- Multiple distributions can target Oiduna
- Clean separation of concerns

---

## File Locations (for reference)

- **Glossary**: `/oiduna/GLOSSARY.md` (this file)
- **Destinations Config**: `/oiduna/destinations.yaml`
- **Extensions Config**: `/oiduna/extensions.yaml`
- **MessageScheduler**: `/oiduna/packages/oiduna_scheduler/scheduler.py`
- **DestinationRouter**: `/oiduna/packages/oiduna_scheduler/router.py`
- **Loop Engine**: `/oiduna/packages/oiduna_loop/engine/loop_engine.py`
- **API Routes**: `/oiduna/packages/oiduna_api/routes/playback.py`

---

**Last Updated**: 2026-02-25
**Version**: 1.0
