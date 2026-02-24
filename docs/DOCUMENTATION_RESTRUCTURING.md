# Oidunaドキュメント再構成計画

**作成日**: 2026-02-24
**バージョン**: 1.0.0
**目的**: 網羅的で理解しやすいドキュメント体系の確立

## 到達目標

このドキュメントからOidunaの：
1. ✅ **基本概念・目的**を理解できる
2. ✅ **データモデルとデータフロー**を理解できる
3. ✅ **ユースケース熟知者**が性能向上/リファクタをレビューできる
4. ✅ **網羅性**があり、必要な情報がすべて含まれる

---

## 提案するドキュメント体系（読む順序）

### 📚 Tier 1: 導入・概要（Oidunaを知る）

読者がOidunaとは何かを理解し、使い始めるための最初のステップ。

| ファイル | 目的 | 対象読者 | ページ数 | 状態 |
|---------|------|---------|---------|------|
| **README.md** | プロジェクト概要、クイックスタート | すべての人 | 2-3p | 📝 要リファクタ |
| **OIDUNA_CONCEPTS.md** | Oidunaとは何か、責任範囲、基本概念 | 初学者 | 15-20p | ✅ 完成 |
| **TERMINOLOGY.md** | 用語集、Oiduna固有の用語 | すべての人 | 5p | ✅ 完成 |

**読む順序**: README → OIDUNA_CONCEPTS → TERMINOLOGY

**内容**:
- **README**: 1分で理解できる概要、インストール、最初のAPIコール例
- **OIDUNA_CONCEPTS**: Oidunaの存在理由、何ができて何ができないか、階層化IR、責任分離
- **TERMINOLOGY**: 用語の統一、混同しやすい用語の区別

---

### 🏗️ Tier 2: アーキテクチャ理解（設計を理解する）

Oidunaの内部設計を深く理解し、設計判断の背景を知る。

| ファイル | 目的 | 対象読者 | ページ数 | 状態 |
|---------|------|---------|---------|------|
| **ARCHITECTURE.md** | システム設計、データフロー、設計判断 | 開発者、上級ユーザー | 20-25p | 🆕 新規作成 |
| **DATA_MODEL_REFERENCE.md** | IRモデル完全リファレンス | 開発者、Distribution作者 | 30-40p | 🆕 新規作成 |
| **PERFORMANCE.md** | パフォーマンス特性、ボトルネック | 開発者、最適化担当 | 10-15p | 🆕 新規作成 |

**読む順序**: ARCHITECTURE → DATA_MODEL_REFERENCE → PERFORMANCE

**内容**:
- **ARCHITECTURE**:
  - 設計哲学（SPECIFICATION_v1.mdから抽出）
  - 責任分離（Oiduna vs Distribution）
  - 階層化IRの詳細設計
  - データフロー全体図
  - 設計判断の理由（なぜこの設計なのか）

- **DATA_MODEL_REFERENCE**:
  - CompiledSession構造の完全仕様
  - 各層（Environment/Configuration/Pattern/Control）の詳細
  - 各dataclassの全フィールド説明
  - デシリアライズ・シリアライズ仕様
  - モジュレーションモデル
  - ステップインデックスの実装詳細

- **PERFORMANCE**:
  - ループエンジンのボトルネック分析
  - O(1)検索の実装とメリット
  - メモリ使用量の見積もり
  - GIL影響とマルチスレッド戦略
  - 最適化ポイント（EventSequence構築、OSC送信等）
  - ベンチマーク結果

---

### 🔧 Tier 3: API・使用方法（実際に使う）

Oidunaを実際に使うための実践的な情報。

| ファイル | 目的 | 対象読者 | ページ数 | 状態 |
|---------|------|---------|---------|------|
| **API_REFERENCE.md** | 全エンドポイント、使用例 | ユーザー、Distribution作者 | 15-20p | 🆕 新規作成 |
| **USAGE_PATTERNS.md** | 典型的なユースケース、パターン | ユーザー | 10-15p | 🆕 新規作成 |

**読む順序**: API_REFERENCE → USAGE_PATTERNS

**内容**:
- **API_REFERENCE**:
  - 全エンドポイント一覧（OpenAPI形式）
  - 各エンドポイントの詳細：
    - リクエスト形式
    - レスポンス形式
    - curlコマンド例
    - Pythonコード例
  - エラーレスポンス一覧
  - SSEストリーム仕様

- **USAGE_PATTERNS**:
  - 典型的なユースケース：
    - シンプルなループ再生
    - リアルタイムBPM変更
    - シーン切り替え
    - MIDI出力
    - SuperDirtサンプルロード
  - アンチパターン（やってはいけないこと）
  - トラブルシューティング

---

### 👨‍💻 Tier 4: 開発者向け（Oidunaを改善する）

Oidunaの開発に参加する、または拡張するための情報。

| ファイル | 目的 | 対象読者 | ページ数 | 状態 |
|---------|------|---------|---------|------|
| **DEVELOPMENT_GUIDE.md** | 新機能追加、デバッグ、テスト | Oiduna開発者 | 15-20p | 🆕 新規作成 |
| **DISTRIBUTION_GUIDE.md** | Distribution（DSL）開発ガイド | Distribution作者 | 20-25p | ✅ 完成（要更新） |

