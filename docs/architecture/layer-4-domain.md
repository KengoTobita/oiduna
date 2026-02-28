# Layer 4: ドメイン層 (Scheduling & Optimization)

**パッケージ**: `oiduna_scheduler`

**最終更新**: 2026-03-01

---

## 概要

ドメイン層は、メッセージのスケジューリングと最適化を担当します。Session階層構造をフラットなメッセージリストに変換し、O(1)で高速検索できるインデックスを構築します。

### 責任

- ✅ ScheduledMessage, ScheduledMessageBatchの定義
- ✅ ステップ別インデックスの構築（O(1)検索）
- ✅ 送信先非依存の設計
- ✅ MARSとOidunaの共通フォーマット
- ❌ 実際の送信処理（Layer 3に任せる）
- ❌ Session構造の管理（Layer 5に任せる）

### 依存関係

```
oiduna_scheduler → なし（完全に独立）
```

**設計原則**: ドメイン層はどの層にも依存しない（純粋なアルゴリズム層）

---

## パッケージ構成

```
oiduna_scheduler/
├── __init__.py
├── scheduler_models.py   # ScheduledMessage, ScheduledMessageBatch
├── scheduler.py          # MessageScheduler
└── validators/
    └── midi_validator.py # MIDI仕様バリデーション
```

---

## 主要なデータ構造

### 1. ScheduledMessage

単一のスケジュール済みメッセージ。

```python
@dataclass(frozen=True)
class ScheduledMessage:
    """タイミング情報付きメッセージ"""
    destination_id: str           # 送信先ID
    step: int                     # ステップ番号 (0-255)
    cycle: float                  # サイクル位置
    params: dict[str, Any]        # 送信先依存パラメータ
```

**特徴**:
- **イミュータブル**: `frozen=True`で不変
- **送信先非依存**: `params`は任意の辞書
- **タイミング情報**: `step`と`cycle`の両方を保持

**使用例**:
```python
# SuperDirt向けメッセージ
msg1 = ScheduledMessage(
    destination_id="superdirt",
    step=0,
    cycle=0.0,
    params={"sound": "bd", "orbit": 0, "track_id": "kick"}
)

# MIDI向けメッセージ
msg2 = ScheduledMessage(
    destination_id="volca",
    step=64,
    cycle=1.0,
    params={"note": 60, "velocity": 100, "duration": 0.5}
)
```

### 2. ScheduledMessageBatch

メッセージ群とメタデータ。

```python
@dataclass(frozen=True)
class ScheduledMessageBatch:
    """スケジュール済みメッセージのバッチ"""
    messages: tuple[ScheduledMessage, ...]
    bpm: float
    pattern_length: float  # サイクル数（例: 4.0）
```

**なぜtupleなのか**:
- イミュータブル（一度作成したら変更不可）
- ハッシュ可能
- 並行処理で安全

**JSON変換**:
```python
batch = ScheduledMessageBatch(
    messages=(msg1, msg2),
    bpm=120.0,
    pattern_length=4.0
)

# dict化
batch_dict = {
    "messages": [asdict(msg) for msg in batch.messages],
    "bpm": batch.bpm,
    "pattern_length": batch.pattern_length
}

# JSON文字列化
import json
json_str = json.dumps(batch_dict)
```

**MARSからのHTTP送信**:
```python
# MARS側（送信）
import requests
response = requests.post(
    "http://localhost:57122/playback/session",
    json=batch_dict
)

# Oiduna側（受信）
from oiduna_scheduler import ScheduledMessageBatch
batch = ScheduledMessageBatch(**request_data)
```

---

## MessageScheduler: O(1)高速検索

### 仕組み

階層構造をフラット化し、ステップ番号から即座にメッセージを取得できるインデックスを構築。

```python
class MessageScheduler:
    def __init__(self, batch: ScheduledMessageBatch):
        self.batch = batch
        self._index: dict[int, list[int]] = {}  # step → indices

        # インデックス構築（O(N)、初回のみ）
        for i, msg in enumerate(batch.messages):
            if msg.step not in self._index:
                self._index[msg.step] = []
            self._index[msg.step].append(i)

    def get_at_step(self, step: int) -> list[ScheduledMessage]:
        """特定ステップのメッセージ取得（O(1)）"""
        indices = self._index.get(step, [])
        return [self.batch.messages[i] for i in indices]
```

### パフォーマンス特性

```
インデックス構築: O(N)（メッセージ数）
検索: O(1)（ステップあたりのメッセージ数は定数）
メモリ: O(N)（インデックスとメッセージ）
```

### 使用例

