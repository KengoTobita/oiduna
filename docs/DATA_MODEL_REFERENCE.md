# データモデルリファレンス

**バージョン**: 2.0.0
**更新日**: 2026-02-23

> **Single Source of Truth**: このドキュメントはデータモデルの概念とアーキテクチャを説明します。詳細な型定義、フィールド名、デフォルト値などは実際のコードを参照してください。コードが真実の源です。

## 目次

1. [3層IR構造の概念](#1-3層ir構造の概念)
2. [なぜこの設計なのか](#2-なぜこの設計なのか)
3. [データモデルの場所](#3-データモデルの場所)
4. [モデル間の関係](#4-モデル間の関係)
5. [データフロー](#5-データフロー)

---

## 1. 3層IR構造の概念

Oidunaは3層の中間表現（IR: Intermediate Representation）を採用しています。これは音楽制作の概念的な階層構造を反映しています。

```
┌────────────────────────────────────────────────────────────┐
│ Layer 1: Environment（演奏環境）                            │
│  - BPM、スケール、スウィングなどグローバル設定              │
│  - コード進行                                              │
└────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌────────────────────────────────────────────────────────────┐
│ Layer 2: Track Configuration（トラック設定）                │
│  - サウンドパラメータ（音色、ゲイン、パンなど）             │
│  - エフェクト設定                                          │
│  - MIDIトラック設定                                        │
│  - ミキサーライン（バス/グループ）                          │
└────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌────────────────────────────────────────────────────────────┐
│ Layer 3: Pattern Data（パターンデータ）                     │
│  - EventSequence: ステップごとのイベント                    │
│  - Event: トリガータイミング、ベロシティ、ノート            │
└────────────────────────────────────────────────────────────┘
```

### 1.1 Layer 1: Environment

**責任**: グローバルな演奏環境を定義

**主要な概念**:
- **BPM**: テンポ制御
- **Scale**: 音階定義（例: "C_major", "A_minor"）
- **Chords**: コード進行（オプション）
- **Loop Steps**: ループの長さ（固定256ステップ = 16ビート）

**なぜ分離するのか**: すべてのトラックで共有される設定を一元管理するため。

### 1.2 Layer 2: Track Configuration

**責任**: 個別のトラックの音色とエフェクトを定義

**主要な概念**:
- **Track**: SuperDirtトラックの完全な定義
  - メタ情報（ID、ミュート、ソロ）
  - サウンドパラメータ（音色名、ゲイン、パンなど）
  - エフェクトパラメータ（フィルター、ディストーション、エンベロープなど）
  - モジュレーション（LFO、エンベロープなどの時間変化）
- **TrackMidi**: MIDIトラックの定義
- **MixerLine**: 複数トラックをグループ化するバス/グループ（v5新規）

**なぜ分離するのか**: 音色設定とパターンデータを分離することで、同じパターンを異なる音色で再生できる。

### 1.3 Layer 3: Pattern Data

**責任**: 時間軸上のイベントを定義

**主要な概念**:
- **EventSequence**: インデックス化されたイベントのコレクション
  - O(1)でステップ位置からイベントを検索可能
  - イミュータブルデータ構造（パフォーマンス最適化）
- **Event**: 1つのトリガー
  - ステップ位置（0-255）
  - ベロシティ
  - ノート（メロディック楽器用）
  - ゲート長

**なぜ分離するのか**: パターンデータを効率的に管理し、リアルタイム再生時の高速検索を実現するため。

---

## 2. なぜこの設計なのか

### 2.1 イミュータブル設計

すべてのIRモデルは`dataclass(frozen=True)`で定義されています。

**理由**:
- **予測可能性**: データの状態が変わらないため、デバッグが容易
- **並行性**: マルチスレッド環境で安全
- **キャッシュ**: ハッシュ可能なため、効率的なキャッシングが可能

### 2.2 型安全性

Pythonの型ヒントを完全に使用し、mypyで厳密に型チェックしています。

**理由**:
- **コンパイル時エラー検出**: 実行前に型エラーを発見
- **ドキュメントとしての型**: コードが自己文書化される
- **IDEサポート**: 自動補完とリファクタリング支援

### 2.3 3層分離の利点

**音色とパターンの独立性**:
- 同じパターンを異なる音色で演奏可能
- パターンを変更せずに音色だけ調整可能

**段階的なコンパイル**:
- DSL → Layer 1, 2, 3の順に構築
- 各層を独立してテスト可能

**効率的なリアルタイム処理**:
- ステップインデックスによるO(1)イベント検索
- 不要な再計算を避ける

### 2.4 MARSとOidunaの分離

**MARS (mars_dsl)**: DSLコンパイラとしてのRuntime表現
**Oiduna (oiduna_core)**: ループエンジンとしてのCompiled表現

**理由**:
- **責任の分離**: DSLの進化とエンジンの最適化を独立して行える
- **互換性**: MARSのRuntime表現は後方互換性を維持、Oidunaは最適化のために変更可能
- **柔軟性**: MARS以外のDSLやフロントエンドもOidunaを使用できる

**注意**: この分離により一部のフィールド名に相違があります（例: `sound` vs `params`、エフェクト名のキャメルケース vs スネークケース）。変換処理は`mars_compiler/model_converter.py`で自動的に行われます。

---

## 3. データモデルの場所

### 3.1 Oiduna Core IR（ループエンジン用）

**場所**: `oiduna/packages/oiduna_core/ir/`

| ファイル | 主要なモデル | 説明 |
|---------|------------|------|
| `session.py` | CompiledSession, ApplyCommand | セッション全体とApplyコマンド |
| `environment.py` | Environment, Chord | Layer 1: 演奏環境 |
| `track.py` | Track, TrackParams, FxParams, TrackFxParams | Layer 2: SuperDirtトラック |
| `track_midi.py` | TrackMidi | Layer 2: MIDIトラック |
| `mixer_line.py` | MixerLine, MixerLineDynamics, MixerLineFx | Layer 2: ミキサーライン（v5） |
| `send.py` | Send | Layer 2: センドルーティング |
| `sequence.py` | EventSequence, Event | Layer 3: パターンデータ |
| `scene.py` | Scene | スナップショット |

**モジュレーション**: `oiduna/packages/oiduna_core/modulation/`

| ファイル | 主要なモデル | 説明 |
|---------|------------|------|
| `modulation.py` | Modulation | パラメータモジュレーション定義 |
| `signal_expr.py` | SignalExpr | シグナル式のAST（LFO、エンベロープなど） |
| `step_buffer.py` | StepBuffer | ステップごとの値バッファ |

### 3.2 MARS DSL Runtime（DSLコンパイラ用）

**場所**: `Modular_Audio_Real-time_Scripting/mars_dsl/models.py`

**主要なモデル**: RuntimeSession, RuntimeEnvironment, RuntimeTrack, RuntimeSequence など

**特徴**: oiduna_core IRと構造的に類似していますが、一部のフィールド名が異なります。詳細はコードを参照してください。

### 3.3 MARS API（プロジェクト管理用）

**場所**: `Modular_Audio_Real-time_Scripting/mars_api/models.py`

**主要なモデル**: ProjectData, SongData, ClipData など

**目的**: プロジェクト、ソング、クリップの永続化とメタデータ管理

---

## 4. モデル間の関係

### 4.1 セッション構造

```
CompiledSession (oiduna_core)
├── environment: Environment
├── tracks: dict[str, Track]
├── tracks_midi: dict[str, TrackMidi]
├── mixer_lines: dict[str, MixerLine]
├── sequences: dict[str, EventSequence]
├── scenes: dict[str, Scene]
└── apply: ApplyCommand | None
```

### 4.2 トラック構造

```
Track (SuperDirt)
├── meta: TrackMeta (ID, mute, solo)
├── params: TrackParams (音色、ゲイン、パンなど)
├── fx: FxParams (後方互換用エフェクト)
├── track_fx: TrackFxParams (トーン整形エフェクト、v5)
├── sends: tuple[Send, ...] (ミキサーラインへのセンド)
└── modulations: dict[str, Modulation] (パラメータモジュレーション)

TrackMidi (MIDI)
├── track_id: str
├── channel: int (0-15)
├── velocity: int
├── mute, solo: bool
└── モジュレーション設定
```

### 4.3 ミキサーライン構造（v5新規）

```
MixerLine
├── name: str
├── include: tuple[str, ...] (含まれるトラック名)
├── volume, pan: float
├── mute, solo: bool
├── dynamics: MixerLineDynamics (リミッター/コンプレッション)
└── fx: MixerLineFx (空間エフェクト: reverb, delay, leslie)
```

**シグナルフロー**:
```
トラックサウンド → トラックFx → MixerLineダイナミクス → MixerLineFx → 出力
```

### 4.4 シーン構造

```
Scene (スナップショット)
├── name: str
├── environment: Environment | None
├── tracks: dict[str, Track]
├── tracks_midi: dict[str, TrackMidi]
└── sequences: dict[str, EventSequence]
```

---

## 5. データフロー

### 5.1 DSLからサウンド再生まで

```
┌─────────────────────────────────────────────────────────────┐
│ 1. ユーザー                                                  │
│    ↓ MARS DSLコード                                         │
│ 2. MARS DSL Compiler                                        │
│    ├─ Larkパーサー (338行文法)                               │
│    ├─ RuntimeSession生成 (mars_dsl)                         │
│    └─ CompiledSession変換 (oiduna_core)                    │
│       ↓ JSON (HTTP POST /playback/pattern)                  │
│ 3. Oiduna Loop Engine                                       │
│    ├─ CompiledSessionデシリアライズ                         │
│    └─ ループエンジン適用                                     │
│       ├─→ OSCメッセージ → SuperCollider → サウンド再生       │
│       └─→ MIDIメッセージ → MIDIデバイス → サウンド再生       │
│                                                             │
│ 4. ユーザー ← サウンド                                       │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 プロジェクト管理からIRモデルへ

```
┌─────────────────────────────────────────────────────────────┐
│ mars_api (Pydantic) - プロジェクト管理層                     │
│                                                             │
│   ProjectData ────→ project.json                            │
│      │                                                      │
│      └─→ SongData ──→ songs/*/song.json                    │
│             │                                               │
│             └─→ ClipData ──→ songs/*/clips/*.json          │
│                    │                                        │
│                    │ DSLコンパイル                          │
│                    ↓                                        │
└─────────────────────────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ mars_dsl (Runtime) - コンパイラ層                            │
│                                                             │
│   RuntimeSession                                            │
│      │ 変換 (model_converter.py)                           │
│      ↓                                                      │
└─────────────────────────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ oiduna_core (Compiled) - エンジン層                         │
│                                                             │
│   CompiledSession                                           │
│      │                                                      │
│      └─→ Oiduna Loop Engine                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 詳細情報の参照方法

### データモデルの詳細を知りたい場合

1. **Pythonファイルを直接読む**: コードが最も正確で最新の情報源です
2. **型ヒントを確認**: 各フィールドの型がドキュメントとして機能します
3. **docstringを読む**: クラスやフィールドのdocstringに説明があります
4. **テストコードを参照**: `tests/`ディレクトリのテストコードが使用例を示しています

### 推奨ツール

- **IDEのジャンプ機能**: VSCodeやPyCharmで定義にジャンプ
- **mypy**: 型チェックで整合性を確認
- **pydantic**: ランタイムバリデーション

### フィールド名の相違について

MARS DSL (mars_dsl) と Oiduna Core (oiduna_core) の間で一部のフィールド名が異なります。

**主な相違点**:
- エフェクトパラメータの命名規則（キャメルケース vs スネークケース）
- 一部のフィールドの追加/削除

**変換方法**: `MARS_for_oiduna/mars_compiler/model_converter.py` を参照してください。このファイルがすべての変換ロジックを含んでいます。

---

## 関連ドキュメント

- [システム全体像](00_システム全体像.md) - アーキテクチャとデータフロー
- [現状分析](01_現状分析.md) - 実装状況
- [ADR-0002: OSC確認プロトコル](knowledge/adr/0002-osc-confirmation-protocol.md) - データ送信プロトコル設計

---

## コードリファレンス

すべての詳細情報はコードを参照してください：

**Oiduna Core IR**:
- `oiduna/packages/oiduna_core/ir/` - すべてのIRモデル
- `oiduna/packages/oiduna_core/modulation/` - モジュレーションモデル

**MARS DSL**:
- `Modular_Audio_Real-time_Scripting/mars_dsl/models.py` - Runtimeモデル

**MARS API**:
- `Modular_Audio_Real-time_Scripting/mars_api/models.py` - Pydanticモデル

---

**バージョン**: 2.0.0 (SSOT準拠版)
**更新日**: 2026-02-23
**作成者**: Claude Code
**ドキュメント方針**: 概念とアーキテクチャのみ記載、詳細はコードを参照
