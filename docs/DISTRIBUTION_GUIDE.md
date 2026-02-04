# Oiduna Distribution ガイド

**対象**: Oidunaを使うDistribution開発者・分離エージェント
**参照**: `docs/SPECIFICATION_v1.md`（設計仕様）

---

## 目次

1. [全体像](#全体像)
2. [Oidunaの入口と出口](#oidunaの入口と出口)
3. [IRデータモデル（実装実体）](#irデータモデル実装実体)
4. [APIとの連携方法](#apiとの連携方法)
5. [MARSからの分離マッピング](#mARSからの分離マッピング)
6. [コード再利用と移動対象](#コード再利用と移動対象)

---

## 全体像

```
┌─────────────────────────────────────────────────────────────────┐
│                        Oiduna Core                              │
│                                                                 │
│  HTTP API (FastAPI)                                             │
│    POST /playback/pattern   ← CompiledSession (JSON)            │
│    POST /playback/start                                         │
│    POST /playback/stop                                          │
│    POST /playback/pause                                         │
│    GET  /playback/status                                        │
│    GET  /stream             → SSE (position, state, tracks)     │
│                                                                 │
│  LoopEngine (asyncio, 5タスク)                                  │
│    step_loop    → StepProcessor → OscSender (SuperDirt OSC)     │
│    clock_loop   → ClockGenerator → MidiSender (24PPQ clock)     │
│    note_off_loop → NoteScheduler → MidiSender (note_off)        │
│    command_loop → コマンド処理                                   │
│    heartbeat_loop → 接続監視                                    │
│                                                                 │
│  出力                                                           │
│    OSC  → SuperDirt (/dirt/play @ 127.0.0.1:57120)              │
│    MIDI → ノート, CC, PitchBend, Aftertouch, クロック, トランスポート │
└─────────────────────────────────────────────────────────────────┘
         ▲
         │ HTTP POST (JSON)
         │
┌────────┴────────────────────────────────────────────────────────┐
│                      Distribution                               │
│  例: MARS_for_oiduna                                            │
│                                                                 │
│    DSL ──→ パース ──→ コンパイル ──→ CompiledSession.to_dict() │
│                                        │                        │
│                                        ▼                        │
│                                  JSON → POST /playback/pattern  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Oidunaの入口と出口

### 入口（Distribution側から送る）

| エンドポイント | メソッド | 何を送るか |
|---------------|---------|-----------|
| `/playback/pattern` | POST | `CompiledSession.to_dict()` のJSON |
| `/playback/start` | POST | なし |
| `/playback/stop` | POST | なし |
| `/playback/pause` | POST | なし |

**コア入口は1つだけ**: `POST /playback/pattern`に`CompiledSession`のJSON辞書を送る。

### 出口（Oidunaが出す）

| 出力先 | プロトコル | 内容 |
|--------|-----------|------|
| SuperDirt | OSC UDP `/dirt/play` | サウンド再生命令 |
| 外部MIDI機器 | MIDI | ノート, CC, PB, AT, クロック |
| クライアント | SSE | position, state, tracks イベント |

### 現実装のAPI（playback.py:52〜178）

```python
POST /playback/start    → engine.start()
POST /playback/stop     → engine.stop()
POST /playback/pause    → engine.pause()
POST /playback/pattern  → CompiledSession.from_dict(body) → engine.load_session()
GET  /playback/status   → step, beat, bar, bpm, tracks情報
GET  /stream            → SSE (現時点はstub、エンジン未接続)
```

---

## IRデータモデル（実装実体）

以下がDistributionが生成すべき実際のPythonデータモデルです。
全てに `to_dict()` / `from_dict()` を持ちJSON往復可能。

### トップレベル: CompiledSession

```python
# oiduna_core/models/ir/session.py

@dataclass
class CompiledSession:
    environment: Environment                    # Layer 1: グローバル設定
    tracks:      dict[str, Track]               # Layer 2: SuperDirtトラック
    tracks_midi: dict[str, TrackMidi]           # Layer 2: MIDIトラック
    mixer_lines: dict[str, MixerLine]           # ミキサーバス
    sequences:   dict[str, EventSequence]       # Layer 3: パターン
    scenes:      dict[str, Scene]               # シーン定義
    apply:       ApplyCommand | None            # 適用タイミング
```

**キー**: `tracks`, `sequences` のキーは同じtrack_idで対応する。

### Layer 1: Environment

```python
# oiduna_core/models/ir/environment.py

@dataclass
class Environment:
    bpm:           float       = 120.0
    scale:         str         = "C_major"   # v1.1で削除予定
    default_gate:  float       = 1.0
    swing:         float       = 0.0
    loop_steps:    int         = 256         # 固定、変更不可
    chords:        list[Chord] = []          # v1.1で削除予定

@dataclass
class Chord:
    name:   str
    length: int | None = None   # Noneは等分割
```

### Layer 2: Track (SuperDirt)

```python
# oiduna_core/models/ir/track.py

@dataclass
class Track:
    meta:          TrackMeta
    params:        TrackParams
    fx:            FxParams          # 旧インターフェース
    track_fx:      TrackFxParams     # v5: トーン調整エフェクト
    sends:         tuple[Send, ...]  # MixerLineへのルーティング
    modulations:   dict[str, Modulation]

@dataclass
class TrackMeta:
    track_id:  str
    range_id:  int  = 2
    mute:      bool = False
    solo:      bool = False

@dataclass
class TrackParams:
    s:             str              # サウンド名 (例: "super808", "bd")
    s_path:        str    = ""      # 階層パス (例: "synthdef.drum.super808")
    n:             int    = 0       # サンプル番号
    gain:          float  = 1.0
    pan:           float  = 0.5
    speed:         float  = 1.0
    begin:         float  = 0.0
    end:           float  = 1.0
    orbit:         int    = 0       # SuperDirt オビット
    cut:           int | None
    legato:        float | None
    extra_params:  dict[str, Any]   # SynthDef固有パラメータ
```

### Layer 2: TrackMidi

```python
# oiduna_core/models/ir/track_midi.py

@dataclass
class TrackMidi:
    track_id:                str
    channel:                 int              # 0-15
    velocity:                int    = 127
    transpose:               int    = 0       # 半音単位
    mute:                    bool   = False
    solo:                    bool   = False
    cc_modulations:          dict[int, Modulation]   # CC番号 → モジュレーション
    pitch_bend_modulation:   Modulation | None
    aftertouch_modulation:   Modulation | None
    velocity_modulation:     Modulation | None
```

### Layer 3: EventSequence

```python
# oiduna_core/models/ir/sequence.py

@dataclass(frozen=True, slots=True)
class Event:
    step:      int              # 0-255
    velocity:  float  = 1.0    # 0.0-1.0
    note:      int | None      # MIDIノート番号
    gate:      float  = 1.0    # ゲート長比率

@dataclass
class EventSequence:
    track_id:    str
    _events:     tuple[Event, ...]
    _step_index: dict[int, list[int]]   # O(1)検索インデックス
```

### MixerLine

```python
# oiduna_core/models/ir/mixer_line.py

@dataclass(frozen=True)
class MixerLine:
    name:      str
    include:   tuple[str, ...]     # トラック名リスト
    volume:    float = 1.0
    pan:       float = 0.5
    mute:      bool  = False
    solo:      bool  = False
    output:    int   = 0           # 物理出力チャンネル
    dynamics:  MixerLineDynamics   # リミター・コンパレッサー
    fx:        MixerLineFx         # リバーブ・デレイ・レスリー

# シグナルフロー:
# Track Sound → TrackFx → MixerLine Dynamics → MixerLine Fx → 出力
```

### Scene

```python
# oiduna_core/models/ir/scene.py

@dataclass
class Scene:
    name:          str
    environment:   Environment | None
    tracks:        dict[str, Track]
    tracks_midi:   dict[str, TrackMidi]
    sequences:     dict[str, EventSequence]
```

### ApplyCommand

```python
# oiduna_core/models/ir/session.py

ApplyTiming = Literal["now", "beat", "bar", "seq"]

@dataclass
class ApplyCommand:
    timing:     ApplyTiming          # いつ適用するか
    track_ids:  list[str]            # 対象トラック（空の場合は全トラック）
    scene_name: str | None           # シーン適用時
```

---

## APIとの連携方法

### Distribution側の実装パターン

```python
import httpx
import json

OIDUNA_URL = "http://localhost:8000"

class OidunaClient:
    """Distribution側からOiduna Coreに接続するクライアント"""

    def __init__(self, base_url: str = OIDUNA_URL):
        self.base_url = base_url

    def load_session(self, compiled_session) -> dict:
        """CompiledSessionをOidunaに送信"""
        payload = compiled_session.to_dict()
        resp = httpx.post(f"{self.base_url}/playback/pattern", json=payload)
        resp.raise_for_status()
        return resp.json()

    def start(self) -> dict:
        resp = httpx.post(f"{self.base_url}/playback/start")
        resp.raise_for_status()
        return resp.json()

    def stop(self) -> dict:
        resp = httpx.post(f"{self.base_url}/playback/stop")
        resp.raise_for_status()
        return resp.json()

    def get_status(self) -> dict:
        resp = httpx.get(f"{self.base_url}/playback/status")
        resp.raise_for_status()
        return resp.json()
```

### 最小限のCompiledSession生成例

```python
from oiduna_core.models.ir import (
    CompiledSession, Environment,
    Track, TrackMeta, TrackParams,
    EventSequence, Event,
)

# キック: 1拍ごとに打つ
events = [Event(step=i * 4, velocity=1.0) for i in range(64)]  # 16小節 × 4拍

session = CompiledSession(
    environment=Environment(bpm=120.0),
    tracks={
        "kick": Track(
            meta=TrackMeta(track_id="kick"),
            params=TrackParams(s="bd", orbit=0),
        )
    },
    sequences={
        "kick": EventSequence.from_events("kick", events)
    },
)

# 送信
client = OidunaClient()
client.load_session(session)
client.start()
```

---

## MARSからの分離マッピング

### パッケージレベルの対応

```
Modular_Audio_Real-time_Scripting/
  packages/
    mars_common/     → モデル部分がoiduna_core/models/に移動済み
    dsl/             → MARS_for_oiduna/mars_dsl/ に移動予定
    mars_api/        → MARS_for_oiduna/mars_api/ に移動予定
    mars_loop/       → oiduna_core/engine/ に移動済み
  apps/
    frontend/        → MARS_for_oiduna/ に移動予定

oiduna/
  oiduna_core/       → Oiduna Core（言語非依存プレイヤー）

MARS_for_oiduna/
  mars_dsl/          → MARSのDSLコンパイラ（Distribution側）
  mars_api/          → MARSのAPIサーバー（Distribution側）
```

### ファイルレベルの移動済み対応

| MARS (元) | Oiduna (移動先) | 変更点 |
|-----------|----------------|--------|
| `mars_common/models/session.py` | `models/ir/session.py` | なし |
| `mars_common/models/environment.py` | `models/ir/environment.py` | なし |
| `mars_common/models/track.py` | `models/ir/track.py` | なし |
| `mars_common/models/track_midi.py` | `models/ir/track_midi.py` | なし |
| `mars_common/models/sequence.py` | `models/ir/sequence.py` | なし |
| `mars_common/models/scene.py` | `models/ir/scene.py` | なし |
| `mars_common/models/mixer_line.py` | `models/ir/mixer_line.py` | なし |
| `mars_common/models/output.py` | `models/output/output.py` | なし |
| `mars_loop/engine/loop_engine.py` | `engine/loop_engine.py` | IPC→HTTP |
| `mars_loop/engine/clock_generator.py` | `engine/clock_generator.py` | なし |
| `mars_loop/engine/step_processor.py` | `engine/step_processor.py` | なし |
| `mars_loop/engine/note_scheduler.py` | `engine/note_scheduler.py` | なし |
| `mars_loop/output/osc_sender.py` | `output/osc_sender.py` | なし |
| `mars_loop/output/midi_sender.py` | `output/midi_sender.py` | なし |

### MARSに残る部分（Distribution側の作業）

```
packages/dsl/
  grammar/mars_v5.lark        → DSL文法定義
  schema/sounds.json          → サウンドカタログ
  schema/scales.json          → スケール定義
  transformers/               → パース変換ロジック
  compiler.py                 → AST → CompiledSession
  parser.py                   → Larkパーサー

packages/mars_api/
  routes/                     → エンドポイント
  services/compiler_service   → コンパイル実行
  services/monaco_service     → エディタ補完

apps/frontend/                → Monaco Editor UI
```

### 通信の変化

```
【旧MARS】
mars_api ──ZeroMQ PUB/SUB──→ mars_loop
          (PUB:5556, SUB:5557)

【新Oiduna】
MARS_for_oiduna ──HTTP REST──→ oiduna_core
                (POST /playback/pattern)
```

---

## コード再利用と移動対象

### 移動済み（oiduna_core に既に存在）

- 3層データモデル全体（IR）
- LoopEngine（5タスク構成）
- StepProcessor, ClockGenerator, NoteScheduler
- OscSender, MidiSender
- Output IR（OscEvent, MidiNoteEvent等）

### 移動が必要な部分（MARS_for_oiduna に行く）

- `packages/dsl/` 全体（文法、パーサー、コンパイラー、スキーマ）
- `packages/mars_api/` の API ルート・サービス層
- `apps/frontend/` のMonaco UI
- `packages/mars_common/ipc/` のシリアライザーは不要になる（HTTP+JSONに変わるため）

### 不要になる部分

- `packages/mars_common/ipc/` — ZeroMQ通信（HTTP RESTに置換）
- `packages/mars_loop/ipc/` — ZeroMQ通信
- `packages/mars_api/ipc/` — ZeroMQ通信
- `pyzmq` 依存関係

### oiduna_core の依存関係

```toml
# pyproject.toml
dependencies = [
    "fastapi>=0.112.0",
    "uvicorn>=0.30.0",
    "python-osc>=1.8.3",          # SuperDirt OSC
    "python-rtmidi>=1.5.8",       # MIDI
    "mido>=1.3.0",                # MIDI
    "msgpack>=1.0.0",             # シリアライズ
    "sse-starlette>=2.1.0",       # SSE
]
```

**注意**: `pyzmq` は含まない。Oiduna Core自体にはIPC不要。