```python
# メッセージバッチ作成
messages = (
    ScheduledMessage("superdirt", 0, 0.0, {"sound": "bd"}),
    ScheduledMessage("superdirt", 0, 0.0, {"sound": "sd"}),  # 同じステップ
    ScheduledMessage("superdirt", 64, 1.0, {"sound": "hh"}),
    ScheduledMessage("volca", 64, 1.0, {"note": 60}),
)
batch = ScheduledMessageBatch(messages, 120.0, 4.0)

# スケジューラー作成（インデックス構築）
scheduler = MessageScheduler(batch)

# ステップ0のメッセージ取得（O(1)）
msgs_at_0 = scheduler.get_at_step(0)
# → [msg(bd), msg(sd)]

# ステップ64のメッセージ取得（O(1)）
msgs_at_64 = scheduler.get_at_step(64)
# → [msg(hh), msg(note=60)]

# 存在しないステップ
msgs_at_100 = scheduler.get_at_step(100)
# → []
```

### なぜO(1)が重要か

LoopEngineは256ステップを高速に処理する必要があります：

```python
# LoopEngine内部（疑似コード）
for step in range(256):
    messages = scheduler.get_at_step(step)  # O(1)で取得
    for msg in messages:
        send_to_destination(msg)  # OSC/MIDI送信
    await asyncio.sleep(step_duration)
```

もしO(N)検索だと：
- 256ステップ × N個のメッセージ = O(256N)
- 高BPMで遅延が発生

O(1)検索なら：
- 256ステップ × 定数時間 = O(256)
- 常に高速

---

## フラット構造 vs 階層構造

### 階層構造（旧）

```python
Session
  └─ Track("kick")
      ├─ base_params: {"sound": "bd"}
      └─ Pattern("main")
          └─ Event(step=0, params={})
```

**問題点**:
- トラック階層を維持する必要がある
- 特定ステップのメッセージ取得にO(N)
- 送信先がSuperDirt固定

### フラット構造（新）

```python
ScheduledMessageBatch([
    ScheduledMessage(
        destination_id="superdirt",
        step=0,
        cycle=0.0,
        params={"sound": "bd", "track_id": "kick"}
    ),
    ...
])
```

**利点**:
- トラック情報は`params`に埋め込み
- ステップ→メッセージがO(1)
- 送信先非依存（`destination_id`で任意の送信先）

---

## 送信先非依存設計

### params: dict[str, Any]の柔軟性

```python
# SuperDirt向け
params = {
    "sound": "bd",
    "gain": 0.8,
    "orbit": 0,
    "track_id": "kick"
}

# MIDI向け
params = {
    "note": 60,
    "velocity": 100,
    "duration": 0.5,
    "channel": 1
}

# カスタム送信先向け
params = {
    "custom_param_1": "value",
    "custom_param_2": 42
}
```

**Oiduna側での処理**:
```python
# DestinationRouter (Layer 3)
if msg.destination_id == "superdirt":
    # SuperDirt向けにOSC送信
    osc_sender.send(
        host=dest.host,
        port=dest.port,
        address=dest.address,
        params=msg.params  # そのまま渡す
    )
elif msg.destination_id == "volca":
    # MIDI送信
    midi_sender.send(
        port=dest.port_name,
        note=msg.params["note"],
        velocity=msg.params["velocity"]
    )
```

---

## MARSとの統合

### SessionCompiler (Layer 2)

SessionをScheduledMessageBatchに変換：

```python
# oiduna_session/compiler.py
class SessionCompiler:
    @staticmethod
    def compile(session: Session) -> ScheduledMessageBatch:
        messages = []

        for track in session.tracks.values():
            for pattern in track.patterns.values():
                if not pattern.active:
                    continue

                for event in pattern.events:
                    # base_paramsとevent.paramsをマージ
                    merged_params = {
                        **track.base_params,
                        **event.params,
                        "track_id": track.track_id
                    }

                    msg = ScheduledMessage(
                        destination_id=track.destination_id,
                        step=event.step,
                        cycle=event.cycle,
                        params=merged_params
                    )
                    messages.append(msg)

        return ScheduledMessageBatch(
            messages=tuple(messages),
            bpm=session.environment.bpm,
            pattern_length=4.0  # デフォルト
        )
```

### MARSからのHTTP送信

```
MARS DSL
  ↓ コンパイル
RuntimeSession (MARS内部表現)
  ↓ 変換
ScheduledMessageBatch (JSON)
  ↓ HTTP POST /playback/session
Oiduna LoopEngine
```

**HTTPリクエスト例**:
```json
POST /playback/session
Content-Type: application/json

{
  "messages": [
    {
      "destination_id": "superdirt",
      "step": 0,
      "cycle": 0.0,
      "params": {"sound": "bd", "orbit": 0}
    },
    {
      "destination_id": "superdirt",
      "step": 64,
      "cycle": 1.0,
      "params": {"sound": "sd", "orbit": 0}
    }
  ],
  "bpm": 120.0,
  "pattern_length": 4.0
}
```

