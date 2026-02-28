# ADR 0012: Package Architecture - Layered Design and Module Separation

**Status**: Accepted

**Date**: 2026-03-01

**Deciders**: tobita, Claude Code

---

## Context

### Background

Oidunaは旧システムの単純な3層構造（API層、ループ層、出力層）から、12個のパッケージに分割された階層化アーキテクチャへと進化しました。この変更は以下の目的で行われました：

1. **Rust移植への準備**: 段階的な移植を可能にする
2. **拡張機能のサポート**: 明確なインターフェースでの拡張機能接続
3. **保守性の向上**: 責任の明確な分離
4. **Silent Failureの防止**: 適切な検証ロジックの配置

### 旧システムの問題点

```
┌─────────────────────────────────────────┐
│ API層 - すべてのロジックが混在          │
└─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│ ループ層 - データとロジックが密結合     │
└─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│ 出力層 - OSC/MIDI送信                   │
└─────────────────────────────────────────┘
```

**問題点**:
- API層にビジネスロジックが散在
- 検証ロジックがエンドポイント内に埋め込み
- データ構造が固定的で拡張困難
- Rust移植の範囲が不明確
- Silent Failure（存在しないデスティネーションを指定してもエラーにならない）

---

## Decision

### 5+1層アーキテクチャの採用（5層 + External Interface）

packages/以下を5つの明確な層に分割し、各層に独立したパッケージを配置。さらにExternal Interface（オプション）として外部クライアントツールを配置：

```
┌─────────────────────────────────────────────────┐
│ External Interface (Optional)                   │
│    - oiduna_cli, oiduna_client                  │
│    - HTTP通信のみ、他パッケージに依存しない     │
│    - テスト・開発用ツール                       │
└─────────────────────────────────────────────────┘
                    ↓ HTTP
┌─────────────────────────────────────────────────┐
│ 1. API層                                        │
│    - oiduna_api                                 │
│    - エンドポイント定義のみ（薄いラッパー）     │
└─────────────────────────────────────────────────┘
                    ↓
┌──────────────┬───────────────┬──────────────────┐
│ 2. ビジネス層│ 3. 認証層     │ 4. 通信層        │
│  session     │  auth         │  core            │
│              │               │                  │
│- Manager分離 │- Token認証    │- IPC Protocol    │
│- 検証ロジック│- Admin認証    │- 抽象インター    │
│- Compiler    │               │  フェース        │
└──────────────┴───────────────┴──────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ 5. スケジューリング層                            │
│    - oiduna_scheduler                           │
│    - O(1)高速検索インデックス、送信先非依存     │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ 6. 実行層                                        │
│    - oiduna_loop                                │
│    - ループエンジン、タイミング制御             │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ 7. データモデル層（Foundation）                 │
│    - oiduna_models                              │
│    - Pydanticバリデーション、型安全性           │
└─────────────────────────────────────────────────┘
```

### パッケージの役割と依存関係

#### External Interface: クライアント層

**oiduna_cli**
- **責任**: コマンドラインインターフェース
- **依存**: なし（HTTP通信のみ）
- **Rust移植優先度**: 中（配布の容易さ）

**oiduna_client**
- **責任**: Pythonクライアントライブラリ
- **依存**: なし（HTTP通信のみ）
- **Rust移植優先度**: 低（各言語で実装）

#### Layer 1: API層

**oiduna_api**
- **責任**: HTTP REST APIエンドポイント提供
- **依存**: session, loop, auth, models, destination
- **Rust移植優先度**: 低（Python FastAPIが成熟）
- **主要機能**:
  - `/clients/*`: クライアント管理
  - `/tracks/*`: トラック管理
  - `/tracks/{track_id}/patterns/*`: パターン管理
  - `/session/*`: セッション状態取得
  - `/playback/*`: 再生制御
  - `/stream`: SSEリアルタイムストリーム

#### Layer 2: ビジネスロジック層

**oiduna_session**
- **責任**: セッション状態の管理とビジネスロジック
- **依存**: models, destination, scheduler
- **Rust移植優先度**: 中
- **主要コンポーネント**:
  - `SessionContainer`: 全マネージャーの統合（Facade）
  - `ClientManager`: クライアント登録・認証トークン管理
  - `TrackManager`: トラック作成・削除・更新
  - `PatternManager`: パターン作成・更新・アクティブ切り替え
  - `DestinationManager`: デスティネーション追加・削除（使用中チェック）
  - `SessionCompiler`: Session → ScheduledMessageBatch変換

