# Architecture Decision Records (ADR)

このディレクトリには、ライブコーディングワークスペース全体の重要なアーキテクチャ決定を記録しています。

## ADRとは

Architecture Decision Record（ADR）は、ソフトウェアアーキテクチャにおける重要な決定とその理由を記録するドキュメントです。

**記録する理由:**
- なぜその決定をしたのか、将来振り返れるように
- 代替案を検討したことを明示
- 新規参加者が設計判断の背景を理解できるように
- 過去の失敗を繰り返さないように

## ADR一覧

### 承認済み

| 番号 | タイトル | 日付 | 概要 |
|------|----------|------|------|
| [0001](./0001-supernova-multicore-integration.md) | SuperDirt supernovaマルチコア処理の採用 | 2026-02-22 | scsynth → supernova移行、マルチコアCPU活用 |
| [0002](./0002-osc-confirmation-protocol.md) | OSC確認プロトコルの設計 | 2026-02-22 | 双方向OSC通信、コマンド実行確認、エラーハンドリング |
| [0003](./0003-python-timing-engine-phase1.md) | Phase 1でのPythonタイミングエンジン継続 | 2026-02-22 | Rust化はPhase 2以降、段階的アプローチ |

### 提案中

なし

### 非推奨・置き換え済み

なし

## ADR作成ガイド

### いつADRを書くべきか

以下のような決定を行う際にADRを作成してください：

✓ **書くべき決定:**
- アーキテクチャパターンの選択（マイクロサービス、モノリス等）
- 技術スタックの選択（言語、フレームワーク、データベース等）
- 重要なAPIの設計方針
- セキュリティ・パフォーマンスに関わる設計
- 後から変更が困難な決定

✗ **書かなくて良い決定:**
- コーディング規約（別ドキュメントで管理）
- 一時的な実験・プロトタイプ
- 簡単に後から変更できる実装の詳細
- プロジェクト固有すぎる小さな決定

### 作成手順

1. **テンプレートをコピー:**
   ```bash
   # 次の番号を確認
   ls knowledge/adr/ | grep -E '^[0-9]+' | tail -1

   # テンプレートをコピー
   cp templates/adr-template.md knowledge/adr/0004-your-title.md
   ```

2. **記入:**
   - ステータス: 「提案中」から開始
   - コンテキスト: 問題・制約・要件を明確に
   - 決定事項: 何をどう実装するか具体的に
   - 理由: なぜこの決定をしたか
   - 代替案: 他の選択肢とその長所・短所
   - 影響: プラス・マイナス・リスク

3. **レビュー:**
   - 他のメンバーに共有（該当する場合）
   - フィードバックを反映

4. **承認:**
   - ステータスを「承認済み」に変更
   - このREADMEに追加

5. **実装:**
   - ADRに基づいて実装
   - 実装時に新たに分かったことをメモに追記

### 命名規則

```
NNNN-short-kebab-case-title.md
```

- **NNNN:** 4桁の連番（0001, 0002, ...）
- **short-kebab-case-title:** 簡潔で分かりやすいタイトル（kebab-case）

**例:**
- `0001-supernova-multicore-integration.md`
- `0002-osc-confirmation-protocol.md`
- `0003-python-timing-engine-phase1.md`

### ステータスの意味

- **提案中:** 検討中、まだ実装していない
- **承認済み:** 決定して実装した、現在有効
- **非推奨:** 新規使用は推奨しないが、既存コードには残っている
- **置き換え済み:** 別のADRに置き換えられた（関連ADRを記載）

### ステータスの更新

決定が変更された場合、古いADRを削除せず、ステータスを更新します：

```markdown
## ステータス

置き換え済み（[ADR-0010: 新しい決定](./0010-new-decision.md)に置き換え）
```

新しいADRの「関連するADR」セクションに旧ADRへのリンクを記載。

## テンプレート

ADRテンプレートは [`/templates/adr-template.md`](../../../../templates/adr-template.md) にあります。

## 参考リンク

- [ADR GitHub Organization](https://adr.github.io/)
- [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
- [ADR Tools](https://github.com/npryce/adr-tools)

## メンテナンス

### 定期レビュー

四半期ごとにADRを見直し：

- 古くなった決定を「非推奨」に変更
- 新しい技術・状況に応じて再評価
- 実装状況と齟齬がないか確認

### アーカイブ

「置き換え済み」のADRは削除せず、履歴として保持します。
GitHubでの変更履歴も重要な情報源です。

---

**最終更新:** 2026-02-22
**管理者:** ワークスペースメンテナー
