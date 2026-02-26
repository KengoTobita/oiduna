# ScheduledMessageBatch方式 - 処理フローとデータ構造

**作成日**: 2026-02-26
**目的**: ScheduledMessageBatch方式の完全な処理フローとデータ構造を理解する

---

## 概要

ScheduledMessageBatch方式は、**現在実際に音を出している**Oidunaのデータアーキテクチャです。

### 特徴

✅ **実装済み**: ループエンジンで実際に動作
✅ **Destination-Agnostic**: OSC/MIDI/カスタム送信先に対応
✅ **シンプル**: フラットなメッセージリスト
✅ **拡張可能**: ExtensionPipelineで変換可能

❌ **型安全性が低い**: `params: dict[str, Any]`
❌ **階層構造なし**: Track/Sequenceの概念がない

---

## 完全なデータフロー

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. HTTP API Layer (FastAPI)                                    │
│    POST /playback/session                                       │
└─────────────────────────────────────────────────────────────────┘
                           │
                           │ JSON Request Body
                           │ {
                           │   "messages": [...],
                           │   "bpm": 120.0,
                           │   "pattern_length": 4.0
                           │ }
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. Pydantic Validation                                         │
│    SessionRequest model                                         │
│    - messages: list[ScheduledMessageRequest]                   │
│    - bpm: float (gt=0)                                         │
│    - pattern_length: float (gt=0)                              │
└─────────────────────────────────────────────────────────────────┘
                           │
                           │ Validated Data
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. Extension Pipeline (Optional)                               │
│    ExtensionPipeline.apply(payload)                            │
│                                                                 │
│    例: SuperDirtExtension                                       │
│    - mixer_line_id → orbit マッピング                          │
│    - パラメータ名変換 (snake_case → camelCase)                 │
│    - カスタムパラメータ追加                                     │
└─────────────────────────────────────────────────────────────────┘
                           │
                           │ Transformed Payload (dict)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. ScheduledMessageBatch 生成                                  │
│    ScheduledMessageBatch.from_dict(payload)                    │
│                                                                 │
│    @dataclass(frozen=True)                                     │
│    class ScheduledMessageBatch:                                │
│        messages: tuple[ScheduledMessage, ...]                  │
│        bpm: float                                              │
│        pattern_length: float                                   │
└─────────────────────────────────────────────────────────────────┘
                           │
                           │ ScheduledMessageBatch object
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. MessageScheduler                                            │
│    MessageScheduler.load_messages(batch)                       │
│                                                                 │
│    Internal Structure:                                         │
│    _messages_by_step: dict[int, list[ScheduledMessage]]        │
│                                                                 │
│    Example:                                                    │
│    {                                                           │
│        0: [msg1, msg2],      # Step 0 (cycle 0.0)             │
│        16: [msg3],           # Step 16 (cycle 1.0)            │
│        32: [msg4, msg5],     # Step 32 (cycle 2.0)            │
│    }                                                           │
└─────────────────────────────────────────────────────────────────┘
                           │
                           │ Messages indexed by step
                           │
         ┌─────────────────┴─────────────────┐
         │                                   │
         │  ループエンジン起動待機            │
         │  POST /playback/start             │
         │                                   │
         └─────────────────┬─────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. Loop Engine - Step Loop                                     │
│    async def _step_loop(self):                                 │
│                                                                 │
│    while playing:                                              │
│        current_step = self.state.position.step  # 0-255       │
│                                                                 │
│        # Get messages for current step                         │
│        messages = self._message_scheduler                      │
│                     .get_messages_at_step(current_step)        │
│                                                                 │
│        if messages:                                            │
│            # Apply runtime hooks (optional)                    │
│            for hook in self._before_send_hooks:                │
│                messages = hook(messages, bpm, step)            │
│                                                                 │
│            # Send to destinations                              │
│            self._destination_router.send_messages(messages)    │
│                                                                 │
│        # Advance to next step                                  │
│        self.state.advance_step()                               │
│                                                                 │
│        # Drift-corrected sleep                                 │
│        await asyncio.sleep(step_duration)                      │
└─────────────────────────────────────────────────────────────────┘
                           │
                           │ list[ScheduledMessage]
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. DestinationRouter                                           │
│    DestinationRouter.send_messages(messages)                   │
│                                                                 │
│    # Group messages by destination_id                          │
│    by_destination = defaultdict(list)                          │
│    for msg in messages:                                        │
│        by_destination[msg.destination_id].append(msg)          │
│                                                                 │
│    # Send to each destination                                  │
│    for dest_id, dest_messages in by_destination.items():       │
│        sender = self._senders[dest_id]                         │
│        for msg in dest_messages:                               │
│            sender.send_message(msg.params)                     │
└─────────────────────────────────────────────────────────────────┘
                           │
         ┌─────────────────┴─────────────────┐
         │                                   │
         ▼                                   ▼