**設計原則**:
- **Single Responsibility**: 各Managerが単一の責任を持つ
- **Fail Fast**: デスティネーション存在確認など、作成時にエラー
- **明確なエラーメッセージ**: 利用可能なデスティネーション一覧を表示

#### Layer 3: 認証層

**oiduna_auth**
- **責任**: 認証・認可ロジック
- **依存**: なし（独立）
- **Rust移植優先度**: 低（セキュリティ要件による）
- **主要機能**:
  - クライアントトークン認証（UUID）
  - Admin パスワード認証
  - FastAPI依存性注入

#### Layer 4: 通信層

**oiduna_core**
- **責任**: IPC（プロセス間通信）プロトコル定義
- **依存**: なし
- **Rust移植優先度**: 最優先（インターフェース定義）
- **主要機能**:
  - MARSとOidunaの通信インターフェース定義
  - 抽象インターフェース（将来的なプロトコル変更に対応）

#### Layer 5: スケジューリング層

**oiduna_scheduler**
- **責任**: メッセージのインデックス化と高速検索
- **依存**: なし（独立）
- **Rust移植優先度**: 中（パフォーマンス重要）
- **主要モデル**:
  - `ScheduledMessage`: タイミング情報付きメッセージ
  - `ScheduledMessageBatch`: メッセージ群 + BPM + pattern_length
  - `MessageScheduler`: ステップ別インデックス（dict[int, list[int]]）

**重要な設計決定**:
- **フラット構造**: トラック階層を持たず、全メッセージをフラットに
- **O(1)検索**: ステップ番号から即座にメッセージ取得
- **送信先非依存**: `params: dict[str, Any]`で任意の送信先に対応

#### Layer 6: 実行層

**oiduna_loop**
- **責任**: リアルタイムループ再生エンジン
- **依存**: core
- **Rust移植優先度**: 最高（パフォーマンスクリティカル）
- **主要コンポーネント**:
  - `LoopEngine`: メインループエンジン
  - `ClockGenerator`: 256ステップクロック生成
  - `OSCSender`: SuperDirt等へのOSC送信
  - `MIDISender`: MIDI機器へのMIDI送信
  - `DestinationRouter`: 送信先別ルーティング

#### Layer 7: データモデル層（Foundation）

**oiduna_models**
- **責任**: ビジネスドメインのデータ構造定義と送信先設定
- **依存**: なし（完全に独立、最下層）
- **Rust移植優先度**: 最優先（データ構造は言語間で共有しやすい）
- **Foundation概念**: すべての層がこの層のモデルを使用し、この層は他のどの層にも依存しない
- **主要モデル**:
  - `Session`: セッション全体の状態
  - `Track`: 送信先とパラメータを持つトラック
  - `Pattern`: イベントのシーケンス
  - `Event`: 単一のトリガーイベント（step, cycle, params）
  - `ClientInfo`: 接続クライアント情報
  - `Environment`: BPM等の環境設定
  - `OscDestinationConfig`: SuperDirt等のOSC送信先
  - `MidiDestinationConfig`: MIDI機器送信先
  - `load_destinations`: YAML/JSON設定読み込み

### 依存関係マップ

```
oiduna_api → session, loop, auth, models
oiduna_session → models, scheduler
oiduna_loop → core
oiduna_auth → (独立)
oiduna_cli → (HTTP通信のみ)
oiduna_client → (HTTP通信のみ)
oiduna_core → (独立)
oiduna_models → (独立・Foundation)
oiduna_scheduler → (独立)
```

**設計原則**:
- **Foundation層**: oiduna_modelsは他のどの層にも依存しない最下層・基盤
- **独立したコンポーネント**: scheduler, auth, coreは独立
- **明確な依存方向**: 上から下への一方向のみ

---

## Consequences

### Positive

1. **Rust移植の明確な優先度**
   ```
   最優先: models, destination, core（データ構造定義）
   高優先: loop, scheduler（パフォーマンスクリティカル）
   中優先: session, cli（ビジネスロジック、配布）
   低優先: api, auth, client（Python成熟、言語別実装）
   ```

2. **拡張機能の接続が容易**
   ```
   拡張機能
     ├─ HTTP API (/extensions/*) → oiduna_api
     ├─ SSE受信 (/stream) ← リアルタイム通知
     └─ ScheduledMessageBatch送信 → oiduna_scheduler
   ```

3. **Silent Failureの防止**
   ```python
   # 旧: 実行時までエラーに気づかない
   track.destination_id = "typo"  # OK → Silent Failure

   # 新: 作成時にエラー
   container.tracks.create(
       destination_id="typo"  # ValueError即座に発生
   )
   ```