**読む順序**: DEVELOPMENT_GUIDE → DISTRIBUTION_GUIDE

**内容**:
- **DEVELOPMENT_GUIDE**:
  - 開発環境セットアップ
  - コードベース構造（packages/oiduna_core, oiduna_loop, oiduna_api）
  - 新機能追加の手順
  - テスト戦略（pytest、mypy、ruff）
  - デバッグ方法（ログ、ブレークポイント）
  - CI/CD（GitHub Actions）
  - リリースプロセス

- **DISTRIBUTION_GUIDE**:
  - Distributionとは何か
  - CompiledSessionの生成方法
  - Oiduna APIとの通信
  - モデル変換（RuntimeSession → CompiledSession）
  - 実装例（MARS DSL）
  - ベストプラクティス

---

### 📋 その他

| ファイル | 目的 | 状態 |
|---------|------|------|
| **CHANGELOG.md** | 変更履歴 | ✅ 維持 |
| **architecture/GIL_MITIGATION.md** | GIL軽減策の詳細 | ✅ 維持 |

---

## 現状ファイルの処理

### ✅ そのまま維持

| ファイル | 理由 |
|---------|------|
| OIDUNA_CONCEPTS.md | 新規作成、そのまま維持 |
| TERMINOLOGY.md | 新規作成、そのまま維持 |
| DISTRIBUTION_GUIDE.md | 内容良好、マイナー更新のみ |
| CHANGELOG.md | 変更履歴、維持 |
| architecture/GIL_MITIGATION.md | 専門的内容、維持 |

### 🔄 リファクタ・統合

| 現状ファイル | 処理 | 新ファイル |
|------------|------|-----------|
| SPECIFICATION_v1.md | 分割統合 | → ARCHITECTURE.md（設計哲学、責任分離）<br>→ DATA_MODEL_REFERENCE.md（IRモデル）<br>→ API_REFERENCE.md（REST API仕様） |
| api-examples.md | 拡充 | → API_REFERENCE.md |
| data-model.md | 統合（古い内容） | → DATA_MODEL_REFERENCE.md |
| quick-start.md | 統合 | → README.md（クイックスタート） |
| distribution-guide.md | 統合 | → DISTRIBUTION_GUIDE.md（英語版統合） |

### ❌ 削除・移動

| ファイル | 処理 | 理由 |
|---------|------|------|
| mars-development-prompt.md | `/docs/`（ワークスペース）へ移動 | MARS統合情報、Oiduna単体には不要 |

---

## 新規作成ファイルの詳細仕様

### 1. ARCHITECTURE.md

**構成**:
```markdown
# Oiduna Architecture

## 設計哲学
- Oidunaのミッション
- 責任の分離（Oiduna vs Distribution）
- 設計原則

## システム構成
- パッケージ構成（oiduna_core/loop/api）
- 依存関係
- デプロイ構成

## 階層化IR設計
- なぜ階層化するのか
- 4層の詳細（Environment/Configuration/Pattern/Control）
- イミュータブル設計の理由
- 型安全性

## データフロー
- クライアント → Oiduna API → ループエンジン → SuperDirt/MIDI
- シーケンス図
- タイミングチャート

## 設計判断の記録
- なぜHTTP APIなのか
- なぜ256ステップ固定なのか
- なぜステップインデックスを使うのか
```

**元ネタ**: SPECIFICATION_v1.md（設計哲学、基本仕様）、OIDUNA_CONCEPTS.md

---

### 2. DATA_MODEL_REFERENCE.md

**構成**:
```markdown
# Oiduna Data Model Reference

## CompiledSession
- 構造全体図
- フィールド一覧

## Environment Layer
- Environment
- Chord

## Configuration Layer
### Audio Tracks
- Track
- TrackMeta
- TrackParams
- FxParams
- TrackFxParams
- Send

### MIDI Tracks
- TrackMidi

### Mixer Lines
- MixerLine
- MixerLineDynamics
- MixerLineFx

## Pattern Layer
- EventSequence
- Event
- ステップインデックス仕様

## Control Layer
- Scene
- ApplyCommand
- ApplyTiming

## Modulation
- Modulation
- SignalExpr
- StepBuffer

## シリアライゼーション
- JSON形式
- デシリアライズ仕様
- バリデーション
```

**元ネタ**: SPECIFICATION_v1.md（IRデータモデル）、data-model.md、実際のコード（`oiduna_core/ir/`）

---

### 3. PERFORMANCE.md

**構成**:
```markdown
# Oiduna Performance

## パフォーマンス特性
- ループエンジンのタイミング精度
- OSC/MIDI送信レイテンシ
- メモリ使用量

## ボトルネック分析
- EventSequence構築
- ステップインデックス検索
- OSC送信
- GIL（Global Interpreter Lock）

## 最適化ポイント
- O(1)検索の実装
- イミュータブル設計のメリット
- dataclass(slots=True)の効果

## ベンチマーク
- 小規模セッション（5トラック）
- 中規模セッション（20トラック）
- 大規模セッション（50トラック）

## スケーラビリティ
- 同時接続数の制限
- メモリスケーリング
```

