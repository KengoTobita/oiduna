# Oiduna データアーキテクチャ 現状分析

**作成日**: 2026-02-26
**目的**: 現在の2つの並行データアーキテクチャを明確化し、統合と型安全性向上の方針を議論

---

## 現状の問題

Oidunaには**2つの異なるデータアーキテクチャ**が並行して存在しています：

1. **CompiledSession方式**（MARS DSL v5ベース）- 階層構造
2. **ScheduledMessageBatch方式**（新Destination-Based API）- フラット構造

現在、**実際に音を出しているのはScheduledMessageBatch方式のみ**です。

---

## アーキテクチャA: CompiledSession方式（旧MARS互換）

### データフロー

```
POST /playback/pattern (oiduna_api/routes/playback.py:60)
  ↓
CompileCommand validation (Pydantic)
  ↓
RuntimeState.load_compiled_session() (oiduna_loop/state/runtime_state.py:523)
  ↓
CompiledSession stored in RuntimeState
  ↓
❌ ループエンジンでの音出し処理なし（実装途中）
```

### データ構造

```python
@dataclass
class CompiledSession:
    """DSLコンパイル済みセッション（oiduna_core/ir/session.py:55）"""

    environment: Environment              # グローバル設定
    tracks: dict[str, Track]              # トラック定義
    tracks_midi: dict[str, TrackMidi]     # MIDIトラック
    mixer_lines: dict[str, MixerLine]     # ミキサーライン（v5新機能）
    sequences: dict[str, EventSequence]   # パターン（256ステップ）
    scenes: dict[str, Scene]              # シーン
    apply: ApplyCommand | None            # 適用タイミング
```

#### 階層構造の詳細

```python
# Layer 1: Environment（グローバル設定）
@dataclass
class Environment:
    bpm: float = 120.0
    scale: str = "C_major"
    default_gate: float = 1.0
    swing: float = 0.0
    loop_steps: int = 256
    chords: dict[str, list[int]] = field(default_factory=dict)

# Layer 2: Track（トラック定義）
@dataclass
class Track:
    meta: TrackMeta                    # track_id, range_id, mute, solo
    params: TrackParams                # s, n, gain, pan, speed, begin, end, orbit
    fx: FxParams                       # reverb, delay, filter, distortion, etc.
    track_fx: TrackFxParams            # トーンシェイピング系エフェクト
    sends: list[Send]                  # マルチバスルーティング
    modulations: dict[str, Modulation] # パラメータモジュレーション

@dataclass
class TrackParams:
    """サウンドパラメータ（型安全）"""
    s: str                  # サウンド名（例: "bd", "super808"）
    s_path: str = ""        # 階層パス（例: "synthdef.drum.super808"）
    n: int = 0              # サンプル番号
    gain: float = 1.0       # ゲイン
    pan: float = 0.5        # パン
    speed: float = 1.0      # 再生速度
    begin: float = 0.0      # 開始位置
    end: float = 1.0        # 終了位置
    cut: int | None = None  # カットグループ
    legato: float | None = None
    extra_params: dict[str, Any] = field(default_factory=dict)

# Layer 3: EventSequence（パターン）
@dataclass
class EventSequence:
    """256ステップのイベントシーケンス"""
    track_id: str
    _events: tuple[Event, ...]              # イベントリスト
    _step_index: dict[int, list[int]]       # O(1)ルックアップ用インデックス

@dataclass(frozen=True, slots=True)
class Event:
    """単一イベント"""
    step: int                    # 0-255
    velocity: float = 1.0        # 0.0-1.0
    note: int | None = None      # MIDIノート番号
    gate: float = 1.0            # ゲート長
```

### 特徴

✅ **型安全性が高い**: dataclassで明確に定義
✅ **階層構造**: Environment → Track → Sequence の3層
✅ **MARS DSL v5と完全互換**
✅ **Scene/MixerLineなど高度な機能をサポート**

