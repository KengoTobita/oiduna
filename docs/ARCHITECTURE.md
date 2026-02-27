# システム全体像ドキュメント

**バージョン**: 2.0.0
**更新日**: 2026-02-23

> **Single Source of Truth**: このドキュメントはシステムのアーキテクチャと設計意図を説明します。技術スタックの詳細、ポート番号、エンドポイントリスト、ファイル構成などはコードと設定ファイルを参照してください。

## 目次

1. [プロジェクト概要](#1-プロジェクト概要)
2. [アーキテクチャ](#2-アーキテクチャ)
3. [なぜこの設計なのか](#3-なぜこの設計なのか)
4. [通信フロー](#4-通信フロー)
5. [詳細情報の参照方法](#5-詳細情報の参照方法)

---

## 1. プロジェクト概要

### 1.1 全体の目的

ライブコーディング環境において、**表現力の高いDSL言語**から**リアルタイムオーディオ制御**まで、シームレスに統合されたシステムを提供すること。

### 1.2 主要コンポーネント

#### Oiduna - リアルタイムループエンジン

**責任**: パターンデータをリアルタイムでSuperDirtとMIDIデバイスに出力

**なぜ存在するのか**:
- ライブパフォーマンス中に即座にパターンを変更したい
- SuperDirtとMIDI両方に対応した統一インターフェースが必要
- HTTPでリモートコントロール可能にしたい

**主要機能**:
- 256ステップループエンジン（16ビート）
- SuperDirt OSC出力
- MIDI出力
- HTTP REST API
- SSEによるリアルタイム状態配信

詳細: `oiduna/README.md`、`oiduna/pyproject.toml`

#### MARS - DSLコンパイラ

**責任**: 高レベルDSL言語をOidunaの中間表現にコンパイル

**なぜ存在するのか**:
- 簡潔な構文で複雑なパターンを記述したい
- プロジェクト管理機能が必要
- Webベースのエディタで編集したい

**主要機能**:
- DSL v3.1パーサー（Larkベース）
- プロジェクト/ソング/クリップ管理
- Webベースエディタ
- Oiduna統合

詳細: `Modular_Audio_Real-time_Scripting/README.md`、`MARS_for_oiduna/README.md`

---

## 2. アーキテクチャ

### 2.1 全体データフロー

```
┌─────────────────────────────────────────────────────────────┐
│ ユーザー                                                     │
│   ↓ MARS DSLコード                                          │
├─────────────────────────────────────────────────────────────┤
│ MARS DSL Compiler                                           │
│   ├─ Larkパーサー (DSL → AST)                               │
│   ├─ RuntimeSession生成 (mars_dsl)                          │
│   └─ ScheduledMessageBatch変換                             │
│     ↓ HTTP POST /playback/session (JSON)                    │
├─────────────────────────────────────────────────────────────┤
│ Oiduna Loop Engine                                          │
│   ├─ ScheduledMessageBatchデシリアライズ                    │
│   ├─ MessageScheduler インデックス化（O(1)ルックアップ）    │
│   └─ ループ再生                                             │
│     ├─ OSCメッセージ → SuperCollider → サウンド再生         │
│     └─ MIDIメッセージ → MIDIデバイス → サウンド再生         │
└─────────────────────────────────────────────────────────────┘
        ↑ SSE /stream (リアルタイム状態配信)
      ユーザー
```

**なぜこのフロー**:
- **DSLとエンジンの分離**: それぞれを独立して進化させられる
- **HTTP通信**: 任意のフロントエンドから制御可能
- **JSON形式**: 言語非依存、デバッグ容易

### 2.2 ScheduledMessageBatchアーキテクチャ

```
┌───────────────────────────────────────────────────────────┐
│ ScheduledMessageBatch                                     │
│                                                           │
│  messages: tuple[ScheduledMessage, ...]                   │
│    ├─ destination_id: str  (例: "superdirt", "volca")    │
│    ├─ cycle: float         (サイクル位置: 0.0-4.0)       │
│    ├─ step: int            (ステップ番号: 0-255)         │
│    └─ params: dict[str, Any]  (送信先依存パラメータ)     │
│                                                           │
│  bpm: float                (テンポ: 120.0)                │
│  pattern_length: float     (パターン長: 4.0サイクル)      │
└───────────────────────────────────────────────────────────┘
        ↓
MessageScheduler (oiduna_scheduler)
  ├─ ステップ別インデックス構築 (dict[int, list[int]])
  └─ O(1)高速ルックアップ
```

**なぜフラット構造なのか**:

1. **Destination-Agnostic（送信先非依存）**
   - SuperDirt、MIDI、カスタム送信先を統一的に扱える
   - 拡張機能で新しい送信先を追加可能

2. **シンプルさ**
   - 階層構造を持たず、フラットなメッセージリスト
   - デバッグと理解が容易

3. **効率的なリアルタイム処理**
   - MessageSchedulerがステップ別インデックスを構築
   - O(1)で特定ステップのメッセージ検索が可能
   - リアルタイム再生時の高速検索を実現

詳細: `packages/oiduna_scheduler/scheduler_models.py`

### 2.3 コンポーネント構成

```
┌──────────────────────────────────────────────────────────┐
│ MARS_for_oiduna (HTTP API)                               │
│                                                          │
│  mars_api (FastAPI)                                      │
│    ├─ mars_dsl (コンパイラ)                              │
│    ├─ ProjectManager (プロジェクト永続化)                │
│    └─ OidunaClient (HTTP通信)                            │
│          │                                               │
│          ↓ HTTP                                          │
├──────────────────────────────────────────────────────────┤
│ oiduna (HTTP API)                                        │
│                                                          │
│  oiduna_api (FastAPI)                                    │
│    └─ oiduna_loop (ループエンジン)                       │
│         └─ oiduna_core (IRモデル)                        │
│              │                                           │
│              ├─ OSC → SuperCollider + SuperDirt          │
│              └─ MIDI → MIDIデバイス                      │
└──────────────────────────────────────────────────────────┘
                ↓ ファイルシステム
┌──────────────────────────────────────────────────────────┐
│ project_data/ (プロジェクト保存)                          │
│  └─ {project}/                                           │
│      ├─ project.json                                     │
│      └─ songs/{song}/clips/{clip}.json                   │
└──────────────────────────────────────────────────────────┘
```

**責任の分離**:
- **mars_dsl**: DSLコンパイル（構文解析、最適化）
- **mars_api**: プロジェクト管理、HTTP API
- **oiduna_loop**: リアルタイム再生エンジン
- **oiduna_api**: 再生制御、トラック管理、HTTP API

### 2.4 MARSとOidunaのデータ交換

MARS DSL (mars_dsl) と Oiduna (oiduna_scheduler) は共通のScheduledMessageBatch形式でデータを交換します。

**MARSの役割**:
- DSLコンパイラの出力をScheduledMessageBatchに変換
- 高レベルな構造（Track、Environment等）からフラットなメッセージリストへの変換

**Oidunaの役割**:
- ScheduledMessageBatchをループエンジンで再生
- MessageSchedulerによるインデックス化
- DestinationRouterによる送信先別振り分け

**なぜこの形式なのか**:
- **送信先非依存**: params: dict[str, Any]により任意の送信先に対応
- **柔軟性**: MARS以外のDSLやフロントエンドもOidunaを使用できる
- **拡張性**: ExtensionPipelineによるメッセージ変換が可能

詳細: `packages/oiduna_scheduler/scheduler_models.py`

---

## 3. なぜこの設計なのか

### 3.1 イミュータブルデータ構造

すべてのIRモデルは`dataclass(frozen=True)`でイミュータブルです。

**理由**:
- **予測可能性**: データの状態が変わらないため、デバッグが容易
- **並行性**: マルチスレッド環境で安全
- **キャッシュ**: ハッシュ可能なため、効率的なキャッシングが可能

### 3.2 型安全性

Pythonの型ヒントを完全に使用し、mypyで厳密に型チェックしています。

**理由**:
- **コンパイル時エラー検出**: 実行前に型エラーを発見
- **ドキュメントとしての型**: コードが自己文書化される
- **IDEサポート**: 自動補完とリファクタリング支援

### 3.3 HTTP APIによる分離

MARS APIとOiduna APIは別々のHTTPサーバーです。

**理由**:
- **独立したデプロイ**: それぞれを独立してスケール可能
- **フロントエンドの柔軟性**: 任意のクライアントから制御可能（CLI、Web UI、他のプログラミング言語）
- **テスト容易性**: 各APIを独立してテスト可能

### 3.4 SSE（Server-Sent Events）

Oiduna APIはSSEでリアルタイム状態を配信します。

**理由**:
- **シンプルさ**: WebSocketより実装が簡単
- **一方向通信**: サーバーからクライアントへの状態配信のみで十分
- **HTTP互換**: 既存のHTTPインフラをそのまま使用可能

### 3.5 プロジェクト管理のJSON永続化

プロジェクト、ソング、クリップはJSONファイルとして保存されます。

**理由**:
- **シンプルさ**: データベース不要、ファイルシステムのみで動作
- **可読性**: テキストエディタで直接編集可能
- **バージョン管理**: Gitなどのバージョン管理システムで管理可能
- **移植性**: プロジェクトディレクトリをコピーするだけで移行可能

---

## 4. 通信フロー

### 4.1 コンパイル＆適用フロー

```
1. ユーザー → MARS API
   POST /compile/apply
   Body: {dsl: "Track(\"bd\"):\n    ..."}

2. MARS API内部
   ├─ DSL → Larkパーサー
   ├─ AST → RuntimeSession
   └─ RuntimeSession → ScheduledMessageBatch

3. MARS API → Oiduna API
   POST /playback/session
   Body: ScheduledMessageBatch JSON
   {
     "messages": [
       {"destination_id": "superdirt", "step": 0, "params": {...}},
       ...
     ],
     "bpm": 120.0,
     "pattern_length": 4.0
   }

4. Oiduna API内部
   ├─ JSON → ScheduledMessageBatchデシリアライズ
   ├─ MessageScheduler インデックス化（ステップ別dict作成）
   └─ ループエンジンに適用

5. ループ再生開始
   ├─ DestinationRouter → OSC送信 → SuperCollider
   └─ DestinationRouter → MIDI送信 → MIDIデバイス
```

**重要なポイント**:
- **ステップ2とステップ3の分離**: DSLコンパイルとループエンジンが独立
- **ステップ4のMessageScheduler**: リアルタイム再生のための高速検索インデックス作成
- **ステップ5のDestinationRouter**: 送信先別の自動振り分け

### 4.2 プロジェクト管理フロー

```
プロジェクト作成
  → ソング作成
    → クリップ作成（DSLコード含む）
      → クリップ適用
        ├─ DSLコンパイル (MARS API)
        └─ パターン適用 (Oiduna API)
```

**永続化**:
- プロジェクト: `project_data/{project}/project.json`
- ソング: `project_data/{project}/songs/{song}/song.json`
- クリップ: `project_data/{project}/songs/{song}/clips/{clip}.json`

### 4.3 リアルタイムストリーム（SSE）

```
1. ユーザー → Oiduna API
   GET /stream
   Accept: text/event-stream

2. Oiduna API → ユーザー
   HTTP 200
   Content-Type: text/event-stream

3. ループ再生中、毎ビート繰り返し
   data: {"step": 64, "bpm": 120, "playing": true, ...}
   (空行2つで終端)
```

**用途**: WebベースのUIでリアルタイムに現在のステップ位置、BPM、再生状態を表示

---

## 5. 詳細情報の参照方法

このドキュメントは概念とアーキテクチャを説明しています。具体的な詳細情報は以下を参照してください。

### 技術スタック詳細

**Oiduna**:
- `oiduna/pyproject.toml` - 依存ライブラリとバージョン
- `oiduna/README.md` - プロジェクト概要

**MARS**:
- `Modular_Audio_Real-time_Scripting/pyproject.toml` - 依存ライブラリとバージョン
- `Modular_Audio_Real-time_Scripting/README.md` - プロジェクト概要

### ポート番号とエンドポイント

**設定ファイル**:
- Oiduna: 環境変数（`API_PORT`など）、デフォルトはコード参照
- MARS: 設定ファイルまたはコード参照

**エンドポイントリスト**:
- **自動生成ドキュメント**: サーバー起動後、`http://localhost:{port}/docs` にアクセス（Swagger UI）
- **コード**: `oiduna_api/routes/`、`mars_api/routes/` のFastAPIルーター

### ファイル構成

**実際のファイルシステム**: `tree`コマンドまたはファイルエクスプローラーで確認

### データモデル

**コード**:
- Oiduna Core IR: `oiduna/packages/oiduna_core/ir/`
- MARS DSL Runtime: `Modular_Audio_Real-time_Scripting/mars_dsl/models.py`

**ドキュメント**: [データモデルリファレンス](03_データモデルリファレンス.md)

### 開発状況

**テスト実行**:
```bash
cd oiduna && uv run pytest
cd Modular_Audio_Real-time_Scripting && uv run pytest
```

**型チェック**:
```bash
cd oiduna && uv run mypy packages
cd Modular_Audio_Real-time_Scripting && uv run mypy apps packages
```

---

## 関連ドキュメント

- [MIGRATION_GUIDE_SCHEDULED_MESSAGE_BATCH.md](MIGRATION_GUIDE_SCHEDULED_MESSAGE_BATCH.md) - アーキテクチャ統合マイグレーションガイド
- [archive/ARCHITECTURE_UNIFICATION_COMPLETE.md](archive/ARCHITECTURE_UNIFICATION_COMPLETE.md) - アーキテクチャ統合完了記録 (archive)
- [DATA_MODEL_REFERENCE.md](DATA_MODEL_REFERENCE.md) - データモデル設計と参照
- [ADR一覧](knowledge/adr/) - 重要な設計判断の記録
- [../IMPLEMENTATION_COMPLETE.md](../IMPLEMENTATION_COMPLETE.md) - Phase 1-5完了サマリー (API層)
- [knowledge/adr/0010-session-container-refactoring.md](knowledge/adr/0010-session-container-refactoring.md) - SessionContainer ADR

---

**バージョン**: 2.1.0 (SessionContainer追加版)
**更新日**: 2026-02-28 (Phase 5完了)
**作成者**: Claude Code
**ドキュメント方針**: アーキテクチャと設計意図のみ記載、詳細はコードと設定ファイルを参照

> **Note**: このドキュメントは主にデータフローとコアループエンジンを説明します。API層（SessionContainer、REST API等）の詳細は上記リンクを参照してください。