┌──────────────────────┐          ┌──────────────────────┐
│ 8a. OSC Sender       │          │ 8b. MIDI Sender      │
│                      │          │                      │
│ OscDestinationSender │          │ MidiDestinationSender│
│                      │          │                      │
│ send_message(params) │          │ send_message(params) │
│   │                  │          │   │                  │
│   │ Convert to OSC   │          │   │ Convert to MIDI  │
│   │ args format:     │          │   │ messages:        │
│   │ [k,v,k,v,...]    │          │   │ note_on/note_off │
│   │                  │          │   │ control_change   │
│   ▼                  │          │   ▼                  │
│ pythonosc            │          │ mido                 │
│ SimpleUDPClient      │          │ output port          │
└──────────────────────┘          └──────────────────────┘
         │                                   │
         ▼                                   ▼
┌──────────────────────┐          ┌──────────────────────┐
│ SuperDirt (OSC)      │          │ MIDI Hardware        │
│ 127.0.0.1:57120      │          │ (Synth/DAW)          │
│ /dirt/play           │          │                      │
└──────────────────────┘          └──────────────────────┘

         🔊 音が出る！
```

---

## データ構造の詳細

### 1. HTTP Request (JSON)

```json
{
  "messages": [
    {
      "destination_id": "superdirt",
      "cycle": 0.0,
      "step": 0,
      "params": {
        "s": "bd",
        "gain": 0.8,
        "pan": 0.5,
        "orbit": 0
      }
    },
    {
      "destination_id": "superdirt",
      "cycle": 1.0,
      "step": 16,
      "params": {
        "s": "sn",
        "gain": 0.9
      }
    },
    {
      "destination_id": "volca_bass",
      "cycle": 2.0,
      "step": 32,
      "params": {
        "note": 36,
        "velocity": 100,
        "duration_ms": 250,
        "channel": 0
      }
    }
  ],
  "bpm": 120.0,
  "pattern_length": 4.0
}
```

### 2. Pydantic Models (Validation)

```python
# oiduna_api/routes/playback.py:21-38

class ScheduledMessageRequest(BaseModel):
    """個別メッセージのバリデーション"""
    destination_id: str = Field(..., description="Destination ID")
    cycle: float = Field(..., description="Cycle position")
    step: int = Field(..., ge=0, le=255, description="Step (0-255)")
    params: dict = Field(default_factory=dict, description="Parameters")

class SessionRequest(BaseModel):
    """セッションリクエストのバリデーション"""
    messages: list[ScheduledMessageRequest] = Field(
        default_factory=list,
        description="Scheduled messages"
    )
    bpm: float = Field(default=120.0, gt=0, description="BPM (positive)")
    pattern_length: float = Field(
        default=4.0,
        gt=0,
        description="Pattern length in cycles"
    )
```

**バリデーション内容**:
- `bpm`: 0より大きい浮動小数点数
- `step`: 0-255の整数
- `destination_id`: 必須文字列
- `params`: 任意のdict（型チェックなし）

### 3. ScheduledMessage (Core Data Structure)

```python
# oiduna_scheduler/scheduler_models.py:14-76

@dataclass(frozen=True, slots=True)
class ScheduledMessage:
    """
    スケジュール済みメッセージ（不変）

    Design principles:
    - frozen=True: イミュータブル（スレッドセーフ、キャッシュ可能）
    - slots=True: メモリフットプリント最小化
    - バリデーションなし: MARSが正当性を保証
    - 汎用paramsディクショナリ: ドメイン知識なし
    """

    destination_id: str         # 送信先ID
    cycle: float                # サイクル位置
    step: int                   # ステップ番号(0-255)
    params: dict[str, Any]      # パラメータ（型なし）

    def to_dict(self) -> dict[str, Any]:
        return {
            "destination_id": self.destination_id,
            "cycle": self.cycle,
            "step": self.step,
            "params": self.params,
        }
