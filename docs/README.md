# Oiduna Documentation

Oidunaプロジェクトのドキュメント集です。

---

## 📚 コアドキュメント

### アーキテクチャ

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - システム全体像
  - プロジェクト概要と設計意図
  - 主要コンポーネント
  - 通信フロー

- **[DATA_MODEL_REFERENCE.md](DATA_MODEL_REFERENCE.md)** - データモデル仕様
  - 3層IR構造の概念
  - モデル間の関係
  - データフロー

- **[API_REFERENCE.md](API_REFERENCE.md)** - HTTP API仕様
  - エンドポイント一覧
  - リクエスト/レスポンス形式
  - エラーハンドリング

### 分析と改善提案

- **[ANALYSIS.md](ANALYSIS.md)** - 現状分析
  - システム分析結果
  - 課題の整理

- **[IMPROVEMENTS.md](IMPROVEMENTS.md)** - 問題点と改善提案
  - 特定された問題点
  - 提案される改善策

### ガイド

- **[USAGE_PATTERNS.md](USAGE_PATTERNS.md)** - 使用パターン
  - 典型的な使用例
  - ベストプラクティス

- **[PERFORMANCE.md](PERFORMANCE.md)** - パフォーマンスガイド
  - 最適化のヒント
  - ベンチマーク結果

- **[DISTRIBUTION_GUIDE.md](DISTRIBUTION_GUIDE.md)** - Distribution開発ガイド
  - Distribution（MARS等）の開発方法

- **[EXTENSION_DEVELOPMENT_GUIDE.md](EXTENSION_DEVELOPMENT_GUIDE.md)** - 拡張機能開発ガイド
  - 拡張機能の開発方法

### 概念と用語

- **[OIDUNA_CONCEPTS.md](OIDUNA_CONCEPTS.md)** - Oidunaの概念
  - 基本概念の説明

- **[TERMINOLOGY.md](TERMINOLOGY.md)** - 用語集
  - プロジェクト全体で使用する用語

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

## 🤝 コントリビューション

ドキュメントを追加・更新する場合：

1. **Single Source of Truth** - 情報の重複を避ける
2. **適切な場所に配置** - Oiduna固有かワークスペース横断的かを判断
3. **リンクの整合性** - 相対パスで正しくリンク

---

**Last Updated**: 2026-02-26
**Project**: Oiduna - Realtime Loop Engine