❌ **実装が未完成**: ループエンジンで音を出す処理がない
❌ **RuntimeStateに保存されるだけで使われていない**

---

## アーキテクチャB: ScheduledMessageBatch方式（新API）

### データフロー

```
POST /playback/session (oiduna_api/routes/playback.py:129)
  ↓
SessionRequest validation (Pydantic)
  ↓
ExtensionPipeline.apply() (拡張機能による変換)
  ↓
MessageScheduler.load_messages() (oiduna_scheduler/scheduler.py:38)
  ↓
ステップループで再生 (loop_engine.py:974)
  ↓
DestinationRouter.send_messages() (oiduna_scheduler/router.py:66)
  ↓
✅ OSC/MIDI送信（音が出る）
```

### データ構造

```python
@dataclass(frozen=True)
class ScheduledMessageBatch:
    """スケジュール済みメッセージバッチ（oiduna_scheduler/scheduler_models.py:79）"""

    messages: tuple[ScheduledMessage, ...]  # メッセージリスト
    bpm: float = 120.0                      # テンポ
    pattern_length: float = 4.0             # パターン長（サイクル単位）

@dataclass(frozen=True, slots=True)
class ScheduledMessage:
    """単一スケジュール済みメッセージ（oiduna_scheduler/scheduler_models.py:14）"""

    destination_id: str         # 送信先ID（例: "superdirt", "volca_bass"）
    cycle: float                # サイクル位置（例: 0.0, 0.5, 1.0）
    step: int                   # ステップ番号（0-255）
    params: dict[str, Any]      # 🔴 パラメータ（型安全性なし）
```

### paramsの具体例

#### SuperDirt (OSC) 向けメッセージ

```python
ScheduledMessage(
    destination_id="superdirt",
    cycle=0.0,
    step=0,
    params={
        "s": "bd",              # サウンド名（文字列）
        "gain": 0.8,            # ゲイン（浮動小数点）
        "orbit": 0,             # オービット番号（整数）
        "pan": 0.5,             # パン（浮動小数点）
        "room": 0.3,            # リバーブ（浮動小数点）
        "delaySend": 0.2,       # ディレイセンド（浮動小数点）
        "cps": 0.5,             # Cycles Per Second（浮動小数点）
    }
)
```

#### MIDI向けメッセージ

```python
ScheduledMessage(
    destination_id="volca_bass",
    cycle=1.0,
    step=16,
    params={
        "note": 36,             # MIDIノート番号（整数）
        "velocity": 100,        # ベロシティ（整数 0-127）
        "duration_ms": 250,     # ノート長（ミリ秒）
        "channel": 0,           # MIDIチャンネル（整数 0-15）
    }
)
```

#### パラメータ送信の実装

```python
# OscDestinationSender (oiduna_scheduler/senders.py:51)
def send_message(self, params: dict[str, Any]) -> None:
    """
    paramsをOSC引数に変換: [key, value, key, value, ...]
    例: {"s": "bd", "gain": 0.8} → [s, bd, gain, 0.8]
    """
    args = []
    for key, value in params.items():
        args.extend([key, value])
    self.client.send_message(self.address, args)

# MidiDestinationSender (oiduna_scheduler/senders.py:125)
def send_message(self, params: dict[str, Any]) -> None:
    """
    paramsからMIDIメッセージを生成
    - note/velocity/duration_ms → Note On/Off
    - cc/value → Control Change
    - pitch_bend → Pitch Bend
    """
    if "note" in params:
        # Note On送信
        note = params["note"]
        velocity = params.get("velocity", 100)
        channel = params.get("channel", self.default_channel)
        self.port.send(mido.Message("note_on", note=note, velocity=velocity, channel=channel))
        # ... note_offスケジューリング
```

### 特徴

