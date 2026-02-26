# ADR 0005: Oiduna Client + CLI - 軽量開発ツールの導入

**ステータス:** 承認済み
**日付:** 2026-02-22
**決定者:** ユーザー, Claude Code

---

## コンテキスト

### 背景

Phase 1 完了後、Oiduna の各機能（SynthDef ロード、サンプルロード、パターン実行等）をテスト・検証する必要があります。

### 問題点

**現状の課題:**

1. **テスト手段の不足**
   - 現在、Oiduna を操作する唯一の方法は MARS_for_oiduna（フルスタックディストリビューション）
   - MARS DSL のコンパイラ開発が進まないと Oiduna 自体のテストができない
   - 開発のボトルネックになる可能性

2. **手動確認の困難さ**
   - 各機能を手動で確認するには curl コマンドを直接叩く必要がある
   - JSON を手書きするのは非効率的
   - エラーハンドリングが分かりにくい

3. **自動化の欠如**
   - Claude Code から Oiduna を操作したい（自動化・検証）
   - 機械可読な出力フォーマットが必要
   - スクリプト化可能な CLI が望ましい

### ユーザーの要望

> "かんたんに各機能を人間である私が確かめる的なものがあるとoidunaの開発上楽かなって。MARSのDSLの進捗とかが開発のボトルネックになりかねないから。"

> "一つ抜けている点としてこのoiduna_client_cliはClaude code側からも扱うことを頭に入れておいて。"

---

## 決定

**Phase 2.1 で以下を実装する：**

### 1. oiduna_client（Python ライブラリ）

- Oiduna HTTP API をラップする非同期クライアントライブラリ
- Pydantic モデルで型安全な API 提供
- httpx ベースの非同期実装

**提供クライアント:**
- `OidunaClient` - 統合クライアント
- `PatternClient` - パターン操作
- `SynthDefClient` - SynthDef ロード
- `SampleClient` - サンプル管理
- `HealthClient` - ヘルスチェック

### 2. oiduna_cli（CLI ツール）

- コマンドモード + インタラクティブ REPL の2モード
- Click フレームワークベース
- Rich/prompt-toolkit で UX 向上

**提供コマンド:**
- `oiduna play <pattern>` - パターン実行
- `oiduna validate <pattern>` - 検証のみ
- `oiduna synthdef load <file>` - SynthDef ロード
- `oiduna sample load <cat> <path>` - サンプルロード
- `oiduna status` - ヘルスチェック
- `oiduna repl` - インタラクティブモード

**Claude Code 対応:**
- `--json` フラグで機械可読な JSON 出力
- 明確な終了コード（0/1/2/3/4）
- stderr/stdout の適切な使い分け

### 3. サンプルファイル

- Oiduna IR 形式のパターンファイル（4種類）
- SynthDef ファイル（3種類）
- 即座にテスト可能な状態で提供

---

## 代替案と検討結果

### 代替案A: curl + JSON ファイルで手動テスト

**内容:**
- curl コマンドで直接 Oiduna API を叩く
- JSON ファイルを手書きで作成

**却下理由:**
- 非効率的（毎回 curl コマンドを書く必要）
- エラーハンドリングが困難
- Claude Code から扱いにくい
- タイプセーフでない

### 代替案B: MARS_for_oiduna のみで開発継続

**内容:**
- フルスタックディストリビューションの開発を優先
- Oiduna のテストは MARS DSL 経由で実施

**却下理由:**
- MARS DSL 開発がボトルネックになる
- Oiduna 単体のテストが困難
- 開発サイクルが遅くなる

### 代替案C: Postman 等の GUI ツールを使用

**内容:**
- Postman, Insomnia 等の API テストツールを使用
- コレクションを作成して管理

**却下理由:**
- Claude Code から扱えない
- バージョン管理が困難
- CLI ベースのワークフローに合わない
- 自動化しにくい

### 代替案D: Python スクリプトで都度実装

**内容:**
- テストの度に Python スクリプトを書く
- httpx で直接 API を叩く

**却下理由:**
- 再利用性が低い
- タイプセーフでない
- メンテナンスコストが高い
- 統一されたインターフェースがない

---

## 決定理由

### 1. 開発加速

**問題解決:**
- MARS DSL 開発と並行して Oiduna をテスト可能
- Oiduna の各機能を即座に検証できる
- 開発のボトルネック解消

**メリット:**
- Phase 2 以降の開発がスムーズに進む
- 早期にバグ・問題を発見できる

### 2. DI（Dependency Injection）的アプローチ

**設計思想:**
- Oiduna は「コア API」に専念
- ディストリビューションは「ユーザー体験」に専念
- 軽量クライアントで両者を橋渡し

**参照元:**
> "DI的な意味でのディストリビューションクライアントがあるといいかも。"

### 3. Claude Code 統合

**要件:**
- Claude Code（自動化エージェント）から Oiduna を操作したい
- 機械可読な出力（JSON）が必須
- スクリプト化可能な CLI

**実装:**
- `--json` フラグで JSON 出力
- 明確な終了コード
- subprocess から簡単に呼び出せる設計

### 4. 再利用可能なライブラリ

**oiduna_client の利点:**
- 他のツール・スクリプトから再利用可能
- 型安全な API（Pydantic）
- テスタビリティが高い（DI、モック可能）

**将来の展開:**
- MARS_for_oiduna からも oiduna_client を利用可能
- サードパーティのディストリビューションでも利用可能

