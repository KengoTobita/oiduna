# Layer 5: データ層 (Foundation) - Data Models & Configuration

**パッケージ**: `oiduna_models`

**最終更新**: 2026-03-01

---

## 概要

データ層はOidunaアーキテクチャの**Foundation（基盤）**であり、すべての層が依存するデータ構造の定義とバリデーションを担当します。

### "Foundation"としてのLayer 5

Layer 5は他の層への「データフロー」ではなく、システム全体を支える**基盤**として機能します:

- ✅ すべての層がこの層のモデルを使用
- ✅ 他のどの層にも依存しない（最下層）
- ✅ ビジネスロジックを含まない（純粋なデータ定義）
- ✅ 言語非依存な設計（JSON Schema生成可能）

この"Foundation"概念により、データモデルは単なる「通過点」ではなく、アーキテクチャ全体の**土台**として位置づけられます。

### 責任

- ✅ ビジネスドメインのデータ構造定義
- ✅ Pydanticによる型安全性とバリデーション
- ✅ JSONシリアライズ・デシリアライズ
- ✅ デスティネーション設定の管理（OSC/MIDI）
- ❌ ビジネスロジック（Layer 2に任せる）
- ❌ データの永続化（将来的にDBレイヤーが担当）

### 依存関係

```
oiduna_models → なし（完全に独立）
```

**設計原則**: データ層は他のどの層にも依存しない（最下層・Foundation）

---

## パッケージ構成

### oiduna_models

**ディレクトリ構造**:
```
oiduna_models/
├── __init__.py            # 主要モデルのエクスポート
├── session.py             # Session
├── track.py               # Track
├── pattern.py             # Pattern
├── events.py              # Event
├── client.py              # ClientInfo
├── environment.py         # Environment
├── id_generator.py        # IDGenerator
├── destination_models.py  # OSC/MIDI送信先設定
└── loader.py              # YAML設定読み込み
```

**主要モデル**:

#### 1. Session
セッション全体の状態を保持する最上位モデル。

```python
class Session(BaseModel):
    """セッション全体の状態"""
    environment: Environment = Field(default_factory=Environment)
    destinations: dict[str, OscDestinationConfig | MidiDestinationConfig] = {}
    clients: dict[str, ClientInfo] = {}
    tracks: dict[str, Track] = {}
```

**役割**:
- すべてのクライアント、トラック、デスティネーションを一元管理
- SessionContainerがこのモデルを操作

**JSONシリアライズ例**:
```json
{
  "environment": {"bpm": 120.0, "metadata": {}},
  "destinations": {
    "superdirt": {
      "id": "superdirt",
      "type": "osc",
      "host": "127.0.0.1",
      "port": 57120,
      "address": "/dirt/play"
    }
  },
  "clients": {
    "alice": {
      "client_id": "alice",
      "client_name": "Alice",
      "token": "uuid-here",
      "distribution": "mars"
    }
  },
  "tracks": {}
}
```

#### 2. Track
送信先とパラメータを持つトラック。

```python
class Track(BaseModel):
    """トラック（送信先とパラメータ）"""
    track_id: str
    track_name: str
    destination_id: str  # destinationへの参照
    client_id: str       # クライアントへの参照
    base_params: dict[str, Any] = {}
    patterns: dict[str, Pattern] = {}

    @field_validator("destination_id")
    @classmethod
    def validate_destination_id(cls, v: str) -> str:
        """destination_idは英数字、アンダースコア、ハイフンのみ"""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError(
                f"destination_id must be alphanumeric with underscores/hyphens. "
                f"Got: '{v}'. Valid examples: 'superdirt', 'midi_1', 'osc-synth'"
            )
        return v
```

**バリデーション**:
- `destination_id`: 英数字、`_`, `-` のみ許可
- スペースや特殊文字は即座にエラー

**使用例**:
```python
# OK
track = Track(
    track_id="kick",
    track_name="Kick Drum",
    destination_id="superdirt",
    client_id="alice"
)

# NG: ValidationError
track = Track(
    track_id="kick",
    track_name="Kick",
    destination_id="super dirt",  # スペースはNG
    client_id="alice"
)
```

#### 3. Pattern
イベントのシーケンス。

```python
class Pattern(BaseModel):
    """パターン（イベントのシーケンス）"""
    pattern_id: str
    pattern_name: str
    client_id: str
    active: bool = True
    events: list[Event] = []
```

**重要なフィールド**:
- `active`: True/Falseでパターンのオン/オフを切り替え
- `events`: イベントのリスト（空リストも許可）

#### 4. Event
単一のトリガーイベント。

```python
class Event(BaseModel):
    """単一トリガーイベント"""
    step: Annotated[int, Field(ge=0, le=255)]
    cycle: Annotated[float, Field(ge=0.0)]
    params: dict[str, Any]
```