---

## MIDI仕様バリデーション

### MIDIValidator

MIDI 1.0仕様に準拠したバリデーション：

```python
# oiduna_scheduler/validators/midi_validator.py
class MIDIValidator:
    @staticmethod
    def validate_note(note: int) -> None:
        """ノート番号は0-127"""
        if not 0 <= note <= 127:
            raise ValueError(f"MIDI note must be 0-127, got {note}")

    @staticmethod
    def validate_velocity(velocity: int) -> None:
        """ベロシティは0-127"""
        if not 0 <= velocity <= 127:
            raise ValueError(f"MIDI velocity must be 0-127, got {velocity}")

    @staticmethod
    def validate_channel(channel: int) -> None:
        """チャンネルは1-16"""
        if not 1 <= channel <= 16:
            raise ValueError(f"MIDI channel must be 1-16, got {channel}")
```

**使用例**:
```python
# MIDISender内部（Layer 3）
try:
    MIDIValidator.validate_note(msg.params["note"])
    MIDIValidator.validate_velocity(msg.params["velocity"])
    # 送信処理
except ValueError as e:
    logger.error(f"Invalid MIDI message: {e}")
```

---

## Rust移植の考慮事項

### 優先度: 中 🔶

パフォーマンスクリティカルだが、Python実装でも十分高速。

### Rust実装の方針

```rust
use std::collections::HashMap;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScheduledMessage {
    pub destination_id: String,
    pub step: u8,  // 0-255
    pub cycle: f64,
    pub params: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone)]
pub struct MessageScheduler {
    batch: ScheduledMessageBatch,
    index: HashMap<u8, Vec<usize>>,
}

impl MessageScheduler {
    pub fn new(batch: ScheduledMessageBatch) -> Self {
        let mut index: HashMap<u8, Vec<usize>> = HashMap::new();

        for (i, msg) in batch.messages.iter().enumerate() {
            index.entry(msg.step)
                 .or_insert_with(Vec::new)
                 .push(i);
        }

        Self { batch, index }
    }

    pub fn get_at_step(&self, step: u8) -> Vec<&ScheduledMessage> {
        self.index.get(&step)
            .map(|indices| {
                indices.iter()
                    .map(|&i| &self.batch.messages[i])
                    .collect()
            })
            .unwrap_or_default()
    }
}
```

### パフォーマンス向上見込み

- インデックス構築: 5-10倍高速化
- メモリ使用量: 20-30%削減
- 並行処理: Rustのスレッドで安全

---

## テスト例

### ユニットテスト

```python
def test_message_scheduler_indexing():
    """インデックス構築のテスト"""
    messages = (
        ScheduledMessage("dest1", 0, 0.0, {}),
        ScheduledMessage("dest1", 0, 0.0, {}),  # 同じステップ
        ScheduledMessage("dest2", 64, 1.0, {}),
    )
    batch = ScheduledMessageBatch(messages, 120.0, 4.0)
    scheduler = MessageScheduler(batch)

    # ステップ0には2メッセージ
    msgs_0 = scheduler.get_at_step(0)
    assert len(msgs_0) == 2

    # ステップ64には1メッセージ
    msgs_64 = scheduler.get_at_step(64)
    assert len(msgs_64) == 1

    # ステップ100にはメッセージなし
    msgs_100 = scheduler.get_at_step(100)
    assert len(msgs_100) == 0

def test_scheduled_message_immutability():
    """メッセージのイミュータブル性"""
    msg = ScheduledMessage("dest", 0, 0.0, {"key": "value"})

    # フィールド変更は不可
    with pytest.raises(AttributeError):
        msg.step = 1
```

---

## まとめ

### ドメイン層の重要性

1. **パフォーマンス**: O(1)検索で高速処理
2. **柔軟性**: 送信先非依存設計
3. **シンプルさ**: フラット構造で理解しやすい
4. **MARSとの統合**: 共通フォーマットで連携

### 設計判断

- **フラット構造**: トラック階層を持たない
- **イミュータブル**: dataclass(frozen=True)
- **O(1)検索**: ステップ別インデックス
- **送信先非依存**: `params: dict[str, Any]`

### 次のステップ

ドメイン層を理解したら：
1. [Layer 3: コア層](./layer-3-core.md)で実際の実行を学ぶ
2. [Layer 2: アプリケーション層](./layer-2-application.md)でコンパイルを理解
3. [Layer 5: データ層](./layer-5-data.md)でデータ構造を学ぶ
4. [データフロー例](./data-flow-examples.md)で全体の流れを確認

---

**関連ドキュメント**:
- `packages/oiduna_scheduler/README.md`
- ADR-0007: Destination-Agnostic Core
- ADR-0012: Package Architecture
