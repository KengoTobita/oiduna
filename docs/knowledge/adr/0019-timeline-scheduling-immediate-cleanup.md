# ADR-0019: Timeline Scheduling with Immediate Cleanup

**Status**: Accepted
**Date**: 2026-03-11
**Deciders**: Claude Sonnet 4.5, tobita

---

## Context

Oidunaにライブコーディングセッションでの計画的な楽曲構成を可能にするため、複数ループ先のパターン変更を予約できるタイムラインスケジューリング機能が必要となった。

### 要求事項

1. **グローバルステップ基準**: 累積ステップ数で予約（停止後も継続）
2. **複数予約のマージ**: 同一ステップの複数予約を1回で適用（パフォーマンス最適化）
3. **CRUD操作**: UUID管理による予約の作成・取得・編集・キャンセル
4. **長時間演奏対応**: DJ setやライブパフォーマンス（数時間）でもメモリ安定
5. **リアルタイム性**: BPM 180（83ms/step）でも音飛びなし

### 技術的課題

- **メモリ管理**: 長時間セッションで予約履歴が蓄積するとメモリ圧迫
- **パフォーマンス**: 毎ステップ（最速83ms）での処理が必要
- **履歴管理**: 過去の予約データをどう扱うか

---

## Decision

### 1. 即時削除アーキテクチャを採用

**適用済み予約は即座に削除**し、**未来の予約のみメモリに保持**する。

```python
def apply_changes_at_step(global_step, timeline, scheduler):
    changes = timeline.get_changes_at(global_step)
    if not changes:
        timeline.cleanup_past(global_step)
        return False

    # 適用
    merged_batch = merge_changes(changes)
    scheduler.load_messages(merged_batch)

    # ★即座に削除
    for change in changes:
        timeline.cancel_change(change.change_id)
    timeline.cleanup_past(global_step)  # 過去の未適用も削除

    return True
```

### 2. メモリ上に残るデータ

- **未来の予約のみ**: `target_global_step > current_global_step`
- **過去のデータは一切保持しない**

### 3. 履歴管理は拡張機能に委譲

**SSEイベント**を発行し、履歴記録は外部システムで対応：

```python
# TimelineManager が発行するイベント
"change_scheduled"   # 予約作成時
"change_updated"     # 予約更新時
"change_cancelled"   # 予約キャンセル時
```

ログサーバーやフロントエンドで必要に応じて記録可能。

---

## Rationale

### 即時削除を選んだ理由

#### メリット

1. **メモリ効率**
   - 3時間のDJ set（BPM 120, 8秒/予約）でも約2-3MBで安定
   - 履歴を保持すると41MB以上に増加

2. **シンプルな実装**
   - タイムラインは未来だけ管理、過去は考慮不要
   - デバッグが容易（状態が単純）

3. **パフォーマンス**
   - cleanup処理が軽量（未来のデータ量のみに依存）
   - メモリアクセスパターンが予測可能

4. **リアルタイム用途に適合**
   - ライブコーディングでは「これから何が起こるか」が重要
   - 過去の履歴よりも未来の予定が価値がある

#### デメリットと対策

| デメリット | 対策 |
|-----------|------|
| 予約履歴が見れない | SSEイベントで外部記録 |
| 適用確認ができない | SSEイベント + フロントエンドUI |
| デバッグ困難 | ログ拡張で記録可能 |

### 代替案との比較

#### 案A: 履歴をメモリに保持（不採用）

```python
# 適用後も履歴として保持
self._history.append(change)
```

**問題点**:
- メモリ使用量が線形増加（3時間で41MB）
- GCの負荷増加
- 実用上の価値が低い（過去より未来が重要）

#### 案B: 定期的クリーンアップ（不採用）

```python
# 1000ステップごとにまとめて削除
if global_step % CLEANUP_INTERVAL == 0:
    timeline.cleanup_past(global_step)
```

**問題点**:
- 即時削除とメモリ使用量はほぼ同じ
- 実装が複雑化（クリーンアップタイミング管理）
- リアルタイム性が損なわれる可能性

#### 案C: データベース保存（不採用）

**問題点**:
- I/Oオーバーヘッド（リアルタイム性に影響）
- 依存関係増加（SQLite等）
- 現時点で要求されていない

---

## Consequences

### Positive

- **メモリ安定**: 長時間セッションでもメモリ使用量が一定
- **高パフォーマンス**: 毎ステップの処理が軽量（< 1ms）
- **シンプル**: タイムラインは未来だけ管理
- **拡張性**: SSEイベントで柔軟な履歴管理が可能

### Negative

- **履歴なし**: 適用済み予約はメモリから消える
  - **緩和策**: SSEイベントで外部記録可能

### Neutral

- **履歴管理の責任分離**: コアは予約管理、履歴は拡張機能
- **段階的実装**: 将来必要になれば履歴機能を追加可能

---

## Implementation Details

### コンポーネント構成

```
oiduna_timeline/
├── models.py           # ScheduledChange (UUID, validation)
├── timeline.py         # ScheduledChangeTimeline (CRUD, cleanup)
├── merger.py           # merge_changes() (複数予約マージ)
└── tests/              # 39 unit tests (99% coverage)

oiduna_loop/engine/
└── timeline_loader.py  # TimelineLoader (即時削除実装)

oiduna_session/managers/
└── timeline_manager.py # TimelineManager (SSE event emission)

oiduna_api/routes/
└── timeline.py         # 5 API endpoints
```

### パフォーマンス特性

| 操作 | 計算量 | 実時間 |
|-----|-------|--------|
| add_change() | O(1) | < 1ms |
| apply_changes_at_step() | O(N) | ~2ms (N=300) |
| cleanup_past() | O(M) | < 1ms (M=削除数) |

### メモリ使用量（3時間セッション）

- **即時削除**: 2-3 MB（未来の予約のみ）
- **履歴保持**: 41+ MB（全履歴）

---

## Related Decisions

- **ADR-0012**: Package Architecture - oiduna_timeline パッケージの位置付け
- **ADR-0006**: Extension System - SSEイベントによる履歴記録拡張の実装方法

---

## Notes

### 将来的な拡張オプション

履歴が必要になった場合の実装パス：

1. **SSEログサーバー拡張** (推奨)
   - oiduna_api とは別プロセス
   - SSEイベントをDBに記録
   - タイムラインコアは変更不要

2. **オプショナル履歴モード**
   ```python
   ScheduledChangeTimeline(keep_history=True)
   ```
   - 設定で切り替え可能
   - デフォルトは即時削除

3. **外部ストレージ連携**
   - PostgreSQL, MongoDB等
   - 非同期書き込み（リアルタイム性維持）

### テストカバレッジ

- Unit tests: 39 tests (99% coverage)
- Integration tests: 9 tests (全シナリオ網羅)
- Regression tests: 350 tests (全て合格)

---

## References

- 設計文書: `design_proposal_timeline_v2.py`
- パフォーマンス分析: `timeline_performance_analysis.md`
- 実装プラン: 本ADR作成時の実装プラン