```

**重要な設計判断**:
- `frozen=True`: イミュータブルにすることで、ループ内での安全性を確保
- `slots=True`: 大量のメッセージを扱う際のメモリ効率化
- `params: dict[str, Any]`: 型安全性を犠牲にして汎用性を確保

### 4. ScheduledMessageBatch

```python
# oiduna_scheduler/scheduler_models.py:78-114

@dataclass(frozen=True)
class ScheduledMessageBatch:
    """
    メッセージバッチ（セッション全体）

    MARSからOidunaへHTTP API経由で送信される。
    """

    messages: tuple[ScheduledMessage, ...]  # 全メッセージ
    bpm: float = 120.0                      # テンポ
    pattern_length: float = 4.0             # パターン長（サイクル単位）

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScheduledMessageBatch:
        messages = [
            ScheduledMessage.from_dict(msg)
            for msg in data["messages"]
        ]
        return cls(
            messages=tuple(messages),
            bpm=data.get("bpm", 120.0),
            pattern_length=data.get("pattern_length", 4.0),
        )
```

**メモリ効率**:
- `tuple`: リストより軽量、イミュータブル
- メッセージが1000個でも高速ロード（O(n)）

### 5. MessageScheduler (Indexing)

```python
# oiduna_scheduler/scheduler.py:14-96

class MessageScheduler:
    """
    ステップ別メッセージインデックス

    Design:
    - dict lookup: O(1) ステップ検索
    - defaultdict: メモリ効率（空ステップは保存しない）
    - スレッドセーフ（読み取り専用、イミュータブルメッセージ）
    """

    def __init__(self) -> None:
        # step番号 → メッセージリスト
        self._messages_by_step: dict[int, list[ScheduledMessage]] = defaultdict(list)
        self._bpm: float = 120.0
        self._pattern_length: float = 4.0

    def load_messages(self, batch: ScheduledMessageBatch) -> None:
        """メッセージバッチをロード（既存メッセージは削除）"""
        self._messages_by_step.clear()
        self._bpm = batch.bpm
        self._pattern_length = batch.pattern_length

        # ステップごとにインデックス化
        for msg in batch.messages:
            self._messages_by_step[msg.step].append(msg)

    def get_messages_at_step(self, step: int) -> list[ScheduledMessage]:
        """指定ステップのメッセージを取得（O(1)）"""
        return self._messages_by_step.get(step, [])
```

**インデックス構造の例**:

```python
# 3つのメッセージを持つバッチをロード後

_messages_by_step = {
    0: [
        ScheduledMessage("superdirt", 0.0, 0, {"s": "bd", "gain": 0.8}),
        ScheduledMessage("superdirt", 0.0, 0, {"s": "hh", "gain": 0.5}),
    ],
    16: [
        ScheduledMessage("superdirt", 1.0, 16, {"s": "sn", "gain": 0.9}),
    ],
    32: [
        ScheduledMessage("volca_bass", 2.0, 32, {"note": 36, "velocity": 100}),
    ],
}

# ステップ0にアクセス → O(1)で2つのメッセージ取得
# ステップ8にアクセス → O(1)で空リスト取得（メッセージなし）
```

**パフォーマンス**:
- ステップ検索: O(1)
- 空ステップ: メモリ使用なし
- 256ステップ中、10ステップのみ使用 → 10エントリのみ保存

### 6. DestinationRouter (Message Routing)

```python
# oiduna_scheduler/router.py:28-101

class DestinationRouter:
    """
    メッセージをdestination別に振り分けて送信

    Design:
    - destination_id でグルーピング
    - 各Senderに委譲（OSC/MIDI）
    - 未登録destinationは無視（エラーにしない）
    """

    def __init__(self) -> None:
        self._senders: dict[str, DestinationSender] = {}

    def register_destination(
        self,
        destination_id: str,
        sender: DestinationSender
    ) -> None:
        """送信先を登録"""
        self._senders[destination_id] = sender

    def send_messages(self, messages: list[ScheduledMessage]) -> None:
        """メッセージを送信先別に振り分けて送信"""
        if not messages:
            return

        # destination_id でグルーピング
        by_destination: dict[str, list[ScheduledMessage]] = defaultdict(list)
        for msg in messages:
            by_destination[msg.destination_id].append(msg)

        # 各送信先に送信
        for dest_id, dest_messages in by_destination.items():
            sender = self._senders.get(dest_id)
            if sender is None:
                # 未登録の送信先は無視（ログ出力のみ）
                continue

            # メッセージを個別に送信
            for msg in dest_messages:
                sender.send_message(msg.params)