### 5. 実装コストの妥当性

**工数見積もり:**
- oiduna_client: 3-4日
- oiduna_cli: 3-4日
- サンプルファイル: 1日
- ドキュメント: 1日
- **合計: 8-10日（Phase 2.1 全体で Phase 2 の 1/3 程度）**

**投資対効果:**
- Phase 2 以降の開発効率が大幅に向上
- テスト・検証が容易になる
- 長期的なメンテナンスコスト削減

---

## 影響

### Phase ロードマップへの影響

**Phase 2 の再構成:**

```
Phase 2 (信頼性・品質向上) → 3つのサブフェーズに分割

Phase 2.0: リクエストID導入（2-3日）
Phase 2.1: 開発ツール（8-10日）← NEW
  - oiduna_client
  - oiduna_cli
  - サンプルファイル
Phase 2.2: 検証・品質向上（7-10日）
  - SynthDef検証
  - サンプルメタデータ
  - エラーハンドリング強化
  - 統合テスト
```

**全体スケジュールへの影響:**
- Phase 2 全体: 2-3週間 → 変わらず
- Phase 2.1 を Phase 2 の早期に実施することで、Phase 2.2 以降の開発が加速

### 技術スタックへの影響

**新規依存関係:**
- httpx（非同期HTTPクライアント）
- click（CLI フレームワーク）
- rich（リッチ出力）
- prompt-toolkit（REPL）

**既存コードへの影響:**
- なし（新規パッケージとして独立）

### ディストリビューションへの影響

**MARS_for_oiduna:**
- oiduna_client を内部で利用可能（オプション）
- 独自の DSL コンパイラに専念できる

**その他のディストリビューション:**
- oiduna_client を再利用可能
- 独自の UI・UX に注力できる

---

## トレードオフ

### メリット

1. **開発速度向上**
   - Oiduna 単体でテスト可能
   - 早期バグ発見

2. **再利用性**
   - oiduna_client は汎用ライブラリ
   - 他のツールから利用可能

3. **自動化対応**
   - Claude Code から扱いやすい
   - CI/CD に統合可能

4. **型安全性**
   - Pydantic によるバリデーション
   - IDE 補完が効く

### デメリット

1. **Phase 2 の工数増加**
   - 8-10日の追加実装
   - ただし長期的にはペイする

2. **メンテナンスコスト**
   - 新しいパッケージの追加
   - ドキュメント・テストの維持

3. **機能重複の可能性**
   - MARS_for_oiduna と一部機能が重複
   - ただし目的が異なる（テストツール vs プロダクション）

---

## 実装方針

### 設計原則

1. **シンプル・軽量**
   - 最小限の機能に絞る
   - 複雑な抽象化は避ける

2. **型安全**
   - Pydantic でリクエスト・レスポンスを定義
   - mypy チェック通過

3. **テスタブル**
   - DI で httpx.AsyncClient を注入
   - モック可能な設計

4. **Claude Code フレンドリー**
   - JSON 出力モード必須
   - 明確な終了コード
   - stderr/stdout 使い分け

### 実装範囲

**含む:**
- 全 Oiduna API エンドポイントのラッパー
- 基本的な CLI コマンド
- インタラクティブ REPL
- サンプルファイル（IR + SynthDef）

**含まない（Phase 3 以降）:**
- パターン生成・変換ロジック
- 高度な UI（Web UI）
- ユーザー認証・管理
- プロジェクト管理機能

---

## 検証方法

### 完了条件

1. **oiduna_client**
   - 全エンドポイント対応完了
   - ユニットテストカバレッジ 80%+
   - 実際の Oiduna API で動作確認

2. **oiduna_cli**
   - 全コマンド実装完了
   - REPL モード動作確認
   - JSON 出力モード動作確認
   - Claude Code から呼び出し確認

3. **サンプルファイル**
   - 最低4パターン + 3 SynthDef 提供
   - 実際に動作することを確認

4. **ドキュメント**
   - README, USAGE, EXAMPLES 完備
   - この ADR の作成

### テスト計画

**ユニットテスト:**
- oiduna_client の各クライアントメソッド
- CLI コマンドの動作（CliRunner）

**統合テスト（手動）:**
- 実際の Oiduna API との接続
- 全コマンドの動作確認
- Claude Code からの呼び出し

---

## 参考資料

- `knowledge/research/oiduna-cli-design.md` - 設計書
- `knowledge/handoff/oiduna-client-cli-implementation-spec.md` - 実装仕様書
- `knowledge/adr/0004-phase-roadmap-v2.md` - Phase ロードマップ
- `knowledge/discussions/2026-02-22-distribution-design.md` - ディストリビューション設計

---

## まとめ

**決定:**
Phase 2.1 で oiduna_client + oiduna_cli を実装する。

**理由:**
- MARS DSL 開発をボトルネックにしない
- Oiduna の開発・テストを加速
- Claude Code 統合で自動化を実現
- 再利用可能なライブラリ提供

**影響:**
- Phase 2 に 8-10日の追加工数
- 長期的な開発効率向上
- ディストリビューション開発の加速

**次のステップ:**
別エージェントに実装仕様書を引き継ぎ、Phase 2.1 の実装を開始する。

---

**記録者:** Claude Code
**承認者:** ユーザー
**実装担当:** 別エージェント（予定）
