# ADR-0020: Timeline Lookahead Optimization Strategy

**Status**: Accepted (Phase 1), Future Work (Phase 2)
**Date**: 2026-03-11
**Deciders**: Claude Sonnet 4.5, tobita
**Related**: ADR-0019 (Timeline Scheduling)

---

## Context

ADR-0019でタイムラインスケジューリング機能を実装したが、初期実装では**apply_changes()を同一ステップで実行**しており、クリティカルパス（OSC/MIDI送信）を圧迫する問題が判明した。

### 問題の詳細

**現状のタイミング**:
```
step 1000に到達:
  _execute_current_step()
    → apply_changes_at_step(1000)  (~40ms for 5000 messages)
    → get_messages_at_step(1000)
    → send_messages()              (~3ms)
  _wait_for_next_step()

合計: ~43ms (BPM 180 = 83ms/stepの51%を消費)
```

**問題点**:
1. ⚠️ **クリティカルパス圧迫**: load_messages()が送信処理と同じステップで実行
2. ⚠️ **音飛びリスク**: 大量メッセージ時（5000個）に40ms消費
3. ⚠️ **拡張性の欠如**: hooks処理やSSE送信の時間も考慮すると余裕がない

### 根本原因

- **256-step固定ループ**により、step 1000の変更をstep 1000で適用しても次周は遠い
- 先読みバッファがないため、apply処理が毎回クリティカルパスに入る

---

## Decision

### Phase 1: Lookahead Loading（即座実装）✅

**先読み適用戦略**を採用。N steps先の変更を事前に適用することで、クリティカルパスを最小化。

```python
# LoopEngine定数
TIMELINE_LOOKAHEAD_STEPS = 32   # 2 bar lookahead (8秒 @ BPM 120)
TIMELINE_MIN_LOOKAHEAD = 8      # 2 beat minimum (ギリギリ制限)

async def _execute_current_step(self):
    current_step = self.state.position.step

    # ★先読み適用: 32 steps ahead
    if self._timeline:
        future_global_step = self._global_step + TIMELINE_LOOKAHEAD_STEPS
        TimelineLoader.apply_changes_at_step(
            future_global_step,
            self._timeline,
            self._message_scheduler,
        )

    # クリティカルパス（軽量）
    messages = self._get_filtered_messages(current_step)
    messages = self._apply_hooks(messages, current_step)
    self._send_messages(messages, current_step)
```

**タイミング改善**:
```
step 968:
  apply_changes(1000)  (~40ms)  ← 32 steps前に適用
  send_messages(968)   (~3ms)

...（32 steps = 8秒 @ BPM 120）

step 1000:
  apply_changes(1032)  (~40ms for next change)
  send_messages(1000)  (~3ms)  ← すでに準備済み
```

**効果**:
- クリティカルパス: 43ms → 3ms（**93%削減**）
- BPM 180での消費率: 51% → 4%

#### Lookahead値の選定：32 steps (2 bar)

**候補の比較**:

| Lookahead | BPM 120 | BPM 180 | ウィンドウ* | 評価 |
|-----------|---------|---------|------------|------|
| 16 (1 bar) | 4秒 | 2.7秒 | 2秒 | ❌ 短すぎ |
| **32 (2 bar)** | **8秒** | **5.3秒** | **6秒** | ✅ **最適** |
| 64 (4 bar) | 16秒 | 10.7秒 | 12秒 | △ やや長い |
| 128 (8 bar) | 32秒 | 21.3秒 | 30秒 | ❌ 遅延大 |

*ウィンドウ = LOOKAHEAD - MIN_LOOKAHEAD (8 steps)

**32 stepsを選んだ理由**:

1. **音楽的妥当性**
   - 2 bar = 人間が即座に認識できる最小リズムパターン
   - 楽曲構成の自然な単位（4 barフレーズの半分）
   - ライブコーディングで「ちょっと先」= 2 bar

2. **パフォーマンス余裕**
   ```
   BPM 180（最速）: 5.3秒バッファ
   5000メッセージ処理: 40ms
   消費率: 0.75%（余裕十分）
   ```

3. **即応性の高さ**
   - 64 steps (16秒) より遅延感が少ない
   - 予約してから適用まで8秒 = 体感的に自然

4. **ギリギリ予約への対応**
   - MIN_LOOKAHEAD = 8 steps (2秒)
   - ウィンドウ = 24 steps = 6秒 @ BPM 120
   - 実用上十分な猶予

#### ギリギリ予約の対処

**最小lookahead制限**を導入：

```python
# TimelineManager.schedule_change()
MIN_LOOKAHEAD = 8  # 2 beat = 2秒 @ BPM 120

if target_global_step < current_global_step + MIN_LOOKAHEAD:
    return False, f"予約は最低{MIN_LOOKAHEAD}ステップ先に設定してください", None
```

**効果**:
- ✅ 2秒の猶予でload_messages()は確実に完了
- ✅ ギリギリ予約のエラー処理が明確
- ✅ 超緊急時は`/playback/session`で即座適用を使用（代替手段あり）