**バリデーション**:
```python
# OK
event = Event(step=0, cycle=0.0, params={"sound": "bd"})
event = Event(step=255, cycle=4.0, params={})

# NG: ValidationError
event = Event(step=-1, cycle=0.0, params={})   # step < 0
event = Event(step=256, cycle=0.0, params={})  # step > 255
event = Event(step=0, cycle=-1.0, params={})   # cycle < 0
```

**設計判断**:
- `step`: 0-255の固定範囲（256ステップループ）
- `cycle`: 0以上の任意の値（柔軟性）
- `params`: 任意の辞書（送信先依存）

#### 5. ClientInfo
接続クライアント情報。

```python
class ClientInfo(BaseModel):
    """クライアント情報"""
    client_id: str
    client_name: str
    token: str
    distribution: str = "unknown"
    metadata: dict[str, Any] = {}

    @staticmethod
    def generate_token() -> str:
        """UUID v4トークン生成"""
        return str(uuid.uuid4())
```

**トークン生成**:
```python
token = ClientInfo.generate_token()
# → "550e8400-e29b-41d4-a716-446655440000"

client = ClientInfo(
    client_id="alice",
    client_name="Alice",
    token=token,
    distribution="mars"
)
```

#### 6. Environment
BPM等の環境設定。

```python
class Environment(BaseModel):
    """環境設定（BPM等）"""
    bpm: Annotated[float, Field(ge=20.0, le=999.0)] = 120.0
    metadata: dict[str, Any] = {}
    initial_metadata: dict[str, Any] = {}
```

**バリデーション**:
```python
# OK
env = Environment(bpm=120.0)
env = Environment(bpm=20.0)   # 最小値
env = Environment(bpm=999.0)  # 最大値

# NG: ValidationError
env = Environment(bpm=10.0)   # < 20
env = Environment(bpm=1000.0) # > 999
```

#### 7. IDGenerator
ID生成ユーティリティ。

```python
class IDGenerator:
    """ID生成器（track_001, pattern_001等）"""
    def __init__(self):
        self._track_counter = 0
        self._pattern_counter = 0

    def next_track_id(self) -> str:
        self._track_counter += 1
        return f"track_{self._track_counter:03d}"

    def next_pattern_id(self) -> str:
        self._pattern_counter += 1
        return f"pattern_{self._pattern_counter:03d}"

    def reset(self) -> None:
        self._track_counter = 0
        self._pattern_counter = 0
```

**使用例**:
```python
gen = IDGenerator()
gen.next_track_id()    # → "track_001"
gen.next_track_id()    # → "track_002"
gen.next_pattern_id()  # → "pattern_001"
```

#### 8. DestinationConfig（統合）

OSC/MIDI送信先の設定モデル。

**OscDestinationConfig**:
```python
class OscDestinationConfig(BaseModel):
    """OSC送信先設定"""
    id: str
    type: Literal["osc"] = "osc"
    host: str
    port: int
    address: str
```

**使用例**:
```python
superdirt = OscDestinationConfig(
    id="superdirt",
    type="osc",
    host="127.0.0.1",
    port=57120,
    address="/dirt/play"
)
```

**MidiDestinationConfig**:
```python
class MidiDestinationConfig(BaseModel):
    """MIDI送信先設定"""
    id: str
    type: Literal["midi"] = "midi"
    port_name: str
    channel: int = 1
```

**使用例**:
```python
volca = MidiDestinationConfig(
    id="volca",
    type="midi",
    port_name="Volca Keys",
    channel=1
)
```

**Union型**:
```python
DestinationConfig = Union[OscDestinationConfig, MidiDestinationConfig]
```

**YAML設定例**:
```yaml
destinations:
  superdirt:
    id: superdirt
    type: osc
    host: 127.0.0.1
    port: 57120
    address: /dirt/play
  volca:
    id: volca
    type: midi
    port_name: "Volca Keys"
    channel: 1
```

#### 9. Destination Loader

YAML/JSONファイルから設定を読み込むユーティリティ。

```python
from oiduna_models import load_destinations, load_destinations_from_file

# ファイルから読み込み
destinations = load_destinations_from_file("destinations.yaml")

# 辞書から読み込み
config = {
    "destinations": {
        "superdirt": {
            "id": "superdirt",
            "type": "osc",
            "host": "127.0.0.1",
            "port": 57120,
            "address": "/dirt/play"
        }
    }
}
destinations = load_destinations(config)
```

## Pydanticバリデーションの利点

### 1. 型安全性

```python
# 型エラーは即座に検出
event = Event(step="invalid", cycle=0.0, params={})
# → ValidationError: Input should be a valid integer
```

### 2. 範囲チェック

```python
# 範囲外の値は即座にエラー
event = Event(step=300, cycle=0.0, params={})
# → ValidationError: Input should be less than or equal to 255
```

### 3. カスタムバリデーション

```python
# destination_idのフォーマットチェック
track = Track(
    track_id="t1",
    track_name="kick",
    destination_id="super dirt!",  # 特殊文字
    client_id="c1"
)
# → ValueError: destination_id must be alphanumeric...
```