✅ **実際に音が出る**: ループエンジンで実装済み
✅ **シンプル**: フラットなメッセージリスト
✅ **Destination-Agnostic**: OSC/MIDI/カスタム送信先に対応
✅ **拡張可能**: ExtensionPipelineで変換可能

❌ **型安全性が低い**: `params: dict[str, Any]`
❌ **階層構造なし**: Track/Sequenceの概念がない
❌ **バリデーションなし**: 送信先でエラーが起きる可能性

---

## 型安全性の問題

### 現状の問題点

```python
# ❌ 型チェックが効かない
msg = ScheduledMessage(
    destination_id="superdirt",
    cycle=0.0,
    step=0,
    params={
        "s": "bd",
        "gain": "invalid",  # 🔴 文字列を指定してもエラーにならない
        "typo_orbit": 0,    # 🔴 タイポもエラーにならない
    }
)

# ❌ 実行時エラー（SuperDirtが受信時にエラー）
# pythonosc経由で送信されるが、SuperDirtが解釈できない
```

### Any型の危険性

```python
params: dict[str, Any]
```

- コンパイル時の型チェックなし
- IDEのオートコンプリートなし
- リファクタリング時の検出なし
- 実行時までエラーが発覚しない

---

## 2つのアーキテクチャの比較

| 項目 | CompiledSession | ScheduledMessageBatch |
|------|-----------------|----------------------|
| **データ構造** | 階層構造（3層） | フラット構造 |
| **型安全性** | ✅ 高い（dataclass） | ❌ 低い（dict[str, Any]） |
| **音の出力** | ❌ 未実装 | ✅ 実装済み |
| **MARS互換** | ✅ 完全互換 | ❓ 変換が必要 |
| **拡張性** | ✅ Scene/MixerLine対応 | ❌ フラットのみ |
| **ファイル位置** | `oiduna_core/ir/` | `oiduna_scheduler/` |
| **API** | `/playback/pattern` | `/playback/session` |
| **状態管理** | RuntimeState | MessageScheduler |

---

## 用語の整理

現在のGLOSSARY.mdの定義と、実際の実装にズレがあります。

### あなたの認識（MARS DSL v5ベース）

```
Session（セッション）
  = Environment + Tracks + Sequences + Scenes + MixerLines
  = ループ全体に関わるデータの構造的集合体
  = CompiledSession

Pattern（パターン）
  = EventSequence
  = 特定のTrackで使用される256ステップのパターン
```

### 現在のGLOSSARY.md（ScheduledMessageBatchベース）

```
Session（セッション）
  = messages + bpm + pattern_length
  = ScheduledMessageBatch
  = フラットなメッセージリスト

Pattern（パターン）
  ≈ Session（ほぼ同義）
```

### 正しい定義（提案）

```
CompiledSession（コンパイル済みセッション）
  - MARS DSL v5のコンパイル出力
  - Environment/Track/Sequence/Sceneの階層構造
  - POST /playback/pattern で受信

EventSequence（イベントシーケンス）
  - 特定のTrackの256ステップパターン
  - Event（step/velocity/note/gate）のリスト

ScheduledMessageBatch（スケジュール済みメッセージバッチ）
  - ループエンジン用のフラットなメッセージリスト
  - POST /playback/session で受信
  - 実際に音を出すデータ形式

ScheduledMessage（スケジュール済みメッセージ）
  - destination_id/cycle/step/params を持つ単一メッセージ
  - paramsは送信先依存（SuperDirt/MIDI/カスタム）
```

---

## データ変換の必要性

MARSがScheduledMessageBatchを生成するには、以下の変換が必要です：

```
CompiledSession
  ├─ Environment (bpm, scale, ...)
  ├─ Tracks (track_id → TrackParams, FxParams, ...)
  ├─ Sequences (track_id → EventSequence)
  └─ MixerLines (mixer_line_id → orbit mapping)
      ↓
   【変換処理】
      ↓
ScheduledMessageBatch
  └─ messages: [ScheduledMessage, ...]
      - destination_id (from Track or MixerLine)
      - cycle (from Event.step / 16)
      - step (from Event.step)
      - params (merge TrackParams + FxParams + Event)
```