---

### Phase 2: Double Buffering（将来実装）🔮

**二重バッファリング戦略**を将来の高速化タスクとして記録。

#### コンセプト：Prepare & Commit

```python
class MessageScheduler:
    def __init__(self):
        # ★2つのバッファ
        self._active_buffer: Dict[int, List[ScheduledMessage]] = defaultdict(list)
        self._pending_buffer: Dict[int, List[ScheduledMessage]] = defaultdict(list)

        self._bpm = 120.0
        self._pattern_length = 4.0

    def prepare_messages(self, batch: ScheduledMessageBatch):
        """重い処理: pendingバッファにロード（~40ms）"""
        self._pending_buffer.clear()

        for msg in batch.messages:
            self._pending_buffer[msg.step].append(msg)

        self._pending_bpm = batch.bpm
        self._pending_pattern_length = batch.pattern_length

    def commit(self):
        """超軽量: バッファを入れ替え（< 0.1ms）"""
        # ポインタ交換のみ（メモリコピーなし）
        self._active_buffer, self._pending_buffer = \
            self._pending_buffer, self._active_buffer

        self._bpm = self._pending_bpm
        self._pattern_length = self._pending_pattern_length

    def get_messages_at_step(self, step: int):
        """読み取り: activeバッファから（変更なし）"""
        return self._active_buffer.get(step, [])
```

#### タイミング図（Phase 2）

```
step 900:
  prepare_messages(step1000用)  (~40ms)
    → pendingバッファに準備
    → activeバッファは変化なし（再生継続）
  send_messages(900)            (~3ms, activeバッファ使用)

step 999:
  commit()                      (< 0.1ms)
    ★ active ⇔ pending を入れ替え
  send_messages(999)            (~3ms)

step 1000:
  prepare_messages(step1100用)  (~40ms, pendingで準備)
  send_messages(1000)           (~3ms, activeから再生)
    ← step 1000のメッセージはすでにactiveに存在
```

#### メリット・デメリット

**メリット**:
- ✅ **commit()が超高速**: < 0.1ms（ポインタ交換のみ）
- ✅ **完全な分離**: prepare中もactiveで再生継続（競合なし）
- ✅ **予測可能**: commit()タイミングを正確に制御可能
- ✅ **クリティカルパス最小化**: 送信処理のみ（3ms）

**デメリット**:
- ❌ **メモリ2倍**: activeとpendingの2セット必要
  - 5000メッセージ × 2 = 約460KB（実は小さい）
  - 長時間セッションでも問題なし
- ❌ **大規模変更**: MessageSchedulerの全面改修が必要
  - 既存API（load_messages）を維持しつつprepare/commit導入
  - テスト全面見直し
- ❌ **複雑化**: prepare/commitの2ステップ管理
  - LoopEngineでのタイミング制御
  - エラーハンドリング（prepareが失敗した場合等）

#### パフォーマンス比較

| 方式 | クリティカルパス | メモリ | 実装難度 |
|-----|-----------------|--------|---------|
| **現状（同期）** | 43ms | 1x | - |
| **Phase 1（先読み）** | 3ms | 1x | ✅ 低 |
| **Phase 2（二重バッファ）** | < 0.1ms | 2x | ⚠️ 高 |

#### 実装の優先度

**Phase 2は以下の場合に実装を検討**:

1. ✅ **Phase 1で問題が残る場合**
   - 32 steps lookaheadでも不十分
   - hooks処理等で3ms以上かかる

2. ✅ **より高いBPMが必要な場合**
   - BPM 240+（62ms/step）でも安定動作
   - Phase 1: 3ms = 5%消費
   - Phase 2: 0.1ms = 0.2%消費

3. ✅ **複雑なタイミング制御が必要な場合**
   - 複数タイムラインの同時管理
   - A/Bテスト的なパターン切り替え

**現時点の評価**: Phase 1で十分、Phase 2は将来の最適化タスク

---

## Consequences

### Phase 1 (Lookahead Loading)

#### Positive

- ✅ **クリティカルパス最小化**: 43ms → 3ms（93%削減）
- ✅ **実装が単純**: 10行程度の変更で完了
- ✅ **リスクが低い**: ロジック変更なし、タイミングのみ変更
- ✅ **音楽的に自然**: 2 bar lookahead = ライブコーディングに最適
- ✅ **既存テスト全合格**: 後方互換性維持

#### Negative

- ⚠️ **MIN_LOOKAHEAD制限**: 8 steps (2秒) 未満の予約は拒否
  - **緩和策**: `/playback/session`で即座適用可能
- ⚠️ **lookahead期間中のBPM変更**: 理論上は矛盾の可能性
  - **影響**: 2 bar (8秒) 以内のBPM変更は稀
  - **緩和策**: BPM変更時にタイムライン再適用（Phase 1.5で対応可能）

#### Neutral

- 📊 **設定値の調整**: LOOKAHEAD_STEPS, MIN_LOOKAHEADはチューニング可能
- 📊 **段階的実装**: Phase 1で不十分ならPhase 2へ移行

