# ADR-0023: Unified 4-Layer Architecture

**Status:** Accepted
**Date:** 2026-03-11
**Deciders:** Kengo Tobita, Claude Sonnet 4.5
**Related:** ADR-0012 (Package Architecture), ADR-0014 (Merge Destination into Models)

---

## Context

Oidunaは9つの独立したパッケージ（`oiduna_models`, `oiduna_session`, `oiduna_scheduler`, `oiduna_loop`, `oiduna_api`, `oiduna_auth`, `oiduna_timeline`, `oiduna_cli`, `oiduna_client`）で構成されていた。

### 問題点

1. **複雑な依存関係**
   - パッケージ間の循環依存のリスク
   - インポートパスが長く冗長（`from oiduna_session.compiler import ...`）
   - 各パッケージに個別のpyproject.tomlが必要

2. **開発効率の低下**
   - パッケージをまたいだリファクタリングが困難
   - テストの実行が複雑（複数パッケージにまたがる）
   - 新規開発者のオンボーディングコストが高い

3. **配布の複雑さ**
   - ユーザーは9つのパッケージすべてをインストールする必要
   - バージョン管理が複雑（各パッケージが独立したバージョン）

4. **アーキテクチャの可視性低下**
   - パッケージの粒度が細かすぎて全体像が見えにくい
   - 責任境界が曖昧（例：`oiduna_scheduler`と`oiduna_loop`の役割分担）

---

## Decision

**9パッケージ構成から統合4層アーキテクチャへ移行する。**

### 新アーキテクチャ

```
src/oiduna/
├── domain/              # ドメイン層（ビジネスロジック）
│   ├── models/          # データモデル
│   ├── schedule/        # スケジュールコンパイル
│   ├── session/         # セッション管理
│   └── timeline/        # タイムライン管理
│
├── infrastructure/      # インフラ層（技術実装）
│   ├── execution/       # ループエンジン実行
│   ├── routing/         # メッセージルーティング
│   ├── transport/       # OSC/MIDI送信
│   ├── ipc/            # プロセス間通信
│   └── auth/           # 認証・トークン管理
│
├── application/        # アプリケーション層（ユースケース）
│   ├── api/            # FastAPI routes
│   └── factory/        # コンポーネントファクトリ
│
└── interface/          # インターフェース層（外部接続）
    ├── cli/            # コマンドラインインターフェース
    └── client/         # HTTPクライアントライブラリ
```

### 層間依存ルール

- **ドメイン層**: 他の層に依存しない（純粋なビジネスロジック）
- **インフラ層**: ドメイン層のインターフェースを実装
- **アプリケーション層**: ドメイン層とインフラ層を組み合わせる
- **インターフェース層**: アプリケーション層を利用

### 移行マッピング

| 旧パッケージ | 新レイヤー/モジュール |
|-------------|---------------------|
| `oiduna_models` | `domain/models/` |
| `oiduna_session` | `domain/session/`, `domain/schedule/compiler.py` |
| `oiduna_timeline` | `domain/timeline/` |
| `oiduna_scheduler` | `domain/schedule/models.py`, `infrastructure/routing/` |
| `oiduna_loop` | `infrastructure/execution/`, `application/factory.py` |
| `oiduna_auth` | `infrastructure/auth/` |
| `oiduna_api` | `application/api/` |
| `oiduna_cli` | `interface/cli/` |
| `oiduna_client` | `interface/client/` |

---

## Consequences

### Positive

1. **シンプルなインストール**
   ```bash
   pip install oiduna  # 1パッケージのみ
   ```

2. **明確なインポートパス**
   ```python
   from oiduna import Session, LoopEngine  # トップレベルAPI
   from oiduna.domain.schedule import SessionCompiler
   ```

3. **改善された開発体験**
   - 単一のpyproject.toml
   - 統一されたテストスイート
   - リファクタリングが容易

4. **明確なアーキテクチャ**
   - 4層の責任境界が明確
   - 依存方向が一方向（上位層→下位層）
   - 新規開発者が理解しやすい

5. **テストカバレッジの向上**
   - 統合テストが書きやすい
   - モック作成が容易
   - カバレッジ測定が統一的

### Negative

1. **Breaking Change**
   - 全てのインポートパスが変更
   - v0.x → v1.0のメジャーバージョンアップ
   - ユーザーはMIGRATION_GUIDE.mdを参照して移行が必要

2. **初期学習コスト**
   - 既存開発者が新構造を学習する必要
   - ドキュメント更新が必要

3. **一時的な不安定性**
   - 移行中にバグが発生する可能性
   - 広範囲なテストが必要

### Mitigation

1. **包括的なドキュメント**
   - ✅ ARCHITECTURE.md - 4層アーキテクチャ説明
   - ✅ MIGRATION_GUIDE.md - v0.x → v1.0移行ガイド
   - ✅ README.md更新

2. **テスト体制**
   - ✅ 370テストすべてが成功
   - ✅ 52%のコードカバレッジ維持
   - ✅ ドメイン層 >90%カバレッジ

3. **段階的リリース**
   - feature/4-layer-architecture-v1.0ブランチで開発
   - mainブランチマージ前に十分なレビュー

---

## Implementation

### 完了した作業

1. **Phase 0-1: テスト環境構築と修正**
   - 378テスト収集、370テスト成功
   - インポートエラー11件修正

2. **Phase 2: 品質チェック**
   - カバレッジ52%達成
   - 型チェック実行（非致命的エラーのみ）

3. **Phase 3-5: 移植実行**
   - 旧packages/ディレクトリ削除
   - 新src/oiduna/構造作成
   - tests/ディレクトリ再編成

4. **Phase 6: OSS準備**
   - LICENSE (MIT)作成
   - CONTRIBUTING.md作成
   - GitHub Actions CI設定
   - pyproject.toml完全メタデータ

5. **Phase 7-8: 検証とリリース**
   - パッケージビルド成功（139KB wheel）
   - 全テスト成功確認
   - 2コミット作成

### 統計

- **変更ファイル数**: 268ファイル
- **追加行数**: 4067行
- **削除行数**: 9302行
- **テスト数**: 370成功、8スキップ
- **パッケージサイズ**: 139KB (wheel), 97KB (tarball)

---

## References

- [Clean Architecture (Robert C. Martin)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Hexagonal Architecture (Alistair Cockburn)](https://alistair.cockburn.us/hexagonal-architecture/)
- ADR-0012: Package Architecture Layered Design
- ADR-0014: Merge Destination into Models
- ARCHITECTURE.md: 4-Layer Architecture Documentation
- MIGRATION_GUIDE.md: v0.x → v1.0 Migration Guide

---

## Notes

この決定により、Oidunaは**シンプルで保守しやすいモノリシックパッケージ**になった。4層アーキテクチャは明確な責任分離を提供しつつ、単一パッケージの利便性を保つ。

将来的にマイクロサービス化する必要が生じた場合、この明確な層分離により、各層を独立したサービスとして切り出すことが容易になる。

---

**Version:** 1.0.0
**Status:** Production Ready
**Last Updated:** 2026-03-11
