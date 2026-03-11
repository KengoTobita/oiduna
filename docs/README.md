# Oiduna Documentation

Oidunaプロジェクトのドキュメント集です。

---

## 📚 コアドキュメント

### システム理解

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - システム全体のアーキテクチャ
  - プロジェクト概要と設計意図
  - 主要コンポーネント（Oiduna、MARS）
  - データフローと通信プロトコル

- **[OIDUNA_CONCEPTS.md](OIDUNA_CONCEPTS.md)** - 設計哲学とコンセプト
  - Oidunaが「何か」「何でないか」
  - 設計哲学（Destination-Agnostic、Simplicity、Performance等）
  - アーキテクチャの進化（Phase 1-5）
  - 核となるコンセプト（Timing Model含む）

- **[TERMINOLOGY.md](TERMINOLOGY.md)** - 用語集
  - Event用語の3つの文脈（PatternEvent/SessionEvent/SSE Event）
  - データ構造用語（ScheduledMessageBatch、RuntimeState等）
  - ID形式の体系（8桁/4桁hexadecimal）
  - 時間単位（Step/Beat/Bar/Cycle）
  - Layer 1-4アーキテクチャ
  - IPC通信（Producer/Consumer）
  - Manager pattern

- **[CODING_CONVENTIONS.md](CODING_CONVENTIONS.md)** - コーディング規約
  - 命名規則（PEP 8準拠、対になる概念）
  - ID形式ルール
  - パラメータ命名規則（SuperDirt/MIDI）
  - 型定義方針（Pydantic/Protocol/NewType/TypedDict）
  - モジュール構成原則（依存方向、単一責任原則）
  - パフォーマンスガイドライン

---

## 📖 リファレンス

### API・データモデル

- **[API_REFERENCE.md](API_REFERENCE.md)** - HTTP API仕様
  - エンドポイント一覧（/playback、/session、/tracks等）
  - リクエスト/レスポンス形式
  - エラーハンドリング

- **[DATA_MODEL_REFERENCE.md](DATA_MODEL_REFERENCE.md)** - データモデル詳細
  - Session/Track/Pattern/PatternEvent階層
  - ScheduledMessageBatch形式
  - モデル間の関係とデータフロー

- **[SSE_EVENTS.md](SSE_EVENTS.md)** - SSEイベントリファレンス
  - Server-Sent Events仕様
  - イベントタイプ一覧
  - ストリーミング配信形式

- **[MIDI_PARAMS_REFERENCE.md](MIDI_PARAMS_REFERENCE.md)** - MIDIパラメータ仕様
  - MIDI Note On/Off
  - Control Change
  - Pitch Bend

---

## 🛠️ 開発ガイド

### 移行・アップグレード

- **[MIGRATION_GUIDE_SCHEDULE_CUED.md](MIGRATION_GUIDE_SCHEDULE_CUED.md)** - Schedule/Cued命名整理（2026-03）
  - ScheduledMessageBatch → LoopSchedule
  - ScheduledMessage → ScheduleEntry
  - MessageScheduler → LoopScheduler
  - ScheduledChange → CuedChange
  - ScheduledChangeTimeline → CuedChangeTimeline
  - schedule_change() → cue_change()

- **[MIGRATION_GUIDE_TERMINOLOGY_CLEANUP.md](MIGRATION_GUIDE_TERMINOLOGY_CLEANUP.md)** - 用語整理移行ガイド（2026-03）
  - SessionEvent → SessionChange リネーム
  - list() → list_clients() / list_tracks() / list_patterns() リネーム
  - timing.py 新機能（StepNumber, BPM等）
  - params.py 新機能（SuperDirtParams, SimpleMidiParams等）
  - SSE Event用語の明確化

### 拡張と配布

- **[EXTENSION_DEVELOPMENT_GUIDE.md](EXTENSION_DEVELOPMENT_GUIDE.md)** - 拡張機能開発ガイド
  - Extension Systemの使い方
  - カスタムDestinationSenderの実装
  - ScheduledMessageBatch変換

- **[DISTRIBUTION_GUIDE.md](DISTRIBUTION_GUIDE.md)** - Distribution開発ガイド
  - Distribution（MARS等）の開発方法
  - Oiduna統合方法

- **[PERFORMANCE.md](PERFORMANCE.md)** - パフォーマンス設計
  - リアルタイム制約（125ms/step）
  - O(1)検索の必要性
  - 最適化技法（早期リターン、Immutable設計）