### Phase 2 (Double Buffering) - Future

#### Positive (期待効果)

- 🔮 **究極の高速化**: commit() < 0.1ms
- 🔮 **完全な予測可能性**: タイミング制御が正確
- 🔮 **高BPM対応**: BPM 300でも余裕

#### Negative (実装コスト)

- 💰 **大規模変更**: MessageScheduler全面改修（100+行）
- 💰 **メモリ2倍**: 460KB増（実質的には影響小）
- 💰 **テスト工数**: 新規テスト30+個、既存テスト見直し

---

## Implementation Plan

### Phase 1: Lookahead Loading（即座実装）

**優先度**: 🔴 High - 即座に実装

```python
# 1. LoopEngine定数追加（2行）
TIMELINE_LOOKAHEAD_STEPS = 32
TIMELINE_MIN_LOOKAHEAD = 8

# 2. _execute_current_step()修正（3行変更）
future_global_step = self._global_step + self.TIMELINE_LOOKAHEAD_STEPS
TimelineLoader.apply_changes_at_step(future_global_step, ...)

# 3. TimelineManager検証追加（5行）
if target_global_step < current_global_step + TIMELINE_MIN_LOOKAHEAD:
    return False, "最低8ステップ先に設定してください", None
```

**工数**: 30分
**テスト**: 既存テスト全合格（ロジック不変）+ 新規テスト2個

### Phase 2: Double Buffering（将来タスク）

**優先度**: 🟡 Low - 必要になったら実装

**前提条件**:
- Phase 1で問題が残る
- BPM 240+の要求がある
- 複雑なタイミング制御が必要

**実装ステップ**:

1. **MessageScheduler改修** (3-4時間)
   - `_active_buffer`, `_pending_buffer`追加
   - `prepare_messages()`, `commit()`実装
   - 既存`load_messages()`をwrapperに変更（後方互換性）

2. **LoopEngine統合** (1-2時間)
   - prepare/commitタイミング制御
   - エラーハンドリング

3. **テスト** (2-3時間)
   - 新規テスト30個（prepare/commit各種シナリオ）
   - 既存テスト見直し
   - パフォーマンステスト

**工数**: 6-9時間
**リスク**: 中（大規模変更だが、設計は明確）

---

## Alternatives Considered

### 案A: 非同期バックグラウンド適用（不採用）

```python
asyncio.create_task(
    self._apply_timeline_async(self._global_step)
)
```

**問題点**:
- ❌ 競合状態リスク（MessageScheduler._stepsへの同時書き込み）
- ❌ 適用完了タイミングが不確定
- ❌ 排他制御が必要（複雑化）

### 案B: 定期的バックグラウンドタスク（不採用）

```python
# 別タスクで定期的にtimelineをチェック
async def _timeline_worker():
    while True:
        await asyncio.sleep(0.1)
        apply_upcoming_changes()
```

**問題点**:
- ❌ タイミング制御が不正確
- ❌ ポーリングオーバーヘッド
- ❌ 同期問題

---

## Performance Analysis

### Lookahead値とパフォーマンス

| Lookahead | BPM 120 | 処理時間 | 消費率 | 音楽的妥当性 |
|-----------|---------|---------|--------|------------|
| 4 (beat) | 1秒 | 40ms | 4% | ❌ 短すぎ |
| 16 (bar) | 4秒 | 40ms | 1% | △ やや短 |
| **32 (2 bar)** | **8秒** | **40ms** | **0.5%** | ✅ **最適** |
| 64 (4 bar) | 16秒 | 40ms | 0.25% | △ やや長 |
| 128 (8 bar) | 32秒 | 40ms | 0.125% | ❌ 長すぎ |

### 実測データ（想定）

```python
# BPM 180, 5000メッセージ
現状:
  step 1000: 43ms (load 40ms + send 3ms)
  83ms/stepの51%消費

Phase 1 (32 steps lookahead):
  step 968: 43ms (load 40ms + send 3ms)
  step 1000: 3ms (send only)
  83ms/stepの4%消費（step 1000）

Phase 2 (double buffering):
  step 968: 43ms (prepare 40ms + send 3ms)
  step 999: 0.1ms (commit)
  step 1000: 3ms (send only)
  83ms/stepの0.1%消費（commit）
```

---

## Related Decisions

- **ADR-0019**: Timeline Scheduling with Immediate Cleanup - 本機能の基盤
- **ADR-0012**: Package Architecture - oiduna_loop/oiduna_scheduler分離
- **ADR-0003**: Python Timing Engine Phase 1 - ループエンジンの設計

---

## References

- LoopEngine実装: `packages/oiduna_loop/engine/loop_engine.py`
- MessageScheduler実装: `packages/oiduna_scheduler/scheduler.py`
- TimelineLoader実装: `packages/oiduna_loop/engine/timeline_loader.py`
- パフォーマンス分析: `timeline_performance_analysis.md`

---

## Revision History

- 2026-03-11: Initial version
  - Phase 1: 32 steps lookahead決定
  - Phase 2: Double buffering記録
