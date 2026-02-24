# Oiduna用語集

**バージョン**: 1.0.0
**作成日**: 2026-02-24

## クイックリファレンス

### 旧用語 → 新用語マッピング

| 旧用語 | 新用語 | 英語 | 備考 |
|-------|-------|------|------|
| 3層IR | 階層化IR | Layered IR | 実際は4層構造 |
| Layer 1 | 環境層 | Environment Layer | - |
| Layer 2 | 構成層 | Configuration Layer | Audio/MIDI/Mixer含む |
| Layer 3 | パターン層 | Pattern Layer | - |
| （新設） | 制御層 | Control Layer | Scene/ApplyCommand |

---

## Oidunaの核となる概念

### Oidunaとは

**定義**: リアルタイム音楽パターン再生エンジン

**入力**: HTTP経由のJSON（CompiledSession形式）
**出力**: OSC（SuperDirt）+ MIDI（デバイス）

---

## 階層化IR（Layered IR）

### 4つの層

#### 🌍 Environment Layer（環境層）

**役割**: グローバルな演奏環境
**モデル**: `Environment`
**主要な概念**:
- BPM（テンポ）
- Scale（スケール）
- Swing（スウィング）
- Chords（コード進行）

#### 🎛️ Configuration Layer（構成層）

**役割**: トラック設定と音響ルーティング
**3種類のトラック**:

| 種類 | モデル | 用途 |
|------|-------|------|
| Audio Tracks | `Track` | SuperDirt出力 |
| MIDI Tracks | `TrackMidi` | MIDI出力 |
| Mixer Lines | `MixerLine` | バス/グループ |

#### 🎵 Pattern Layer（パターン層）

**役割**: 時間軸上のイベント定義
**モデル**: `EventSequence`, `Event`
**重要概念**:
- ステップ（0-255）
- ステップインデックス（O(1)検索）
- Event（step, velocity, note, gate）

#### 🎮 Control Layer（制御層）

**役割**: 再生制御とスナップショット
**モデル**: `Scene`, `ApplyCommand`
**主要概念**:
- Scene（状態の保存/復元）
- ApplyCommand（適用タイミング制御）

---

## データモデル用語

### セッション

| 用語 | 型 | 説明 |
|------|---|------|
| CompiledSession | dataclass | Oidunaが受け取るセッション全体 |
| Environment | dataclass | 環境層のデータ |
| Track | dataclass | SuperDirtトラック |
| TrackMidi | dataclass | MIDIトラック |
| MixerLine | dataclass | ミキサーライン |
| EventSequence | dataclass | イベントシーケンス |
| Scene | dataclass | シーン（スナップショット） |
| ApplyCommand | dataclass | 適用コマンド |

### トラック構成要素

| 用語 | 説明 |
|------|------|
| TrackParams | 音色パラメータ（s, gain, pan等） |
| FxParams | 後方互換エフェクト |
| TrackFxParams | トーン整形エフェクト（v5新規） |
| Send | センドルーティング |
| Modulation | パラメータモジュレーション |

### パターン要素

| 用語 | 説明 |
|------|------|
| Event | 1つのトリガーイベント |
| step | ステップ位置（0-255） |
| velocity | ベロシティ（0.0-1.0） |
| note | MIDIノート番号 |
| gate | ゲート長（0.0-1.0） |
| nudge | タイミング微調整 |
| step_index | ステップ→イベントマップ（内部用） |

---

## 技術用語

### アーキテクチャ

| 用語 | 説明 |
|------|------|
| IR（中間表現） | Intermediate Representation |
| イミュータブル | 変更不可能（frozen=True） |
| 型安全 | mypyによる静的型チェック |
| O(1)検索 | ステップインデックスによる定数時間検索 |

### ループエンジン

| 用語 | 説明 |
|------|------|
| ループエンジン | 256ステップを繰り返し再生 |
| ステップ | 1/16音符単位（256ステップ = 16ビート） |
| ビート | 4分音符単位（16ビート = 4小節） |
| タイミング | ApplyTiming（bar, beat, now） |