### 4. 自動ドキュメント生成

Pydanticモデルは自動的にJSON Schemaを生成できます。

```python
print(Event.model_json_schema())
```

出力:
```json
{
  "properties": {
    "step": {
      "type": "integer",
      "minimum": 0,
      "maximum": 255
    },
    "cycle": {
      "type": "number",
      "minimum": 0.0
    },
    "params": {
      "type": "object"
    }
  },
  "required": ["step", "cycle", "params"]
}
```

---

## JSONシリアライズ・デシリアライズ

### シリアライズ（Python → JSON）

```python
track = Track(
    track_id="kick",
    track_name="Kick Drum",
    destination_id="superdirt",
    client_id="alice",
    base_params={"sound": "bd", "orbit": 0}
)

# dict化
track_dict = track.model_dump()

# JSON文字列化
track_json = track.model_dump_json()
```

### デシリアライズ（JSON → Python）

```python
# dictから
track_dict = {
    "track_id": "kick",
    "track_name": "Kick",
    "destination_id": "superdirt",
    "client_id": "alice"
}
track = Track(**track_dict)

# JSON文字列から
track_json = '{"track_id": "kick", ...}'
track = Track.model_validate_json(track_json)
```

---

## Rust移植の考慮事項

### 優先度: 最優先 🔥

データ層は最優先でRust移植すべき理由：

1. **言語間共有が容易**: データ構造は言語非依存
2. **他の層の基盤**: すべての層がこれに依存
3. **段階的移植**: まずデータ構造から始められる

### Rust実装の方針

```rust
// oiduna_models (Rust版)
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Event {
    pub step: u8,           // 0-255
    pub cycle: f64,         // >= 0.0
    pub params: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Track {
    pub track_id: String,
    pub track_name: String,
    pub destination_id: String,
    pub client_id: String,
    pub base_params: HashMap<String, serde_json::Value>,
    pub patterns: HashMap<String, Pattern>,
}
```

### Python-Rust相互運用

**PyO3での公開**:
```rust
use pyo3::prelude::*;

#[pyclass]
#[derive(Clone)]
pub struct Event {
    #[pyo3(get, set)]
    pub step: u8,
    #[pyo3(get, set)]
    pub cycle: f64,
    // ...
}

#[pymethods]
impl Event {
    #[new]
    fn new(step: u8, cycle: f64, params: HashMap<String, PyObject>) -> Self {
        // ...
    }
}
```

### JSON互換性の維持

PythonのPydanticとRustのserdeで同じJSON形式を扱う：

```json
// Python Pydantic → JSON ← Rust serde
{
  "track_id": "kick",
  "track_name": "Kick",
  "destination_id": "superdirt",
  "client_id": "alice",
  "base_params": {"sound": "bd"},
  "patterns": {}
}
```

---

## テスト例

### ユニットテスト（test_models.py）

```python
def test_event_step_validation():
    """stepは0-255の範囲内"""
    # OK
    Event(step=0, cycle=0.0, params={})
    Event(step=255, cycle=0.0, params={})

    # NG
    with pytest.raises(ValidationError):
        Event(step=-1, cycle=0.0, params={})
    with pytest.raises(ValidationError):
        Event(step=256, cycle=0.0, params={})

def test_track_destination_id_format():
    """destination_idは英数字、_、-のみ"""
    # OK
    Track(track_id="t1", track_name="kick",
          destination_id="superdirt", client_id="c1")
    Track(track_id="t2", track_name="snare",
          destination_id="super_dirt", client_id="c1")

    # NG
    with pytest.raises(ValueError, match="alphanumeric"):
        Track(track_id="t3", track_name="hat",
              destination_id="super dirt", client_id="c1")
```

---

## まとめ

### データ層の重要性

1. **型安全性の基盤**: すべてのデータがバリデーション済み
2. **Silent Failure防止**: 不正なデータは即座にエラー
3. **ドキュメントとしての型**: Pydanticモデルが仕様書
4. **Rust移植の出発点**: まずデータ構造から

### 設計判断

- **Pydantic採用**: 型安全性とバリデーション
- **immutable優先**: dataclass(frozen=True)を検討（現在はBaseModel）
- **送信先非依存**: `params: dict[str, Any]`で柔軟性確保

### 次のステップ

データ層を理解したら：
1. [Layer 4: ドメイン層](./layer-4-domain.md)でメッセージ最適化を学ぶ
2. [Layer 2: アプリケーション層](./layer-2-application.md)でビジネスロジックを理解
3. [Layer 3: コア層](./layer-3-core.md)で実行エンジンを理解
4. [データフロー例](./data-flow-examples.md)で実際の使用例を確認

---

**関連ドキュメント**:
- `packages/oiduna_models/README.md`
- ADR-0012: Package Architecture
- ADR-0014: oiduna_destination Merge into oiduna_models
