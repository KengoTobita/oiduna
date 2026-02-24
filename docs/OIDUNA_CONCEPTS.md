# Oiduna: コンセプトと用語定義

**作成日**: 2026-02-24
**バージョン**: 1.0.0
**対象**: Oiduna開発者・利用者

## 目次

1. [Oidunaとは何か](#oidunaとは何か)
2. [Oidunaの責任範囲](#oidunaの責任範囲)
3. [Oidunaのデータモデル](#oidunaのデータモデル)
4. [階層化IR構造](#階層化ir構造)
5. [用語集](#用語集)

---

## Oidunaとは何か

### 一言で言うと

**Oiduna = リアルタイム音楽パターン再生エンジン**

HTTPでパターンデータ（JSON形式）を受け取り、SuperDirtとMIDIデバイスにリアルタイムでイベントを送信するPythonアプリケーション。

### Oidunaが「ではない」もの

- ❌ DSLコンパイラ（それはMARSの役割）
- ❌ プロジェクト管理システム（それもMARSの役割）
- ❌ DAW（Digital Audio Workstation）
- ❌ シンセサイザー（それはSuperColliderの役割）

### Oidunaの位置づけ

```
┌─────────────────────────────────────────────────────┐
│ クライアント（例: MARS DSL、カスタムUI、他のツール） │
│   - DSLコード記述                                    │
│   - パターン生成                                     │
│   - JSON生成                                        │
└─────────────────┬───────────────────────────────────┘
                  │ HTTP POST /playback/pattern
                  │ Content-Type: application/json
                  ↓
┌─────────────────────────────────────────────────────┐
│ ★ Oiduna ★                                          │
│   - JSONをパース                                     │
│   - IRモデルをデシリアライズ                          │
│   - 256ステップループで再生                          │
│   - OSC/MIDIメッセージ送信                           │
└─────────────────┬───────────────────────────────────┘
                  │
         ┌────────┴────────┐
         ↓                 ↓
┌─────────────────┐  ┌──────────────┐
│ SuperCollider   │  │ MIDIデバイス │
│ + SuperDirt     │  │              │
│   → 音声出力     │  │   → 音声出力  │
└─────────────────┘  └──────────────┘
```

### Oidunaの特徴

| 特徴 | 説明 |
|------|------|
| **HTTP API** | RESTful API、言語非依存 |
| **固定ループ長** | 256ステップ = 16ビート（変更不可） |
| **リアルタイム再生** | スレッドベースのループエンジン |
| **SuperDirt統合** | OSC経由でSuperCollider通信 |
| **MIDI出力** | python-rtmidi使用 |
| **SSE配信** | リアルタイム状態配信（/stream） |
| **型安全** | Python 3.13 dataclass + mypy |

---

## Oidunaの責任範囲

### ✅ Oidunaが責任を持つこと

1. **IRモデルの定義**
   - `CompiledSession`, `Environment`, `Track`, `EventSequence` 等
   - Pythonの `dataclass(frozen=True)` で定義

2. **HTTP API提供**
   - `/playback/pattern` - パターン適用
   - `/playback/start`, `/playback/stop` - 再生制御
   - `/playback/bpm` - テンポ変更
   - `/stream` - リアルタイム状態配信
   - `/superdirt/*` - SuperDirt管理
   - `/midi/*` - MIDI管理

3. **ループエンジン実装**
   - 256ステップの正確なタイミング制御
   - ステップごとのイベント検索（O(1)）
   - OSC/MIDIメッセージ送信

4. **SuperDirtとMIDI管理**
   - SuperDirtへのOSC送信
   - MIDIデバイスへのノート送信
   - バッファ管理、SynthDef管理

### ❌ Oidunaが責任を持たないこと

1. **DSL構文解析**
   - パーサー、コンパイラは含まない
   - JSONで受け取るのみ

2. **プロジェクト永続化**
   - ファイル保存、読み込みは行わない
   - クライアント側の責任

3. **UI提供**
   - Web UIやGUIは含まない
   - HTTP APIのみ提供

4. **音声生成**
   - シンセサイザーエンジンは含まない
   - SuperColliderに委譲

---

## Oidunaのデータモデル

### モデルの場所

```
oiduna/
└── packages/
    └── oiduna_core/
        ├── ir/                    # IRモデル定義
        │   ├── session.py         # CompiledSession, ApplyCommand
        │   ├── environment.py     # Environment, Chord
        │   ├── track.py           # Track, TrackParams, FxParams
        │   ├── track_midi.py      # TrackMidi
        │   ├── mixer_line.py      # MixerLine
        │   ├── send.py            # Send
        │   ├── sequence.py        # EventSequence, Event
        │   └── scene.py           # Scene
        │
        └── modulation/            # モジュレーション
            ├── modulation.py      # Modulation
            ├── signal_expr.py     # SignalExpr
            └── step_buffer.py     # StepBuffer
```

### コアとなるモデル

```python
@dataclass(frozen=True, slots=True)
class CompiledSession:
    """
    Oidunaが受け取るセッション全体のデータ

    HTTPリクエストでJSONとして受信され、
    このモデルにデシリアライズされる。
    """
    environment: Environment
    tracks: dict[str, Track]
    tracks_midi: dict[str, TrackMidi]
    mixer_lines: dict[str, MixerLine]
    sequences: dict[str, EventSequence]
    scenes: dict[str, Scene]
    apply: ApplyCommand | None
```

---

## 階層化IR構造

### 旧称：「3層IR」の問題点

**問題**:
- 「3層」と言いながら、実際には4つの役割層が存在
- Layer 2（構成層）だけで3種類以上の要素（Track, TrackMidi, MixerLine）
- 拡張性が低い（新しい要素を追加すると「3」と矛盾）

### 新称：「階層化IR（Layered IR）」

Oidunaは**4つの役割層**を持つ階層化IR構造を採用しています。

```
CompiledSession
│
├── 🌍 Environment Layer（環境層）
│   └── 目的: グローバルな演奏環境の定義
│   └── モデル: Environment
│
├── 🎛️ Configuration Layer（構成層）
│   ├── 目的: 個別トラックと音響ルーティングの設定
│   ├── Audio Tracks: Track（SuperDirt用）
│   ├── MIDI Tracks: TrackMidi（MIDI用）
│   └── Mixer Lines: MixerLine（ミキサー用）
│
├── 🎵 Pattern Layer（パターン層）
│   └── 目的: 時間軸上のイベント定義
│   └── モデル: EventSequence, Event
│
└── 🎮 Control Layer（制御層）
    ├── 目的: 再生制御とスナップショット管理
    ├── Scenes: Scene
    └── Apply Command: ApplyCommand
```

### 各層の詳細

#### 🌍 Environment Layer（環境層）

**責任**: すべてのトラックで共有される演奏環境

**モデル**: `Environment`

**主要フィールド**:
```python
@dataclass(frozen=True)
class Environment:
    bpm: float                    # テンポ（例: 120.0）
    scale: str                    # スケール（例: "C_major"）
    default_gate: float           # デフォルトゲート長
    swing: float                  # スウィング量（0.0~1.0）
    loop_steps: int               # ループ長（固定256）
    chords: list[Chord]           # コード進行（オプション）
```

**なぜ分離するのか**:
- すべてのトラックが同じBPMで演奏される
- スケール変更が全トラックに影響
- 一元管理により整合性を保証

---

#### 🎛️ Configuration Layer（構成層）

**責任**: 個別トラックの音色、エフェクト、ルーティング設定

**3種類のトラック**:

##### 1. Audio Tracks（SuperDirtトラック）

**モデル**: `Track`

**構造**:
```python
@dataclass(frozen=True)
class Track:
    meta: TrackMeta               # ID, mute, solo
    params: TrackParams           # 音色パラメータ
    fx: FxParams                  # 後方互換エフェクト
    track_fx: TrackFxParams       # トーン整形エフェクト
    sends: tuple[Send, ...]       # ミキサーラインへのセンド
    modulations: dict[str, Modulation]  # パラメータモジュレーション
```

**役割**:
- SuperDirtへのOSCメッセージ生成元
- サウンド名（`s`）、ゲイン、パン等を保持
- エフェクトパラメータ（フィルター、ディストーション等）

##### 2. MIDI Tracks（MIDIトラック）

**モデル**: `TrackMidi`

**構造**:
```python
@dataclass(frozen=True)
class TrackMidi:
    track_id: str                 # トラック識別子
    channel: int                  # MIDIチャンネル（0-15）
    velocity: int                 # デフォルトベロシティ
    transpose: int                # トランスポーズ（半音単位）
    mute: bool
    solo: bool
    cc_modulations: dict          # CCモジュレーション
```

**役割**:
- 外部MIDIデバイス制御
- MIDIノートON/OFF送信

##### 3. Mixer Lines（ミキサーライン）

**モデル**: `MixerLine`

**構造**:
```python
@dataclass(frozen=True)
class MixerLine:
    name: str                     # ライン名（例: "drums_bus"）
    include: tuple[str, ...]      # 含まれるトラック名
    volume: float                 # ボリューム
    pan: float                    # パン
    mute: bool
    solo: bool
    output: int                   # 出力先orbit
    dynamics: MixerLineDynamics   # ダイナミクス処理
    fx: MixerLineFx               # 空間エフェクト
```

**役割**:
- 複数トラックのグループ化
- バス/グループエフェクト
- マスターセクション

**なぜ3種類に分かれているのか**:
- **責任の分離**: SuperDirt、MIDI、Mixerは異なる役割
- **拡張性**: 将来、CVトラック、OSCトラック等を追加可能
- **型安全性**: 各トラック種別に固有のフィールドを持つ

---

#### 🎵 Pattern Layer（パターン層）

**責任**: 時間軸上でいつ何を鳴らすかの定義

**モデル**: `EventSequence`, `Event`

**構造**:
```python
@dataclass(frozen=True)
class EventSequence:
    track_id: str                      # 対象トラックID
    _events: tuple[Event, ...]         # イベントのリスト
    _step_index: dict[int, list[int]]  # ステップ→イベントインデックスマップ

@dataclass(frozen=True)
class Event:
    step: int                          # ステップ位置（0-255）
    velocity: float                    # ベロシティ（0.0-1.0）
    note: int | None                   # ノート番号（MIDIノート）
    gate: float                        # ゲート長（0.0-1.0）
    nudge: float                       # タイミング微調整
```

**ステップインデックスの重要性**:
```python
# ループエンジンの高速検索
current_step = 64  # 現在のステップ位置
event_indices = sequence._step_index.get(current_step, [])  # O(1)
for idx in event_indices:
    event = sequence._events[idx]
    send_osc(event)  # OSC送信
```

**なぜ分離するのか**:
- 同じパターンを異なる音色で演奏可能
- パターンを変更せずに音色だけ調整可能
- リアルタイム処理の効率化（O(1)検索）

---

#### 🎮 Control Layer（制御層）

**責任**: 再生制御とスナップショット管理

**2つの要素**:

##### 1. Scenes（シーン）

**モデル**: `Scene`

**構造**:
```python
@dataclass(frozen=True)
class Scene:
    name: str                          # シーン名
    environment: Environment | None    # 環境オーバーライド
    tracks: dict[str, Track]           # トラックスナップショット
    tracks_midi: dict[str, TrackMidi]  # MIDIトラックスナップショット
    sequences: dict[str, EventSequence]  # パターンスナップショット
    mixer_lines: dict[str, MixerLine]  # ミキサースナップショット
```

**役割**:
- 状態の保存と復元
- ライブパフォーマンス時のシーン切り替え

##### 2. Apply Command（適用コマンド）

**モデル**: `ApplyCommand`

**構造**:
```python
@dataclass(frozen=True)
class ApplyCommand:
    timing: ApplyTiming               # 適用タイミング（bar, beat, now）
    track_ids: list[str]              # 適用対象トラック
    scene_name: str | None            # シーン名
```

**役割**:
- パターン適用のタイミング制御
- 部分的な更新（特定トラックのみ）

**なぜ分離するのか**:
- パターンデータ（Pattern Layer）と制御メタデータを分離
- 同じパターンを異なるタイミングで適用可能

---

## 階層化IRの設計原則

### 1. イミュータブル（不変）

すべてのモデルは `dataclass(frozen=True)` で定義され、生成後は変更できません。

**理由**:
- 予測可能性: データが変わらないためデバッグが容易
- 並行性: マルチスレッド環境で安全
- キャッシュ: ハッシュ可能

### 2. 型安全

Python 3.13の型ヒント + mypyで厳密に型チェック。

**理由**:
- コンパイル時エラー検出
- IDEサポート（自動補完、リファクタリング）
- ドキュメントとしての型

### 3. 階層化された責任

各層が明確な責任を持ち、他の層に依存しない。

**理由**:
- テストが容易（層ごとに独立してテスト）
- 拡張が容易（新しいトラック種別を追加しても他の層は不変）
- 理解が容易（層ごとに学習できる）

### 4. O(1)検索の保証

EventSequenceのステップインデックスにより、リアルタイム処理でも高速。

**理由**:
- 256ステップ × 50トラック = 12,800回/秒の検索が必要
- O(N)では間に合わない

---

## 用語集

### Oiduna固有の用語

| 用語 | 英語 | 説明 |
|------|------|------|
| **階層化IR** | Layered IR | Oidunaが採用する4層のデータモデル構造 |
| **環境層** | Environment Layer | BPM、スケール等のグローバル設定 |
| **構成層** | Configuration Layer | トラック設定（Audio/MIDI/Mixer） |
| **パターン層** | Pattern Layer | 時間軸上のイベント定義 |
| **制御層** | Control Layer | 再生制御とシーン管理 |
| **CompiledSession** | - | Oidunaが受け取るセッション全体のデータ |
| **ステップインデックス** | Step Index | EventSequenceのO(1)検索用インデックス |
| **ループエンジン** | Loop Engine | 256ステップを繰り返し再生するエンジン |

### 混同しやすい用語の区別

| Oiduna用語 | MARS DSL用語 | 説明 |
|-----------|-------------|------|
| CompiledSession | RuntimeSession | Oidunaが受け取るIR vs MARSが生成するIR |
| Track | RuntimeTrack | Oiduna用 vs MARS DSL用（フィールド名が異なる） |
| params | sound | Oidunaでは`params` vs MARS DSLでは`sound` |
| delay_send | delaySend | snake_case vs camelCase |

### 一般的な音楽用語

| 用語 | 説明 |
|------|------|
| **BPM** | Beats Per Minute（1分間の拍数） |
| **ステップ** | 1/16音符の単位（256ステップ = 16ビート） |
| **ゲート** | ノートの長さ（0.0~1.0、1.0 = ステップ全体） |
| **ベロシティ** | ノートの強さ（0.0~1.0） |
| **パン** | 左右の定位（-1.0~1.0、0.0 = センター） |
| **センド** | 他のトラック/バスへの送信 |
| **orbit** | SuperDirtの出力チャンネル |

---

## データフローの全体像

```
1. クライアント（例: MARS DSL）
   ↓
   DSLコード記述 → RuntimeSession生成 → JSON変換
   ↓

2. HTTP POST /playback/pattern
   Content-Type: application/json
   Body: { "environment": {...}, "tracks": {...}, ... }
   ↓

3. Oiduna API (oiduna_api)
   ↓
   JSONパース → CompiledSessionデシリアライズ
   ↓

4. Oiduna Loop Engine (oiduna_loop)
   ↓
   ┌─ Environment Layer: BPM適用、スケール設定
   ├─ Configuration Layer: トラック初期化
   ├─ Pattern Layer: EventSequenceインデックス構築
   └─ Control Layer: ApplyCommandに従って適用
   ↓

5. ループ再生（256ステップ繰り返し）
   ↓
   各ステップで:
   ├─ ステップインデックスから該当イベント検索（O(1)）
   ├─ Track設定とEventを合成
   ├─ OSCメッセージ生成 → SuperDirt
   └─ MIDIメッセージ生成 → MIDIデバイス
   ↓

6. SuperCollider / MIDIデバイス
   ↓
   音声出力
```

---

## まとめ

### Oidunaの本質

**Oiduna = 階層化IRを受け取り、リアルタイムでOSC/MIDIを送信するループエンジン**

### 重要なポイント

1. **Oidunaは独立したコンポーネント** - MARS DSLとは別のプロジェクト
2. **階層化IR（4層）** - Environment/Configuration/Pattern/Control
3. **イミュータブル + 型安全** - 予測可能で安全な実装
4. **O(1)検索** - リアルタイム処理に最適化
5. **HTTP API** - 言語非依存、他のツールからも利用可能

---

## 次のステップ

Oidunaを理解したら:

1. **実際に使ってみる**: [SuperDirt v2 Setup](SUPERDIRT_V2_SETUP.md)
2. **APIリファレンス**: [Quick Reference](SUPERDIRT_V2_QUICK_REFERENCE.md)
3. **コードを読む**: `oiduna/packages/oiduna_core/ir/`

MARS DSLとの関係を理解したい場合:

4. **アーキテクチャの進化**: [Architecture Evolution](../../docs/ARCHITECTURE_EVOLUTION.md)
5. **モデル変換**: `MARS_for_oiduna/mars_compiler/model_converter.py`

---

**バージョン**: 1.0.0
**作成日**: 2026-02-24
**作成者**: Claude Code
**対象読者**: Oidunaを使う/開発するすべての人
