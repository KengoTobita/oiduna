# Oiduna コーディング規約

**バージョン**: 1.0.0
**作成日**: 2026-03-11
**対象**: Oiduna開発者

このドキュメントは、Oidunaプロジェクトにおけるコーディング規約を定めます。一貫性のあるコードベースを維持し、開発者間の齟齬を防ぐために、以下の規約に従ってください。

## 目次

1. [命名規則](#命名規則)
2. [ID形式ルール](#id形式ルール)
3. [パラメータ命名規則](#パラメータ命名規則)
4. [型定義方針](#型定義方針)
5. [モジュール構成原則](#モジュール構成原則)
6. [ドキュメントルール](#ドキュメントルール)
7. [パフォーマンスガイドライン](#パフォーマンスガイドライン)

---

## 命名規則

### 基本方針

Oidunaは**PEP 8準拠**のPython命名規則を採用します。

| 対象 | 規則 | 例 |
|------|------|-----|
| モジュール名 | snake_case | `scheduler.py`, `router.py` |
| クラス名 | PascalCase | `LoopScheduler`, `DestinationRouter` |
| 関数名 | snake_case | `get_messages_for_step()`, `send_messages()` |
| 変数名 | snake_case | `step_index`, `destination_id` |
| 定数 | UPPER_SNAKE_CASE | `LOOP_STEPS`, `DRIFT_RESET_THRESHOLD_MS` |
| プライベートメソッド | _snake_case | `_emit_event()`, `_build_index()` |

### クラス名の命名パターン

#### Manager系（CRUD操作）

- **形式**: `{Domain}Manager`
- **例**: `ClientManager`, `TrackManager`, `PatternManager`
- **責務**: 単一ドメインのCRUD操作

#### Producer/Consumer系（IPC通信）

- **形式**: `{Direction}{Protocol}Producer/Consumer`
- **例**: `CommandProducer`, `StateConsumer`, `InProcessStateProducer`
- **責務**: プロセス間通信のインターフェース

#### Sender系（プロトコル実装）

- **形式**: `{Protocol}DestinationSender`
- **例**: `OscDestinationSender`, `MidiDestinationSender`
- **責務**: 送信先固有のプロトコル実装

#### Scheduler/Router系（処理フロー）

- **形式**: `{Purpose}Scheduler/Router`
- **例**: `LoopScheduler`, `DestinationRouter`
- **責務**: データの変換・振り分け

### 対になる概念の命名

Oidunaでは対になる概念が多く存在します。これらは**明確に対応する名前**を使用してください。

| 対の概念 | 説明 | 例 |
|---------|------|-----|
| Producer ↔ Consumer | メッセージ送信 ↔ 受信 | `CommandProducer` ↔ `CommandConsumer` |
| Send ↔ Receive | データ送信 ↔ 受信 | `send_command()` ↔ `receive_command()` |
| Publish ↔ Subscribe | イベント発行 ↔ 購読 | `publish()` ↔ `subscribe()` |
| Mute ↔ Solo | トラック無音化 ↔ 単独再生 | `mute_track()` ↔ `solo_track()` |
| Load ↔ Unload | データ読み込み ↔ 破棄 | `load_messages()` ↔ `unload()` |

**悪い例**:
- `CommandSender` ↔ `CommandConsumer`（SenderとConsumerは対ではない）
- `publish()` ↔ `receive()`（PublishとReceiveは対ではない）

---

## ID形式ルール

### ID種別と形式

| ID種別 | 形式 | 長さ | 例 | 生成方法 |
|--------|------|------|-----|----------|
| Session ID | hexadecimal | 8桁 | `a1b2c3d4` | `generate_session_id()` |
| Client ID | hexadecimal | 4桁 | `0a1f` | `generate_client_id()` またはユーザー定義 |
| Track ID | hexadecimal | 4桁 | `3e2b` | ユーザー定義、Track modelで検証 |
| Pattern ID | hexadecimal | 4桁 | `7f8a` | ユーザー定義、Pattern modelで検証 |
| Destination ID | 英数字+ハイフン/アンダースコア | 任意 | `superdirt`, `volca_bass` | destinations.yamlで定義 |

### ID生成と検証

**Session/Client IDの生成**:
```python
# packages/oiduna_models/id_generator.py
import secrets

def generate_session_id() -> str:
    """8桁hexadecimal Session IDを生成"""
    return secrets.token_hex(4)  # 4 bytes = 8 hex chars

def generate_client_id() -> str:
    """4桁hexadecimal Client IDを生成"""
    return secrets.token_hex(2)  # 2 bytes = 4 hex chars
```

**Track/Pattern IDの検証**:
```python
# packages/oiduna_models/track.py
from pydantic import BaseModel, field_validator

class Track(BaseModel):
    track_id: str

    @field_validator("track_id")
    def validate_track_id(cls, v: str) -> str:
        if not (len(v) == 4 and v.isalnum()):
            raise ValueError("track_id must be 4-character alphanumeric")
        return v.lower()
```

### 命名規則

**変数名**:
- Session ID: `session_id`（snake_case、ID suffix付き）
- Client ID: `client_id`
- Track ID: `track_id`
- Pattern ID: `pattern_id`
- Destination ID: `destination_id`

**悪い例**:
- `session` （IDなのか、Sessionオブジェクトなのか不明）
- `trackId` （camelCaseはPython規約違反）
- `track_identifier` （冗長、`track_id`で十分）

---

## パラメータ命名規則

### SuperDirt向けパラメータ

SuperDirtパラメータは**snake_case**を使用します（APIレベル）。OSC送信時には**camelCase**に変換されます。

**基本パラメータ**:
```python
{
    "s": "bd",           # サウンド名（sound）
    "n": 0,              # サンプル番号（number）
    "gain": 0.8,         # ゲイン
    "pan": 0.5,          # パン（左右定位）
    "speed": 1.0,        # 再生速度
    "orbit": 0           # オービット番号
}
```

**エフェクトパラメータ**:
```python
{
    "room": 0.3,         # リバーブセンド
    "size": 0.8,         # リバーブサイズ
    "delay_send": 0.2,   # ディレイセンド（snake_case）
    "delay_time": 0.5,   # ディレイタイム
    "cutoff": 1000,      # フィルターカットオフ
    "resonance": 0.3     # フィルターレゾナンス
}
```

**変換例**:
```python
# API → OSC変換
api_params = {"delay_send": 0.2, "delay_time": 0.5}
osc_params = {"delaySend": 0.2, "delayTime": 0.5}  # camelCase
```

### MIDI向けパラメータ

MIDI標準用語を使用します。

```python
{
    "note": 60,          # MIDIノート番号（0-127、60=C4）
    "velocity": 100,     # ベロシティ（0-127）
    "duration_ms": 250,  # ノート長（ミリ秒）
    "channel": 0,        # MIDIチャンネル（0-15）
    "cc": 74,            # CCナンバー（Control Change）
    "value": 64,         # CC値（0-127）
    "pitch_bend": 0      # ピッチベンド（-8192〜8191）
}
```

### カスタムパラメータ

拡張機能で独自パラメータを定義する場合：
- **Prefix付き**: `custom_param_name`（衝突防止）
- **snake_case**: Python標準に従う
- **ドキュメント化**: 必ずREADMEに記載

---

## 型定義方針

### Pydantic Models（ドメインモデル）

**Layer 1（階層モデル）**では、Pydanticを使用してバリデーション付きモデルを定義します。

```python
from pydantic import BaseModel, field_validator

class Track(BaseModel):
    """Track represents a single audio track with destination routing."""
    track_id: str
    track_name: str
    destination_id: str
    base_params: dict[str, Any] = {}
    patterns: list[Pattern] = []

    @field_validator("track_id")
    def validate_track_id(cls, v: str) -> str:
        if not (len(v) == 4 and v.isalnum()):
            raise ValueError("track_id must be 4-character alphanumeric")
        return v.lower()
```

**Pydantic使用ルール**:
- `BaseModel`を継承
- `field_validator`でカスタムバリデーション
- `model_validate()`でJSON→モデル変換
- docstringで目的を明記

### Protocol（インターフェース定義）

**疎結合**が必要な箇所ではProtocolを使用します。

```python
from typing import Protocol

class CommandProducer(Protocol):
    """Protocol for sending commands from API to Loop Engine."""

    def send_command(self, command: Command) -> None:
        """Send a command to the loop engine.

        Args:
            command: The command to send (Play, Stop, Compile, etc.)
        """
        ...

class CommandConsumer(Protocol):
    """Protocol for receiving commands in Loop Engine."""

    def receive_command(self) -> Command | None:
        """Receive a command from the API.

        Returns:
            Command if available, None otherwise.
        """
        ...
```

**Protocol使用ルール**:
- IPC通信、拡張ポイントで使用
- メソッドシグネチャのみ定義（実装は`...`）
- docstringで役割を明記
- 実装クラスは明示的に継承不要（Structural Subtyping）

### dataclass（不変データ）

**Layer 2-3（メッセージフォーマット、スケジューリング）**では、immutableなdataclassを使用します。

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class ScheduleEntry:
    """A single scheduled message to be sent to a destination.

    Attributes:
        destination_id: Target destination identifier
        cycle: Timing in cycles (0.0-4.0)
        step: Quantized step number (0-255)
        params: Destination-specific parameters
    """
    destination_id: str
    cycle: float
    step: int
    params: dict[str, Any]
```

**dataclass使用ルール**:
- `frozen=True`: 不変性を保証（ハッシュ可能、スレッドセーフ）
- `slots=True`: メモリ効率向上（-40%）
- tupleでラップ: `entries: tuple[ScheduleEntry, ...]`（固定長配列）

### NewType（型レベルの区別）

**混同を防ぐ**ために、NewTypeで型を区別します。

```python
from oiduna_models.timing import StepNumber, BeatNumber, CycleFloat, BPM

# Example usage
def get_messages_for_step(step: StepNumber) -> list[ScheduleEntry]:
    ...

# Type error if passing wrong type
beat: BeatNumber = BeatNumber(4)
get_messages_for_step(beat)  # mypy error!
```

**実装状況**:
- ✅ **実装済み**: `packages/oiduna_models/timing.py`にタイミング型を定義
- ✅ **利用可能な型**:
  - `StepNumber` - Step番号 (0-255)
  - `BeatNumber` - Beat番号 (0-15)
  - `BarNumber` - Bar番号 (0-3)
  - `CycleFloat` - Cycle位置 (0.0-4.0)
  - `BPM` - Beats per minute (20-999)
  - `Milliseconds` - ミリ秒単位の時間

**NewType使用ルール**:
- タイミング単位（Step/Beat/Bar/Cycle）で必須
- ID型（SessionID、ClientID等）は将来実装予定
- mypy strictモードで型エラー検出
- ランタイムコストなし（型ヒントのみ）

**変換ユーティリティ**:
```python
from oiduna_models.timing import step_to_cycle, cycle_to_step, bpm_to_step_duration_ms

# Step ↔ Cycle変換
cycle = step_to_cycle(StepNumber(64))  # CycleFloat(1.0)
step = cycle_to_step(CycleFloat(2.0))  # StepNumber(128)

# BPM → 時間変換
duration_ms = bpm_to_step_duration_ms(BPM(120))  # Milliseconds(125)
```

### TypedDict（Destination Parameters）

**paramsの型安全性向上**のために、TypedDictを使用します。

```python
from oiduna_models.params import SuperDirtParams, MidiParams, DestinationParams

# SuperDirt parameters with autocomplete
kick_params: SuperDirtParams = {
    "s": "bd",
    "gain": 0.8,
    "pan": 0.5,
    "room": 0.1,
    "orbit": 0,
}

# MIDI parameters with autocomplete
note_params: MidiParams = {
    "note": 60,
    "velocity": 100,
    "duration_ms": 250,
    "channel": 0,
}

# Custom destination parameters
custom_params: DestinationParams = {
    "custom_param": "value",
}
```

**実装状況**:
- ✅ **実装済み**: `packages/oiduna_models/params.py`にパラメータ型を定義
- ✅ **利用可能な型**:
  - `SuperDirtParams` - SuperDirt/TidalCycles用パラメータ（80+ fields）
  - `MidiParams` - MIDI用パラメータ（Note On, CC, Pitch Bend等）
  - `DestinationParams` - Union型（SuperDirt | MIDI | カスタム）

**TypedDict使用ルール**:
- `total=False`: 全フィールド省略可能（柔軟なパラメータ組み合わせ）
- エディタ補完で開発効率向上
- ドキュメント的価値（型ヒントで仕様明示）
- 完全な型安全性は不可（dict互換性のため、ランタイムチェックなし）

**使用例**:
```python
# Function parameter type annotation
def create_pattern(params: SuperDirtParams) -> Pattern:
    ...

# Variable type annotation (editor autocomplete)
hihat: SuperDirtParams = {
    "s": "hh",
    "cutoff": 8000,  # Autocomplete suggests available fields
    "resonance": 0.3,
}
```

---

## モジュール構成原則

### パッケージ構造

```
packages/
├── oiduna_models/          # Layer 1: Pydantic models（データバリデーション）
├── oiduna_scheduler/       # Layer 2-3: Message scheduling & routing
├── oiduna_session/         # Session management (SessionContainer + Managers)
├── oiduna_loop/            # Loop Engine（リアルタイム再生）
├── oiduna_api/             # FastAPI routes（HTTP interface）
├── oiduna_auth/            # Authentication（トークン認証）
├── oiduna_timeline/        # Timeline management（Phase 5）
├── oiduna_cli/             # CLI tools
└── oiduna_client/          # HTTP client library
```

### 依存方向ルール

**単方向依存**を維持してください。循環依存は厳禁です。

```
API → Session → Models
API → Loop → Scheduler → Models
      └─────────────────→
```

**ルール**:
- Layer 1（models）は他に依存しない（最下層）
- Layer 2-3（scheduler）はmodelsのみに依存
- Layer 4（loop、api）は上位層に依存可能
- 同一Layer内の循環依存は避ける

**例**:
```python
# ✅ OK: Higher layer → Lower layer
from oiduna_models import Track, Pattern
from oiduna_scheduler import LoopScheduler

# ❌ NG: Lower layer → Higher layer
# oiduna_models内で oiduna_api をimportしてはいけない
```

### 単一責任原則（SRP）

各パッケージ・モジュールは**単一の責任**のみを持ちます。

| パッケージ | 責任 | 禁止事項 |
|-----------|------|---------|
| oiduna_models | データバリデーションのみ | ビジネスロジック、HTTP処理 |
| oiduna_scheduler | メッセージスケジューリング・ルーティング | OSC/MIDI送信、HTTP処理 |
| oiduna_session | CRUD操作、状態管理 | HTTP処理、ループ再生 |
| oiduna_loop | リアルタイムループ再生 | HTTP処理、CRUD操作 |
| oiduna_api | HTTP interface | ビジネスロジック、ループ再生 |

**悪い例**:
```python
# ❌ NG: oiduna_models内でHTTP処理
class Track(BaseModel):
    def save_to_api(self):  # models層でAPI呼び出しは違反
        requests.post("/api/tracks", ...)
```

**良い例**:
```python
# ✅ OK: 責任を分離
class Track(BaseModel):
    # データバリデーションのみ
    pass

class TrackManager:
    def create(self, track: Track) -> Track:
        # CRUD操作（session層の責任）
        ...
```

---

## ドキュメントルール

### Docstring形式

**Google Style Docstrings**を使用します。

```python
def get_messages_for_step(self, step: int) -> list[ScheduleEntry]:
    """Get all messages scheduled for a specific step.

    Args:
        step: The step number (0-255).

    Returns:
        List of ScheduleEntry objects for this step.
        Empty list if no messages are scheduled.

    Raises:
        ValueError: If step is out of range (< 0 or > 255).

    Example:
        >>> scheduler = LoopScheduler()
        >>> scheduler.load_messages(batch)
        >>> messages = scheduler.get_messages_for_step(0)
        >>> len(messages)
        3
    """
    if not 0 <= step < 256:
        raise ValueError(f"Step must be 0-255, got {step}")
    return [self._messages[i] for i in self._step_index.get(step, [])]
```

**Docstring必須箇所**:
- すべてのpublic関数・メソッド
- すべてのクラス
- すべてのモジュール（ファイル先頭）

**Docstring省略可能**:
- プライベートメソッド（`_method`）
- 自明な処理（getter/setterなど）

### コメントルール

**コメントは「なぜ」を説明**してください。「何を」はコードで明らか。

**悪い例**:
```python
# ステップ0のメッセージを取得
messages = scheduler.get_messages_for_step(0)
```

**良い例**:
```python
# ループ開始時のキックドラムを確実に送信するため、ステップ0を取得
messages = scheduler.get_messages_for_step(0)
```

**コメント必須箇所**:
- 複雑なアルゴリズム（O(1)検索の理由など）
- パフォーマンス最適化（早期リターンの理由など）
- 制約・制限（256ステップ固定の理由など）
- バグ回避（ワークアラウンド）

### 型ヒント必須

**すべてのpublic関数**に型ヒントを付けてください。

```python
# ✅ OK
def create_track(self, track_id: str, name: str) -> Track:
    ...

# ❌ NG: 型ヒントなし
def create_track(self, track_id, name):
    ...
```

**mypy strictモード**を通過すること:
```bash
uv run mypy packages/oiduna_models --strict
```

---

## パフォーマンスガイドライン

### リアルタイム制約を意識

**120 BPM = 125ms/step**の制約を常に意識してください。

**ルール**:
- ループ内で重い処理（ファイルI/O、HTTP通信）を行わない
- O(1)またはO(log N)のアルゴリズムを選択
- 早期リターンでムダな処理を省略

**良い例**:
```python
def filter_messages(self, entries: list[ScheduleEntry]) -> list[ScheduleEntry]:
    # 早期リターン: Mute/Solo未設定時は即座にreturn
    if not self._track_mute and not self._track_solo:
        return messages  # コピーなし、高速

    # フィルタリング（必要な場合のみ）
    return [msg for msg in messages if self.is_track_active(msg.params.get("track_id"))]
```

### Immutable設計でメモリ最適化

**frozen=True, slots=True**でメモリ使用量を削減します。

```python
@dataclass(frozen=True, slots=True)
class ScheduleEntry:
    destination_id: str
    cycle: float
    step: int
    params: dict[str, Any]
```

**効果**:
- `frozen=True`: オブジェクト変更不可（ハッシュ可能、スレッドセーフ）
- `slots=True`: `__dict__`なし、メモリ使用量 -40%

### リスト内包表記を活用

**リスト内包表記**はCレベルで最適化されています。

```python
# ✅ OK: リスト内包表記（高速）
messages = [self._messages[i] for i in self._step_index[step]]

# ❌ NG: forループ（遅い）
messages = []
for i in self._step_index[step]:
    messages.append(self._messages[i])
```

---

## まとめ

このコーディング規約は、Oidunaプロジェクトの**一貫性**と**品質**を保つためのガイドラインです。

**重要な原則**:
1. **PEP 8準拠**: Python標準スタイルに従う
2. **対の概念は対応する名前**: Producer↔Consumer、Send↔Receive
3. **ID形式の統一**: 8桁/4桁hexadecimal、英数字+記号
4. **型安全性**: Pydantic、Protocol、NewType、TypedDictを活用
5. **単一責任原則**: 各モジュールは単一の責任のみ
6. **リアルタイム制約**: 125ms/stepを意識した実装

**参考ドキュメント**:
- [TERMINOLOGY.md](TERMINOLOGY.md) - 用語集
- [OIDUNA_CONCEPTS.md](OIDUNA_CONCEPTS.md) - 設計哲学
- [ARCHITECTURE.md](ARCHITECTURE.md) - アーキテクチャ全体
- [DATA_MODEL_REFERENCE.md](DATA_MODEL_REFERENCE.md) - データモデル詳細

---

**バージョン**: 1.0.0
**作成日**: 2026-03-11
**メンテナンス**: 規約変更時はこのファイルを更新