**元ネタ**: architecture/GIL_MITIGATION.md、実測値、コード解析

---

### 4. API_REFERENCE.md

**構成**:
```markdown
# Oiduna API Reference

## ベースURL
## 認証（現状なし）

## Playback Endpoints
### POST /playback/pattern
### POST /playback/start
### POST /playback/stop
### GET /playback/status
### POST /playback/bpm

## SuperDirt Endpoints
### POST /superdirt/synthdef
### POST /superdirt/sample/load
### GET /superdirt/buffers

## MIDI Endpoints
### GET /midi/ports
### POST /midi/port

## SSE Stream
### GET /stream

## エラーレスポンス
## レート制限（今後実装予定）
```

**元ネタ**: api-examples.md、SPECIFICATION_v1.md（REST API仕様）、OpenAPI自動生成

---

### 5. USAGE_PATTERNS.md

**構成**:
```markdown
# Oiduna Usage Patterns

## 基本パターン
### シンプルなループ再生
### BPM変更
### トラックミュート/ソロ

## 中級パターン
### シーン切り替え
### MIDI出力
### SuperDirtサンプルロード

## 上級パターン
### リアルタイムパラメータモジュレーション
### 複数Oidunaインスタンスの同期

## アンチパターン
### やってはいけないこと

## トラブルシューティング
### SuperDirt接続エラー
### MIDI出力されない
### タイミングのずれ
```

**元ネタ**: api-examples.md、実際のユースケース

---

### 6. DEVELOPMENT_GUIDE.md

**構成**:
```markdown
# Oiduna Development Guide

## 開発環境セットアップ
## コードベース構造
## 新機能追加の手順
## テスト戦略
## デバッグ方法
## CI/CD
## リリースプロセス
## コントリビューションガイドライン
```

**元ネタ**: 実際の開発プロセス、CONTRIBUTING.md（未作成）

---

## 実装計画

### Phase 1: 新規ファイル作成（優先度高）

| ファイル | 工数 | 優先度 |
|---------|------|--------|
| ARCHITECTURE.md | 1日 | 🔴 高 |
| DATA_MODEL_REFERENCE.md | 1.5日 | 🔴 高 |
| API_REFERENCE.md | 0.5日 | 🔴 高 |

### Phase 2: 新規ファイル作成（優先度中）

| ファイル | 工数 | 優先度 |
|---------|------|--------|
| PERFORMANCE.md | 1日 | 🟡 中 |
| USAGE_PATTERNS.md | 0.5日 | 🟡 中 |

### Phase 3: リファクタ

| タスク | 工数 | 優先度 |
|-------|------|--------|
| README.md更新 | 0.5日 | 🔴 高 |
| SPECIFICATION_v1.md分割・統合 | 1日 | 🟡 中 |
| 古いファイル削除・移動 | 0.5日 | 🟢 低 |

### Phase 4: 開発者向け

| ファイル | 工数 | 優先度 |
|---------|------|--------|
| DEVELOPMENT_GUIDE.md | 1日 | 🟢 低 |

**総工数**: 約7.5日

---

## ドキュメント間の参照関係

```
README.md
  └→ OIDUNA_CONCEPTS.md
       └→ TERMINOLOGY.md
       └→ ARCHITECTURE.md
            └→ DATA_MODEL_REFERENCE.md
            └→ PERFORMANCE.md
       └→ API_REFERENCE.md
            └→ USAGE_PATTERNS.md
       └→ DEVELOPMENT_GUIDE.md
            └→ DISTRIBUTION_GUIDE.md
```

---

## 成功基準

このドキュメント体系が成功したと言える条件：

1. ✅ **新規ユーザー**がREADME → OIDUNA_CONCEPTS → API_REFERENCEを読んで、1時間以内に最初のパターンを再生できる
2. ✅ **開発者**がARCHITECTURE → DATA_MODEL_REFERENCEを読んで、システム設計を完全に理解できる
3. ✅ **最適化担当者**がPERFORMANCE.mdを読んで、ボトルネックを特定し改善できる
4. ✅ **Distribution作者**がDISTRIBUTION_GUIDEを読んで、独自のDSLを実装できる
5. ✅ **ユースケース熟知者**がこれらのドキュメントをレビューして、性能向上/リファクタの提案ができる

---

## 次のステップ

1. ⬜ この再構成計画を確認・承認
2. ⬜ Phase 1の新規ファイル作成（ARCHITECTURE, DATA_MODEL_REFERENCE, API_REFERENCE）
3. ⬜ README.md更新
4. ⬜ Phase 2の新規ファイル作成（PERFORMANCE, USAGE_PATTERNS）
5. ⬜ 古いファイルの整理（SPECIFICATION_v1.md分割、不要ファイル削除）

---

**バージョン**: 1.0.0
**作成日**: 2026-02-24
**作成者**: Claude Code
**目的**: Oidunaドキュメントの網羅的で理解しやすい体系の確立