---

## 💡 実用例

- **[LIVE_CODING_EXAMPLES.md](LIVE_CODING_EXAMPLES.md)** - ライブコーディング実用例
  - 実際のライブコーディングシナリオ
  - パターン変更、BPM変更、Mute/Solo操作

- **[USAGE_PATTERNS.md](USAGE_PATTERNS.md)** - 使用パターン
  - 典型的な使用例
  - ベストプラクティス

---

## 🏗️ アーキテクチャ詳細

**[architecture/](architecture/)** - アーキテクチャ詳細ドキュメント

- **[DIAGRAMS.md](architecture/DIAGRAMS.md)** - アーキテクチャ図（Mermaid）
  - Layer 1-4 処理フロー図
  - Producer/Consumer IPC関係図
  - SessionContainer + Managers構成図
  - パッケージ間依存関係図
  - Event用語の3つの文脈図
  - Timing Model図

- **[QUICK_REFERENCE.md](architecture/QUICK_REFERENCE.md)** - クイックリファレンス
- **[README.md](architecture/README.md)** - アーキテクチャドキュメント概要
- **[external-interface.md](architecture/external-interface.md)** - 外部インターフェース
- **[layer-1-api.md](architecture/layer-1-api.md)** - Layer 1: API層
- **[layer-2-application.md](architecture/layer-2-application.md)** - Layer 2: アプリケーション層
- **[layer-3-core.md](architecture/layer-3-core.md)** - Layer 3: コア層
- **[layer-4-domain.md](architecture/layer-4-domain.md)** - Layer 4: ドメイン層
- **[layer-5-data.md](architecture/layer-5-data.md)** - Layer 5: データ層
- **[EXTENSION_GUIDE.md](architecture/EXTENSION_GUIDE.md)** - 拡張ガイド
- **[GIL_MITIGATION.md](architecture/GIL_MITIGATION.md)** - GIL緩和戦略

---

## 🧠 ナレッジベース

**[knowledge/](knowledge/)** - 設計決定、議論、研究資料

### ADR（Architecture Decision Records）

**[knowledge/adr/](knowledge/adr/)** - Oiduna実装レベルのアーキテクチャ決定

| 番号 | タイトル | 概要 |
|------|----------|------|
| [0001](knowledge/adr/0001-supernova-multicore-integration.md) | supernova マルチコア処理の採用 | scsynth → supernova移行 |
| [0002](knowledge/adr/0002-osc-confirmation-protocol.md) | OSC確認プロトコル | 双方向OSC通信設計 |
| [0003](knowledge/adr/0003-python-timing-engine-phase1.md) | Python タイミングエンジン継続 | Phase 1での判断 |
| [0004](knowledge/adr/0004-phase-roadmap-v2.md) | Phase 2以降のロードマップ | 開発フェーズ計画 |
| [0005](knowledge/adr/0005-oiduna-client-cli-design.md) | oiduna_client + CLI設計 | 開発ツール導入 |
| [0006](knowledge/adr/0006-oiduna-extension-system-api-layer.md) | 拡張システムとAPIレイヤー | 拡張機能アーキテクチャ |
| [0010](knowledge/adr/0010-session-container-refactoring.md) | SessionContainer リファクタリング | SessionManager分割 |

### Discussions

**[knowledge/discussions/](knowledge/discussions/)** - 重要な議論の記録

- [Phase Planning (2026-02-22)](knowledge/discussions/2026-02-22-phase-planning.md)
- [Distribution Design (2026-02-22)](knowledge/discussions/2026-02-22-distribution-design.md)
- [Phase 1 Implementation (2026-02-22)](knowledge/discussions/2026-02-22-phase1-implementation.md)

### Research

**[knowledge/research/](knowledge/research/)** - 技術調査・設計資料

- [Request ID System Design](knowledge/research/request-id-system-design.md)
- [oiduna-cli Design](knowledge/research/oiduna-cli-design.md)

### Handoff

**[knowledge/handoff/](knowledge/handoff/)** - 実装ハンドオフ資料

- [oiduna_client + CLI Implementation Spec](knowledge/handoff/oiduna-client-cli-implementation-spec.md)

---

## 📦 Archive

**[archive/](archive/)** - 過去のドキュメント（履歴保存）