4. **テスタビリティの向上**
   - ユニットテスト: 各Managerを独立テスト
   - 結合テスト: SessionContainer全体をテスト
   - E2Eテスト: HTTP API → LoopEngineまで
   - テスト数: 649テスト（92%カバレッジ）

5. **保守性の向上**
   - 各パッケージが100-300行程度
   - 責任が明確
   - 変更の影響範囲が限定的

### Negative

1. **パッケージ数の増加**
   - 3パッケージ → 12パッケージ
   - 初見の学習コストが増加
   - **軽減策**: 本ADRと階層図で全体像を文書化

2. **依存関係の管理コスト**
   - パッケージ間の依存関係の把握が必要
   - **軽減策**: 依存方向を一方向に制限、独立パッケージを多く保つ

3. **インポートパスの増加**
   ```python
   # 旧: from oiduna import ...
   # 新: from oiduna_models import ...
   #     from oiduna_session import ...
   ```
   - **軽減策**: 各パッケージの`__init__.py`で主要なエクスポート

### Neutral

- **複雑性**: 見かけ上は複雑だが、各層の責任は明確
- **MARSとの統合**: `ScheduledMessageBatch`の共通フォーマットで統一

---

## Related Decisions

- **ADR-0010**: SessionContainer Pattern（Manager分離の基礎）
- **ADR-0008**: Code Quality Refactoring Strategy（リファクタリング戦略）
- **ADR-0007**: Destination-Agnostic Core（送信先非依存設計）
- **ADR-0011**: Rust Acceleration Strategy（Rust移植計画）

---

## Data Flow Example

### 完全なフロー（クライアント作成 → トラック作成 → コンパイル → 再生）

```
1. HTTP Request
   POST /clients/alice
   ↓
2. oiduna_api
   routes/clients.py → container.clients.create()
   ↓
3. oiduna_session
   ClientManager.create()
     → models.ClientInfo生成
     → session.clients[id] = client
   ↓
4. HTTP Request
   POST /tracks/kick
   ↓
5. oiduna_api
   routes/tracks.py → container.tracks.create()
   ↓
6. oiduna_session
   TrackManager.create()
     → DestinationManager.get() で存在確認
     → models.Track生成
     → session.tracks[id] = track
   ↓
7. コンパイル
   SessionCompiler.compile(session)
     → ScheduledMessageBatch生成
   ↓
8. oiduna_scheduler
   MessageScheduler(batch)
     → ステップ別インデックス構築
   ↓
9. oiduna_loop
   LoopEngine.sync(scheduler)
     → ClockGenerator → ステップ進行
     → scheduler.get_at_step(step)
     → DestinationRouter
        ├→ OSCSender → SuperDirt
        └→ MIDISender → MIDI機器
```

---

## Implementation Notes

### パッケージ作成のガイドライン

新しいパッケージを追加する場合：

1. **層の決定**: 6層のどこに属するか明確にする
2. **依存関係の確認**: 下位層のみに依存する
3. **責任の明確化**: Single Responsibilityを守る
4. **テストの追加**: 独立したユニットテストを用意
5. **ドキュメント**: `__init__.py`のdocstringで役割を説明

### Rust移植の手順

1. **Phase 1**: models, destination（データ構造）
2. **Phase 2**: scheduler（最適化層）
3. **Phase 3**: loop（実行層）
4. **Phase 4**: session（ビジネスロジック）

各フェーズで：
- Pydanticモデル → Rust struct + serde
- Python型ヒント → Rust型システム
- JSONシリアライズで互換性維持

---

## References

### ドキュメント
- **[docs/architecture/](../../architecture/README.md)** - 各層の詳細ドキュメント（本ADRの詳細版）
  - [External Interface: クライアント層](../../architecture/external-interface.md)
  - [Layer 1: API層](../../architecture/layer-1-api.md)
  - [Layer 2: アプリケーション層](../../architecture/layer-2-application.md)
  - [Layer 3: コア層](../../architecture/layer-3-core.md)
  - [Layer 4: ドメイン層](../../architecture/layer-4-domain.md)
  - [Layer 5: データ層](../../architecture/layer-5-data.md)
  - [Quick Reference](../../architecture/QUICK_REFERENCE.md) - 要点まとめ
- **[docs/ARCHITECTURE.md](../../ARCHITECTURE.md)** - システム全体像
- **`packages/*/README.md`** - 各パッケージの詳細

### テスト
- **`tests/integration/`** - 層をまたぐ統合テスト
- **`packages/*/tests/`** - 各パッケージのユニットテスト

---

**Author**: Claude Code
**Reviewed by**: tobita
**Last Updated**: 2026-03-01