### 変換アルゴリズム（疑似コード）

```python
def compile_to_scheduled_messages(session: CompiledSession) -> ScheduledMessageBatch:
    """CompiledSessionをScheduledMessageBatchに変換"""
    messages = []

    # 各トラックを処理
    for track_id, track in session.tracks.items():
        sequence = session.sequences.get(track_id)
        if not sequence:
            continue

        # 各イベントをScheduledMessageに変換
        for event in sequence:
            # TrackParams + FxParams + Eventをマージ
            params = {
                # TrackParams
                "s": track.params.s,
                "n": track.params.n,
                "gain": track.params.gain * event.velocity,
                "pan": track.params.pan,
                "orbit": track.params.orbit,  # または MixerLine から取得

                # FxParams
                "room": track.fx.room,
                "delay_send": track.fx.delay_send,
                # ... 他のエフェクトパラメータ

                # Event固有
                "note": event.note,  # メロディックパターンの場合
            }

            # None値を除去
            params = {k: v for k, v in params.items() if v is not None}

            messages.append(ScheduledMessage(
                destination_id="superdirt",  # または動的に決定
                cycle=event.step / 16.0,
                step=event.step,
                params=params
            ))

    return ScheduledMessageBatch(
        messages=tuple(messages),
        bpm=session.environment.bpm,
        pattern_length=session.environment.loop_steps / 16.0
    )
```

---

## 型安全性向上の提案

### 案1: Destination別のParams型定義

```python
from typing import TypedDict

class SuperDirtParams(TypedDict, total=False):
    """SuperDirt用パラメータ（型安全）"""
    s: str              # サウンド名（必須）
    n: int              # サンプル番号
    gain: float         # ゲイン
    pan: float          # パン
    orbit: int          # オービット
    room: float         # リバーブ
    size: float         # リバーブサイズ
    delay_send: float   # ディレイセンド
    delay_time: float   # ディレイタイム
    cutoff: float       # フィルターカットオフ
    resonance: float    # フィルターレゾナンス
    # ... 他のパラメータ

class MidiParams(TypedDict, total=False):
    """MIDI用パラメータ（型安全）"""
    note: int           # MIDIノート（必須）
    velocity: int       # ベロシティ
    duration_ms: int    # ノート長
    channel: int        # MIDIチャンネル
    cc: int             # CCナンバー
    value: int          # CC値
```

**利点**:
- 型チェックが効く
- IDEオートコンプリート
- ドキュメント化

**欠点**:
- Destination追加時に型定義が必要
- `total=False`でも型チェックは甘い

### 案2: Pydanticモデル

```python
from pydantic import BaseModel, Field

class SuperDirtParams(BaseModel):
    """SuperDirt用パラメータ（バリデーション付き）"""
    s: str = Field(..., description="Sound name")
    n: int = Field(default=0, ge=0, description="Sample number")
    gain: float = Field(default=1.0, ge=0.0, le=2.0, description="Gain")
    pan: float = Field(default=0.5, ge=0.0, le=1.0, description="Pan")
    orbit: int = Field(default=0, ge=0, le=11, description="Orbit")
    # ... 他のパラメータ

class MidiParams(BaseModel):
    """MIDI用パラメータ（バリデーション付き）"""
    note: int = Field(..., ge=0, le=127, description="MIDI note")
    velocity: int = Field(default=100, ge=0, le=127, description="Velocity")
    duration_ms: int = Field(default=250, ge=0, description="Duration")
    channel: int = Field(default=0, ge=0, le=15, description="MIDI channel")
```

**利点**:
- 実行時バリデーション
- 明確なエラーメッセージ
- 既存のPydantic使用と一貫性

