# Oiduna Knowledge Base

このディレクトリは Oiduna プロジェクトの設計ドキュメント、議事録、研究資料を集約したナレッジベースです。

---

## ディレクトリ構造

```
knowledge/
├── adr/              # Architecture Decision Records（設計決定の記録）
├── discussions/      # ディスカッション議事録
├── research/         # 研究・調査資料、設計ドキュメント
├── handoff/          # 実装ハンドオフ資料（別エージェント向け）
└── README.md         # このファイル
```

---

## ADR（Architecture Decision Records）

設計上の重要な決定を記録したドキュメント群。

### Phase 1関連
- [ADR-0001: supernova マルチコア統合](./adr/0001-supernova-multicore-integration.md)
  - scsynth vs supernova vs Rust の検討結果
  - supernova採用の理由

- [ADR-0002: OSC確認プロトコル](./adr/0002-osc-confirmation-protocol.md)
  - 双方向OSC通信の設計
  - ポート57120（送信）+ 57121（受信）の構成

- [ADR-0003: Python タイミングエンジン継続（Phase 1）](./adr/0003-python-timing-engine-phase1.md)
  - Phase 1でPython継続の決定
  - Rust化はPhase 2.5以降で判断

### Phase 2以降関連
- [ADR-0004: Phase 2以降のロードマップ](./adr/0004-phase-roadmap-v2.md)
  - Phase 2.0: リクエストID導入
  - Phase 2.1: 開発ツール（oiduna_client + oiduna_cli）
  - Phase 2.2: 検証・品質向上
  - Phase 2.5: 最適化・測定
  - Phase 3: 機能拡張
  - Phase 4: Rust化（条件付き）

- [ADR-0005: oiduna_client + CLI 設計](./adr/0005-oiduna-client-cli-design.md)
  - 軽量開発ツール導入の決定
  - MARS DSL開発ボトルネック回避
  - Claude Code統合要件

---

## Discussions（ディスカッション議事録）

重要な議論の記録。

- [Phase Planning Discussion（2026-02-22）](./discussions/2026-02-22-phase-planning.md)
  - Phase 2以降の機能整理
  - 「追い綱」としてのシステム本質の確認
  - Web UIの位置づけ

- [Distribution Design（2026-02-22）](./discussions/2026-02-22-distribution-design.md)
  - MARS_for_oidunaの二重の役割（プロダクション + リファレンス）
  - ディストリビューションが提供すべき機能
  - Oidunaコアとディストリビューションの責務分離

---

## Research（研究・調査資料）

設計書、技術調査、仕様書など。

- [リクエストIDシステム設計](./research/request-id-system-design.md)
  - 同時リクエスト問題の解決
  - UUID生成とマッチング改善
  - キュー管理（基本 + 優先度付き）

- [oiduna-cli 設計](./research/oiduna-cli-design.md)
  - 軽量CLI/ライブラリの設計書
  - DI的アプローチによる開発加速
  - 2モード（コマンド + REPL）

---

## Handoff（実装ハンドオフ資料）

別エージェントや他の開発者に実装を引き継ぐための詳細仕様書。

- [oiduna_client + CLI 実装仕様書](./handoff/oiduna-client-cli-implementation-spec.md)
  - **Phase 2.1 実装担当エージェント向け**
  - oiduna_client（Pythonライブラリ）完全仕様
  - oiduna_cli（CLIツール）完全仕様
  - サンプルファイル仕様
  - Claude Code統合要件
  - 実装チェックリスト
  - テスト要件

---

## ナレッジベースの使い方

### 設計決定を調べたい
→ `adr/` ディレクトリ内のADRを参照

### 過去の議論を振り返りたい
→ `discussions/` ディレクトリ内の議事録を参照

### 技術的な設計詳細を知りたい
→ `research/` ディレクトリ内の設計書を参照

### 実装を引き継ぎたい
→ `handoff/` ディレクトリ内の実装仕様書を参照

---

## ドキュメント作成ガイドライン

### ADR作成時
1. `templates/adr-template.md` をコピー
2. 連番を付ける（例: 0006）
3. コンテキスト、決定、理由、影響を明記
4. 関連ADRへのリンクを追加

### ディスカッション記録時
1. 日付をファイル名に含める（例: 2026-02-22-xxx.md）
2. 参加者、目的、主要な決定事項を記録
3. 次のアクションを明記

### 研究・設計書作成時
1. 問題の背景を明確に記述
2. 代替案の検討結果を記録
3. 実装の詳細を含める
4. 関連ドキュメントへのリンクを追加

### ハンドオフ資料作成時
1. 対象読者を明確にする（別エージェント、新規開発者等）
2. 完全に独立して作業できる詳細度
3. 実装チェックリストを含める
4. 完了条件を明記

---

## 関連リソース

### Oidunaリポジトリ
- メインリポジトリ: `/home/tobita/study/livecoding/oiduna/`
- Phase 1実装サマリー: `oiduna/docs/PHASE1_IMPLEMENTATION_SUMMARY.md`

### MARS_for_oiduna
- ディストリビューションリポジトリ: `/home/tobita/study/livecoding/MARS_for_oiduna/`

---

## 更新履歴

- 2026-02-22: ナレッジベース構築、ADR 0001-0005作成
- 2026-02-22: Phase 2プランニング、oiduna-cli設計
- 2026-02-22: oiduna_client + CLI実装仕様書作成（Phase 2.1ハンドオフ資料）

---

**管理者:** Claude Code
**最終更新:** 2026-02-22