### 通信

| 用語 | 説明 |
|------|------|
| OSC | Open Sound Control（SuperDirt通信） |
| MIDI | Musical Instrument Digital Interface |
| SSE | Server-Sent Events（リアルタイム配信） |
| HTTP API | RESTful API |

---

## 音楽用語

| 用語 | 説明 |
|------|------|
| BPM | Beats Per Minute（1分間の拍数） |
| ゲート | ノートの長さ |
| ベロシティ | ノートの強さ |
| パン | 左右の定位（-1.0~1.0） |
| オービット | SuperDirtの出力チャンネル |
| センド | 他のトラック/バスへの送信量 |
| スウィング | リズムのスウィング量 |
| トランスポーズ | 音程の移動（半音単位） |

---

## Oiduna vs MARS DSL

### 混同しやすい用語

| 概念 | Oiduna用語 | MARS DSL用語 | 違い |
|------|-----------|-------------|------|
| セッション | CompiledSession | RuntimeSession | 受信側 vs 送信側 |
| トラック | Track | RuntimeTrack | フィールド名が異なる |
| 音色パラメータ | params | sound | snake_case vs フィールド名 |
| エフェクト | delay_send | delaySend | snake_case vs camelCase |

### 責任の違い

| 機能 | Oiduna | MARS DSL |
|------|--------|----------|
| DSL構文解析 | ❌ | ✅ |
| プロジェクト管理 | ❌ | ✅ |
| IRモデル定義 | ✅ | ❌（参照のみ） |
| ループ再生 | ✅ | ❌ |
| OSC/MIDI送信 | ✅ | ❌ |
| HTTP API | ✅（再生制御） | ✅（コンパイル） |

---

## 非推奨用語

以下の用語は使用しないでください：

| 非推奨 | 理由 | 代わりに使う用語 |
|-------|------|--------------|
| 3層IR | 実際は4層 | 階層化IR |
| Layer 1, 2, 3 | 数字に依存 | 環境層、構成層、パターン層、制御層 |
| Track（曖昧） | Audio/MIDI/Mixerの区別が不明 | Audio Track, MIDI Track, Mixer Line |

---

## 用語の使い分け例

### ✅ 良い例

```
「Oidunaは階層化IRを採用しています。環境層でBPMを定義し、
構成層でAudio TrackとMIDI Trackを設定し、パターン層で
EventSequenceを定義します。」
```

### ❌ 悪い例

```
「Oidunaは3層IRです。Layer 1でBPM、Layer 2でトラック、
Layer 3でパターンを設定します。」
```

理由：
- 「3層」は実際には4層
- 「トラック」はAudio/MIDI/Mixerの区別が不明
- 「Layer 1, 2, 3」は役割が不明確

---

## よくある質問

### Q: 「3層」はどこに行ったのか？

**A**: 「3層IR」は「階層化IR」に改称されました。実際には4つの役割層（環境/構成/パターン/制御）が存在するため、数字「3」に固執しない名称に変更しました。

### Q: Layer 2が3種類に分かれているのはなぜ？

**A**: Audio Track、MIDI Track、Mixer Lineはすべて「構成層」の責任（トラック設定）を持ちますが、出力先が異なります。同じ層内で種類分けすることで、拡張性を保ちます。

### Q: OidunaとMARSの用語が違うのはなぜ？

**A**: Oidunaは受信側、MARSは送信側という役割の違いがあります。将来的には統一を検討していますが、現時点では `mars_compiler/model_converter.py` で自動変換しています。

---

## 参照ドキュメント

- [Oidunaコンセプト](OIDUNA_CONCEPTS.md) - Oidunaの詳細説明
- [システム全体像](../../docs/00_システム全体像.md) - Oiduna+MARSの全体像
- [アーキテクチャの進化](../../docs/ARCHITECTURE_EVOLUTION.md) - プロジェクト分離の経緯

---

**バージョン**: 1.0.0
**作成日**: 2026-02-24
**メンテナンス**: 用語追加時はこのファイルを更新