```

**ルーティング例**:

```python
# 入力: 5つのメッセージ
messages = [
    ScheduledMessage("superdirt", 0.0, 0, {"s": "bd"}),
    ScheduledMessage("superdirt", 0.0, 0, {"s": "hh"}),
    ScheduledMessage("volca_bass", 0.0, 0, {"note": 36}),
    ScheduledMessage("superdirt", 0.0, 0, {"s": "sn"}),
    ScheduledMessage("volca_keys", 0.0, 0, {"note": 60}),
]

# グルーピング後:
by_destination = {
    "superdirt": [msg1, msg2, msg4],      # 3メッセージ
    "volca_bass": [msg3],                  # 1メッセージ
    "volca_keys": [msg5],                  # 1メッセージ
}

# 各Senderに送信:
# superdirt → OscDestinationSender.send_message() × 3回
# volca_bass → MidiDestinationSender.send_message() × 1回
# volca_keys → MidiDestinationSender.send_message() × 1回
```

### 7. Destination Senders

#### 7a. OscDestinationSender

```python
# oiduna_scheduler/senders.py:11-86

class OscDestinationSender:
    """
    OSC送信先（SuperDirt等）

    Design:
    - pythonosc.udp_client のラッパー
    - params dict を OSC args に変換
    - アドレス設定可能（/dirt/play固定ではない）
    """

    def __init__(
        self,
        host: str,              # "127.0.0.1"
        port: int,              # 57120
        address: str,           # "/dirt/play"
        use_bundle: bool = False,
    ):
        self.host = host
        self.port = port
        self.address = address
        self.use_bundle = use_bundle
        self._client = udp_client.SimpleUDPClient(host, port)

    def send_message(self, params: dict[str, Any]) -> None:
        """
        OSCメッセージ送信

        params を OSC args format に変換:
        {"s": "bd", "gain": 0.8} → [s, bd, gain, 0.8]
        """
        # フラットなリストに変換
        args = []
        for key, value in params.items():
            args.extend([key, value])

        # OSC送信
        self._client.send_message(self.address, args)
```

**OSC変換例**:

```python
# params
{"s": "bd", "gain": 0.8, "pan": 0.5, "orbit": 0}

# OSC args に変換
["s", "bd", "gain", 0.8, "pan", 0.5, "orbit", 0]

# OSC message（送信）
Address: /dirt/play
Args: [s, bd, gain, 0.8, pan, 0.5, orbit, 0]

# SuperDirt側での解釈
(
    s: "bd",        // サウンド名
    gain: 0.8,      // ゲイン
    pan: 0.5,       // パン
    orbit: 0,       // エフェクトチェーン番号
)
```

#### 7b. MidiDestinationSender

```python
# oiduna_scheduler/senders.py:88-205

class MidiDestinationSender:
    """
    MIDI送信先

    Design:
    - mido output port のラッパー
    - params から MIDI メッセージタイプを判別
    - Note On/Off, CC, Pitch Bend 対応
    """

    def __init__(
        self,
        port_name: str,         # "USB MIDI 1"
        default_channel: int = 0,
    ):
        self.port_name = port_name
        self.default_channel = default_channel
        self._port = mido.open_output(port_name)

    def send_message(self, params: dict[str, Any]) -> None:
        """
        MIDIメッセージ送信

        paramsの内容でメッセージタイプを判別:
        - "note" in params → Note On
        - "cc" in params → Control Change
        - "pitch_bend" in params → Pitch Bend
        """
        channel = params.get("channel", self.default_channel)

        # Note message
        if "note" in params:
            note = params["note"]
            velocity = params.get("velocity", 100)

            # Note On送信
            self._port.send(mido.Message(
                "note_on",
                note=note,
                velocity=velocity,
                channel=channel
            ))

            # TODO: duration_ms 後に Note Off
            # （現在は外部スケジューリング依存）

        # CC message
        elif "cc" in params:
            cc = params["cc"]
            value = params.get("value", 0)
            self._port.send(mido.Message(
                "control_change",
                control=cc,
                value=value,
                channel=channel
            ))

        # Pitch Bend message
        elif "pitch_bend" in params:
            pitch_bend = params["pitch_bend"]
            self._port.send(mido.Message(
                "pitchwheel",
                pitch=pitch_bend,
                channel=channel
            ))