**欠点**:
- パフォーマンスオーバーヘッド（ループ内でバリデーション）
- 拡張性が低い（カスタムパラメータ対応が困難）

### 案3: Generic Params + Runtime Validation

```python
from typing import Protocol

class ParamsValidator(Protocol):
    """パラメータバリデータープロトコル"""
    def validate(self, params: dict[str, Any]) -> dict[str, Any]:
        """パラメータをバリデート・正規化"""
        ...

class SuperDirtValidator:
    """SuperDirt用バリデーター"""
    REQUIRED = {"s"}
    OPTIONAL = {"n", "gain", "pan", "orbit", "room", ...}

    def validate(self, params: dict[str, Any]) -> dict[str, Any]:
        # 必須パラメータチェック
        for key in self.REQUIRED:
            if key not in params:
                raise ValueError(f"Missing required param: {key}")

        # 型チェック
        if not isinstance(params["s"], str):
            raise TypeError(f"param 's' must be str, got {type(params['s'])}")

        # 範囲チェック
        if "gain" in params and not (0.0 <= params["gain"] <= 2.0):
            raise ValueError(f"gain must be in [0.0, 2.0], got {params['gain']}")

        return params

# DestinationSenderに組み込む
class OscDestinationSender:
    def __init__(self, validator: ParamsValidator | None = None):
        self.validator = validator or NoOpValidator()

    def send_message(self, params: dict[str, Any]) -> None:
        params = self.validator.validate(params)  # バリデーション
        # ... OSC送信
```

**利点**:
- 柔軟性が高い（カスタムバリデーター追加可能）
- 既存のdict[str, Any]と互換性
- エラーを早期検出

**欠点**:
- 静的型チェックは効かない
- バリデーター実装が必要

---

## 推奨する方向性

### フェーズ1: 現状維持 + ドキュメント整備（短期）

1. **GLOSSARY.mdの修正**
   - CompiledSessionとScheduledMessageBatchを明確に区別
   - 用語の定義を統一
   - paramsの具体例を追加

2. **変換処理の実装**
   - MARS側に `CompiledSession → ScheduledMessageBatch` コンバーター追加
   - Oiduna側の`/playback/pattern`は当面残す

3. **paramsのドキュメント化**
   - SuperDirt用paramsの完全なリファレンス作成
   - MIDI用paramsのリファレンス作成

### フェーズ2: 型安全性向上（中期）

1. **案3採用: Runtime Validation**
   - 各Destination用のValidatorを実装
   - `destinations.yaml`でバリデーター指定
   ```yaml
   destinations:
     superdirt:
       id: superdirt
       type: osc
       validator: SuperDirtValidator  # 追加
   ```

2. **Extension強化**
   - パラメータ変換のExtension例を追加
   - MixerLine → orbit マッピングExtension

### フェーズ3: 統合（長期）

選択肢A: **ScheduledMessageBatchに統一**
- CompiledSessionは中間表現として扱う
- ループエンジンはScheduledMessageのみ処理
- 変換処理はMARS側で実施

選択肢B: **CompiledSessionベースに戻す**
- ループエンジンでCompiledSession → OSC/MIDI変換
- ScheduledMessageBatchは廃止
- Track/Sequenceの階層構造を活用

---

## 次のステップ

### 議論すべき点

1. **データモデルの将来像**
   - A案: ScheduledMessageBatch（フラット）に統一
   - B案: CompiledSession（階層）に戻す
   - C案: 両方維持（用途別）

2. **paramsの型安全性**
   - どの案を採用するか？
   - パフォーマンス vs 安全性のバランス

3. **GLOSSARY.mdの修正方針**
   - すぐに修正すべき箇所
   - 長期的に整理すべき箇所

4. **MARS側の変換処理**
   - Oidunaで実装 vs MARSで実装
   - Extensionで実装 vs コアで実装

これらについて、どこから議論を始めますか？