完了済みの移行ガイド、議論記録、Phase完了サマリー等を保管。

- 完了済み移行ガイド（ID_MIGRATION_GUIDE.md、MIGRATION_GUIDE.md等）
- 議論ドキュメント（ID_LENGTH_DISCUSSION.md、OPTIMISTIC_LOCKING.md等）
- Phase完了サマリー（PHASE_1_2_SUMMARY.md、PHASE_3_SUMMARY.md等）
- 将来構想（RUST_ACCELERATION.md等）

---

## 🔗 関連ドキュメント

### ワークスペースレベル

プロジェクト横断的なドキュメントは **[/docs/](../../docs/)** を参照してください：

- [ARCHITECTURE_EVOLUTION.md](../../docs/ARCHITECTURE_EVOLUTION.md) - MARS→Oiduna分離の経緯
- [IR_RESTRUCTURING_PROPOSAL.md](../../docs/IR_RESTRUCTURING_PROPOSAL.md) - IRモデル再構成提案
- [ADR/](../../docs/ADR/) - ワークスペース横断的なADR
  - [001: Oiduna/MARS Separation of Concerns](../../docs/ADR/001-separation-of-concerns.md)
  - [002: HTTP API Choice](../../docs/ADR/002-http-api-choice.md)
  - [003: 256-Step Fixed Loop](../../docs/ADR/003-256-step-fixed-loop.md)

### MARS Documentation

MARS固有のドキュメントは **[MARS_for_oiduna/docs/](../../MARS_for_oiduna/docs/)** を参照してください。

---

## 📝 ドキュメントの種類

### このディレクトリ（oiduna/docs/）に配置すべき内容

✅ Oiduna固有の実装詳細
✅ Oiduna APIリファレンス
✅ Oiduna実装レベルのADR
✅ Oidunaの使用ガイド
✅ Oidunaの開発・設計議論

### ワークスペースレベル（/docs/）に配置すべき内容

⬆️ 複数プロジェクトに影響する設計決定
⬆️ プロジェクト間の関係
⬆️ 歴史的経緯

---

## 🗺️ ドキュメントナビゲーション

### 初めての方

1. **[OIDUNA_CONCEPTS.md](OIDUNA_CONCEPTS.md)** - Oidunaの設計思想を理解
2. **[ARCHITECTURE.md](ARCHITECTURE.md)** - システム全体像を把握
3. **[TERMINOLOGY.md](TERMINOLOGY.md)** - 用語を確認
4. **[architecture/DIAGRAMS.md](architecture/DIAGRAMS.md)** - 図で視覚的に理解

### 開発者向け

1. **[CODING_CONVENTIONS.md](CODING_CONVENTIONS.md)** - コーディング規約を確認
2. **[API_REFERENCE.md](API_REFERENCE.md)** - API仕様を参照
3. **[DATA_MODEL_REFERENCE.md](DATA_MODEL_REFERENCE.md)** - データモデルを理解
4. **[knowledge/adr/](knowledge/adr/)** - 設計決定の背景を知る

### 拡張機能開発者向け

1. **[EXTENSION_DEVELOPMENT_GUIDE.md](EXTENSION_DEVELOPMENT_GUIDE.md)** - 拡張機能の開発方法
2. **[architecture/EXTENSION_GUIDE.md](architecture/EXTENSION_GUIDE.md)** - 拡張ガイド詳細
3. **[PERFORMANCE.md](PERFORMANCE.md)** - パフォーマンス最適化

### ライブコーディング実践者向け

1. **[LIVE_CODING_EXAMPLES.md](LIVE_CODING_EXAMPLES.md)** - 実用例を確認
2. **[USAGE_PATTERNS.md](USAGE_PATTERNS.md)** - ベストプラクティス
3. **[API_REFERENCE.md](API_REFERENCE.md)** - API操作方法

---

## 🤝 コントリビューション

ドキュメントを追加・更新する場合：

1. **Single Source of Truth** - 情報の重複を避ける
2. **適切な場所に配置** - Oiduna固有かワークスペース横断的かを判断
3. **リンクの整合性** - 相対パスで正しくリンク
4. **バージョン管理** - ドキュメント内にバージョンと更新日を記載

---

**Last Updated**: 2026-03-11
**Project**: Oiduna - Realtime Loop Engine
**Documentation Version**: 2.0 (Phase 1完了、整理済み)