```

**MIDI変換例**:

```python
# params (Note)
{"note": 60, "velocity": 100, "duration_ms": 250, "channel": 0}

# MIDI Message
type: note_on
note: 60 (C4)
velocity: 100
channel: 0

# params (CC)
{"cc": 74, "value": 64, "channel": 0}

# MIDI Message
type: control_change
control: 74 (Brightness)
value: 64
channel: 0
```

### 8. Destination Configuration

#### destinations.yaml

```yaml
# /home/tobita/study/livecoding/oiduna/destinations.yaml

destinations:
  # OSC destination (SuperDirt)
  superdirt:
    id: superdirt
    type: osc
    host: 127.0.0.1
    port: 57120
    address: /dirt/play
    use_bundle: false

  # MIDI destination
  volca_bass:
    id: volca_bass
    type: midi
    port_name: "USB MIDI 1"
    default_channel: 0

  volca_keys:
    id: volca_keys
    type: midi
    port_name: "USB MIDI 1"
    default_channel: 1
```

#### Pydantic Models (Validation)

```python
# oiduna_destination/destination_models.py:13-113

class OscDestinationConfig(BaseModel):
    """OSC送信先設定（バリデーション付き）"""

    id: str = Field(..., min_length=1)
    type: Literal["osc"] = "osc"
    host: str = Field(default="127.0.0.1")
    port: Annotated[int, Field(ge=1024, le=65535)]  # ポート番号範囲チェック
    address: str = Field(...)                       # OSCアドレス
    use_bundle: bool = Field(default=False)

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        """OSCアドレスは '/' で始まる必要がある"""
        if not v.startswith("/"):
            raise ValueError(f"OSC address must start with '/': {v}")
        return v

class MidiDestinationConfig(BaseModel):
    """MIDI送信先設定（バリデーション付き）"""

    id: str = Field(..., min_length=1)
    type: Literal["midi"] = "midi"
    port_name: str = Field(...)
    default_channel: Annotated[int, Field(ge=0, le=15)]  # MIDIチャンネル範囲

    @field_validator("port_name")
    @classmethod
    def validate_port_exists(cls, v: str) -> str:
        """MIDIポートが存在するかチェック（警告のみ）"""
        try:
            import mido
            available_ports = mido.get_output_names()
            if v not in available_ports:
                warnings.warn(
                    f"MIDI port '{v}' not found. Available: {available_ports}"
                )
        except (ImportError, Exception):
            pass
        return v
```

**バリデーション内容**:
- OSC: ポート範囲(1024-65535)、アドレス形式
- MIDI: チャンネル範囲(0-15)、ポート存在チェック

#### Loader

```python
# oiduna_destination/loader.py:79-124

def load_destinations_from_file(
    file_path: Path | str
) -> dict[str, DestinationConfig]:
    """
    YAML/JSON ファイルから送信先設定をロード

    Returns:
        {destination_id: DestinationConfig}
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")

    # YAMLパース
    content = path.read_text(encoding="utf-8")
    config_data = yaml.safe_load(content)

    # バリデーション
    destinations = {}
    for dest_id, dest_config in config_data["destinations"].items():
        dest_type = dest_config.get("type")

        if dest_type == "osc":
            config = OscDestinationConfig(**dest_config)
        elif dest_type == "midi":
            config = MidiDestinationConfig(**dest_config)
        else:
            raise ValueError(f"Unknown type '{dest_type}'")

        destinations[dest_id] = config

    return destinations
```

---

## 具体的な実行例

### シナリオ: キック＋スネア＋MIDIベースのパターン

#### 1. HTTP Request

```http
POST /playback/session HTTP/1.1
Content-Type: application/json

{
  "messages": [
    {
      "destination_id": "superdirt",
      "cycle": 0.0,
      "step": 0,
      "params": {"s": "bd", "gain": 0.8, "orbit": 0}
    },
    {
      "destination_id": "superdirt",
      "cycle": 1.0,
      "step": 16,
      "params": {"s": "sn", "gain": 0.9, "orbit": 0}
    },
    {
      "destination_id": "volca_bass",
      "cycle": 0.0,
      "step": 0,
      "params": {"note": 36, "velocity": 100, "channel": 0}
    }
  ],
  "bpm": 120.0,
  "pattern_length": 2.0
}
```

#### 2. MessageScheduler のインデックス

```python
_messages_by_step = {
    0: [
        ScheduledMessage("superdirt", 0.0, 0, {"s": "bd", "gain": 0.8, "orbit": 0}),
        ScheduledMessage("volca_bass", 0.0, 0, {"note": 36, "velocity": 100, "channel": 0}),
    ],
    16: [
        ScheduledMessage("superdirt", 1.0, 16, {"s": "sn", "gain": 0.9, "orbit": 0}),
    ],
}
```

#### 3. ループエンジンの動作

```
Step 0:
  ├─ get_messages_at_step(0) → 2メッセージ取得
  │
  ├─ DestinationRouter.send_messages([msg1, msg2])
  │   ├─ Grouping by destination_id:
  │   │   ├─ "superdirt": [msg1]
  │   │   └─ "volca_bass": [msg2]
  │   │
  │   ├─ OscDestinationSender.send_message({"s": "bd", "gain": 0.8, "orbit": 0})
  │   │   → OSC message: /dirt/play [s, bd, gain, 0.8, orbit, 0]
  │   │   → SuperDirt: キック音再生 🔊
  │   │
  │   └─ MidiDestinationSender.send_message({"note": 36, "velocity": 100, "channel": 0})
  │       → MIDI message: note_on note=36 vel=100 ch=0
  │       → Volca Bass: C2音再生 🔊
  │
  └─ sleep(0.125秒) # 120 BPM → step_duration = 60/120/4 = 0.125s

Step 1-15:
  └─ get_messages_at_step(1) → 空リスト（何もしない）
  └─ sleep(0.125秒)

Step 16:
  ├─ get_messages_at_step(16) → 1メッセージ取得
  │
  ├─ DestinationRouter.send_messages([msg3])
  │   └─ OscDestinationSender.send_message({"s": "sn", "gain": 0.9, "orbit": 0})
  │       → OSC message: /dirt/play [s, sn, gain, 0.9, orbit, 0]
  │       → SuperDirt: スネア音再生 🔊
  │
  └─ sleep(0.125秒)

Step 17-31:
  └─ (空ステップ)

Step 32:
  └─ pattern_length = 2.0 cycles = 32 steps
  └─ ループして Step 0 に戻る
```

---

## パフォーマンス特性

### メモリ使用量

```
1メッセージあたりのメモリ:
  ScheduledMessage:
    - destination_id: ~8 bytes (文字列参照)
    - cycle: 8 bytes (float64)
    - step: 8 bytes (int64)
    - params: ~100 bytes (dict overhead + entries)
    ≈ 124 bytes/message

1000メッセージのバッチ:
  ≈ 124KB (非常に軽量)

インデックス:
  dict[int, list] overhead: ~20 bytes/entry
  256ステップ中50ステップ使用: ~1KB
```

### CPU使用量

```
ステップ処理 (16th note @ 120 BPM = 8回/秒):
  - get_messages_at_step(): O(1) dict lookup ≈ 0.1μs
  - DestinationRouter.send_messages(): O(n) grouping ≈ 1-10μs
  - OSC send_message(): UDP送信 ≈ 10-50μs

合計: ~100μs/step (ステップ間隔 125ms に対して十分低い)
```

### レイテンシ

```
HTTP Request → 音が出るまで:
  1. Pydantic validation: ~100μs
  2. Extension pipeline: ~50μs (シンプルな変換)
  3. MessageScheduler indexing: ~1ms (1000メッセージ)
  4. 次のステップ待機: 最大125ms
  5. OSC送信: ~50μs

最悪ケース: ~126ms (次ステップまで待機)
最良ケース: ~0.2ms (ちょうどステップ境界で受信)
```

---

## 型安全性の問題と改善案

### 現状の問題

```python
# ❌ 型チェックが効かない
params: dict[str, Any] = {
    "s": "bd",
    "gain": "invalid_string",  # 🔴 文字列でもOK（実行時エラー）
    "typo_orbit": 0,            # 🔴 タイポも検出できない
}

# ❌ IDEオートコンプリートなし
params["g"]  # 🔴 "gain"の補完が出ない

# ❌ リファクタリングに弱い
# "gain" → "volume" に名前変更しても検出できない
```

### 改善案（提案）

#### 案1: TypedDict（静的型チェック）

```python
from typing import TypedDict

class SuperDirtParams(TypedDict, total=False):
    """SuperDirt用パラメータ（型安全）"""
    s: str              # サウンド名
    n: int              # サンプル番号
    gain: float         # ゲイン
    pan: float          # パン
    orbit: int          # オービット
    room: float         # リバーブ
    # ... 他のパラメータ

# ✅ 型チェックが効く
params: SuperDirtParams = {
    "s": "bd",
    "gain": 0.8,        # OK
    # "gain": "invalid"  # 🔴 型エラー（静的チェックで検出）
}

# ✅ IDEオートコンプリート
params["g"]  # → "gain"が補完される
```

**利点**: 静的型チェック、IDEサポート
**欠点**: カスタムパラメータに弱い、`total=False`でも型チェックは限定的

#### 案2: Pydantic（実行時バリデーション）

```python
from pydantic import BaseModel, Field

class SuperDirtParams(BaseModel):
    """SuperDirt用パラメータ（バリデーション付き）"""
    s: str = Field(..., description="Sound name")
    n: int = Field(default=0, ge=0)
    gain: float = Field(default=1.0, ge=0.0, le=2.0)
    pan: float = Field(default=0.5, ge=0.0, le=1.0)
    orbit: int = Field(default=0, ge=0, le=11)

# ✅ 実行時バリデーション
try:
    params = SuperDirtParams(s="bd", gain="invalid")
except ValidationError as e:
    # 🔴 明確なエラーメッセージ
    # gain: Input should be a valid number
```

**利点**: 実行時エラー検出、明確なエラーメッセージ
**欠点**: パフォーマンスオーバーヘッド、拡張性が低い

#### 案3: Runtime Validator（推奨）

```python
class ParamsValidator(Protocol):
    def validate(self, params: dict[str, Any]) -> dict[str, Any]:
        ...

class SuperDirtValidator:
    REQUIRED = {"s"}
    OPTIONAL = {"n", "gain", "pan", "orbit", "room", ...}

    def validate(self, params: dict[str, Any]) -> dict[str, Any]:
        # 必須パラメータチェック
        if "s" not in params:
            raise ValueError("Missing required param: s")

        # 型チェック
        if not isinstance(params["s"], str):
            raise TypeError(f"s must be str, got {type(params['s'])}")

        # 範囲チェック
        if "gain" in params and not (0.0 <= params["gain"] <= 2.0):
            raise ValueError(f"gain must be in [0.0, 2.0]")

        return params

# DestinationSenderに組み込む
class OscDestinationSender:
    def __init__(self, validator: ParamsValidator | None = None):
        self.validator = validator or NoOpValidator()

    def send_message(self, params: dict[str, Any]) -> None:
        params = self.validator.validate(params)  # バリデーション
        # ... OSC送信
```

**利点**: 柔軟性、既存コードと互換、カスタムバリデーター追加可能
**欠点**: 静的型チェックは効かない

---

## まとめ

### ScheduledMessageBatch方式の特徴

✅ **シンプルで実装済み**: フラットなメッセージリスト、実際に音が出る
✅ **Destination-Agnostic**: OSC/MIDI/カスタム送信先に柔軟対応
✅ **パフォーマンス良好**: O(1)ステップ検索、低CPU使用量
✅ **拡張可能**: ExtensionPipelineで変換可能

❌ **型安全性が低い**: `params: dict[str, Any]`
❌ **階層構造なし**: Track/Sequenceの概念がない
❌ **バリデーションなし**: 送信先でエラーが起きる可能性

### 次のステップ

1. **型安全性向上の方針決定**
   - TypedDict vs Pydantic vs Runtime Validator
   - パフォーマンス vs 安全性のバランス

2. **CompiledSessionとの統合検討**
   - 変換処理の実装場所（MARS vs Oiduna vs Extension）
   - 両方維持 vs 一本化

3. **GLOSSARY.mdの修正**
   - Session/Patternの定義を明確化
   - paramsの具体例を追加

これらについてディスカッションを進めていきましょう。
