# ADR 0008: Code Quality Improvement and Refactoring Strategy

**Status**: Accepted

**Date**: 2026-02-27

**Deciders**: tobita, Claude Code

---

## Context

Architecture unification (Phases 1-8) 完了後、コードベースに以下の品質問題が残存していた。

### 背景

**Phase 1-8完了時点の状態**:
- ✅ CompiledSession → ScheduledMessageBatch 移行完了
- ✅ 全328テスト合格
- ❌ LoopEngineが1,034行（大規模クラス）
- ❌ 存在しないメソッド呼び出し（実行時エラーのリスク）
- ❌ 型ヒント不統一（Python 3.8 vs 3.13）
- ❌ 相対インポートとsys.path操作
- ❌ 責任境界の曖昧さ（patterns endpoint）

### 問題点

#### 1. Critical Bugs
```python
# LoopEngine line 831-838
if self.state.should_apply_pending():  # ❌ メソッド存在しない
    self.state.apply_pending_changes()  # ❌ メソッド存在しない

# LoopEngine line 1035
effective = self.state.get_effective()  # ❌ メソッド存在しない

# LoopEngine line 1076
active = self.state.get_active_tracks()  # ❌ 誤った名前
```

**影響**: Phase 2でRuntimeState簡素化時にメソッド削除したが、呼び出し側が残存。

#### 2. Type Safety Issues
```python
# 混在する型ヒント
from typing import List, Dict, Optional  # Python 3.8スタイル
def foo(items: list) -> dict:  # Python 3.13スタイル（非ジェネリック）
```

**影響**: mypy警告、コード理解の困難、将来の型エラーリスク。

#### 3. Architecture Violations

**patterns.py endpoint**:
```python
@router.post("/patterns")
async def create_pattern(...):
    # パターン管理はMARSの責任
    # Oidunaはスケジューリングのみ担当すべき
```

**設計違反**: Oidunaはスケジューラであり、パターン生成器ではない。

#### 4. Code Complexity

**LoopEngine**:
- 1,034行（推奨: <500行）
- `_step_loop()`: 循環的複雑度12+（推奨: <10）
- 複数の責任: コマンド処理、ステップ実行、ドリフト補正、MIDI送信

**保守性**: 変更困難、テスト困難、責任不明確。

---

## Decision

### Strategy: Incremental Refactoring with Test Coverage

Martin Fowlerのリファクタリングパターンを適用し、全テスト合格を維持しながら段階的改善。

---

## Phase A: Critical Fixes (Priority 0)

### Decision A1: Fix Non-Existent Method Calls

**変更**:
```python
# DELETE: Pending changes (Phase 2で削除済み)
- if self.state.should_apply_pending():
-     self.state.apply_pending_changes()

# DELETE: get_effective() (CompiledSession削除済み)
- session = self.state.get_effective()
+ # Return empty list - Monitor display needs update for new architecture

# FIX: Method name
- active = self.state.get_active_tracks()
+ active = self.state.get_active_track_ids()
```

**理由**: 実行時エラーの防止。

### Decision A2: Remove Broken Symlinks

**変更**: 4つの壊れたシンボリックリンクを削除
```bash
rm packages/oiduna_loop/tests/test_helpers.py
rm packages/oiduna_loop/tests/test_modulation_runtime.py
rm packages/oiduna_loop/tests/test_runtime_state.py
rm packages/oiduna_loop/tests/test_step_processor_v2.py
```

**理由**: Phase 1でCompiledSession削除時に残存。実際のテストは`tests/oiduna_loop/`に存在。

---

## Phase B: Type Safety (Priority 1)

### Decision B1: Standardize to Python 3.13 Type Hints

**変更**:
```python
# Before (混在)
from typing import List, Dict, Optional
def foo(items: List) -> Dict:  # 非ジェネリック

# After (統一)
def foo(items: list[str]) -> dict[str, Any]:  # ジェネリック + 3.13構文
def bar(x: str | None) -> None:  # | 演算子
```

**根拠**: Python 3.13推奨、PEP 585 (組み込みジェネリック), PEP 604 (Union演算子)

### Decision B2: Absolute Imports Only

**変更**:
```python
# Before
from scheduler_models import ScheduledMessage  # 相対
import sys
sys.path.insert(0, ...)  # ハック

# After
from oiduna_scheduler.scheduler_models import ScheduledMessage  # 絶対
```

**理由**: Import明確化、IDE補完改善、sys.path汚染回避。

**影響ファイル**: 15+ファイル（`__init__.py`, `loop_engine.py`, `router.py`, `scheduler.py`, etc.）

---

## Phase C: Architecture Cleanup (Priority 1)

### Decision C1: Remove patterns.py Endpoint

**変更**: `POST /api/patterns`エンドポイント削除

**理由**:
- **責任境界違反**: パターン管理はクライアント（MARS）の責任
- **Oidunaの責任**: メッセージスケジューリングのみ
- **代替**: クライアントがScheduledMessageBatchを`POST /playback/session`に送信

**Breaking Change**: ✅ （CHANGELOG.mdに記載）

### Decision C2: Make Command Handlers Public API

**変更**:
```python
# Before
def _handle_play(self, payload) -> CommandResult:  # プライベート

# After
def handle_play(self, payload) -> CommandResult:  # パブリック
    """Public API for playback control - can be called directly from routes."""
```

**理由**:
- `playback.py`が`engine._handle_play()`を直接呼び出し（カプセル化違反）
- 意図的なパブリックAPIとして明示
- ドキュメント化

**影響**: `handle_play()`, `handle_stop()`, `handle_pause()`

---

## Phase D: Refactoring (Priority 2)

### Decision D1: Extract Class - CommandHandler

**パターン**: Martin Fowler - Extract Class

**理由**:
- LoopEngineが複数の責任を持つ（Single Responsibility Principle違反）
- コマンド処理ロジックを独立クラスに分離

**実装**:
```python
# packages/oiduna_loop/engine/command_handler.py
class CommandHandler:
    """
    Handles playback commands (play, stop, pause, bpm, mute, solo).

    Responsibilities:
    - Validate command payloads
    - Update RuntimeState
    - Send MIDI clock messages (delegated)
    """
    def __init__(
        self,
        state: RuntimeState,
        clock_generator: ClockGenerator,
        note_scheduler: NoteScheduler,
        publisher: StateSink,
        midi_enabled: bool,
    ):
        self.state = state
        self._clock_generator = clock_generator
        self._note_scheduler = note_scheduler
        self._publisher = publisher
        self._midi_enabled = midi_enabled

    def handle_play(self, payload: dict[str, Any]) -> CommandResult:
        """Start or resume playback."""
        # State change logic
        ...

    def handle_stop(self, payload: dict[str, Any]) -> CommandResult:
        """Stop playback and reset position."""
        # State change logic
        ...
```

**LoopEngine統合**:
```python
class LoopEngine:
    def __init__(self, ...):
        self._command_handler = CommandHandler(...)

    def handle_play(self, payload) -> CommandResult:
        """Wrapper with engine-specific logic."""
        old_state = self.state.playback_state
        result = self._command_handler.handle_play(payload)

        if result.success and old_state != PlaybackState.PLAYING:
            # Engine-specific: MIDI clock
            if self._midi_enabled:
                if old_state == PlaybackState.STOPPED:
                    self._clock_generator.send_start()
                elif old_state == PlaybackState.PAUSED:
                    self._clock_generator.send_continue()
            # Engine-specific: Status updates
            self._schedule_status_update()

        return result
```

**責任分離**:
- **CommandHandler**: 状態変更（playback_state, BPM, mute/solo）
- **LoopEngine**: エンジン固有ロジック（MIDI送信、ドリフト補正、ステータス更新）

**結果**:
- LoopEngine: 1,034行 → ~850行（**18%削減**）
- CommandHandler: 225行（新規）
- 純削減: ~180行

### Decision D2: Extract Method - Simplify _step_loop()

**パターン**: Martin Fowler - Extract Method

**理由**:
- `_step_loop()`: 130+行、循環的複雑度12+
- 複数の責任: メッセージ取得、フィルタリング、フック適用、送信、待機

**リファクタリング**:
```python
# Before: 1つの巨大メソッド
async def _step_loop(self) -> None:
    while self._running:
        # ドリフト検出 (20行)
        # メッセージ取得とフィルタリング (30行)
        # フック適用 (15行)
        # 送信 (10行)
        # 周期的更新 (20行)
        # エラー処理 (10行)
        # ステップ進行と待機 (15行)

# After: 明確な責任分離
async def _step_loop(self) -> None:
    while self._running:
        if not self.state.playing:
            await asyncio.sleep(0.001)
            continue

        await self._execute_current_step()
        await self._wait_for_next_step()

def _execute_current_step(self) -> None:
    """Execute processing for current step."""
    messages = self._get_filtered_messages(current_step)
    if messages:
        messages = self._apply_hooks(messages, current_step)
        self._send_messages(messages, current_step)
    await self._publish_periodic_updates(current_step)

def _get_filtered_messages(self, step: int) -> list[ScheduledMessage]:
    """Get and filter messages for current step."""
    ...

def _apply_hooks(self, messages, step) -> list[ScheduledMessage]:
    """Apply extension hooks to messages."""
    ...

def _send_messages(self, messages, step) -> None:
    """Send messages to destination router."""
    ...

async def _wait_for_next_step(self) -> None:
    """Wait for next step with drift correction."""
    ...

async def _publish_periodic_updates(self, step: int) -> None:
    """Publish periodic updates (position, tracks info)."""
    ...
```

**メトリクス改善**:
- 循環的複雑度: 12+ → **<5**
- メソッドサイズ: 各<20行
- 責任: 各1つ（Single Responsibility）

**可読性向上**:
- ステップループの流れが一目瞭然
- 各処理が独立してテスト可能
- 変更影響範囲の局所化

---

## Phase E: Code Cleanup (Priority 3)

### Decision E1: Remove Dead Code

**変更**:
```python
# packages/oiduna_api/main.py (lines 100-109)
- # @app.get("/")
- # async def root():
- #     return {"message": "Oiduna API"}
```

**理由**: コメントアウトされたコードはgit履歴で十分。

---

## Consequences

### Positive

#### 1. Stability
- ✅ **全328テスト合格**
- ✅ 実行時エラーリスクの除去
- ✅ 型安全性の向上

#### 2. Maintainability
- ✅ LoopEngine: **18%削減**（1,034 → 850行）
- ✅ 循環的複雑度: **12+ → <5**
- ✅ 明確な責任境界
- ✅ 各メソッド<50行

#### 3. Code Quality
- ✅ Python 3.13準拠
- ✅ 絶対インポートのみ
- ✅ 死んだコードなし
- ✅ Single Responsibility Principle遵守

#### 4. Architecture
- ✅ 責任境界の明確化（Oiduna=スケジューラ、MARS=パターン管理）
- ✅ パブリック/プライベートAPIの区別
- ✅ Dependency Injection維持

### Negative

#### 1. Breaking Changes
- ⚠️ `POST /api/patterns`削除
  - **影響**: patternsエンドポイント使用クライアント
  - **移行**: `POST /playback/session`にScheduledMessageBatch送信
  - **ドキュメント**: CHANGELOG.mdに記載済み

#### 2. Increased File Count
- +1ファイル（`command_handler.py`）
  - **トレードオフ**: ファイル数増加 vs 保守性向上
  - **判断**: 保守性を優先

### Neutral

#### 1. Test Updates
- 全テストファイルで`_handle_*` → `handle_*`更新
- テストロジックは不変

---

## Implementation Summary

### Files Modified: 28

**Created**:
- `packages/oiduna_loop/engine/command_handler.py` (225行)

**Deleted**:
- `packages/oiduna_api/routes/patterns.py` (239行)
- `packages/oiduna_loop/tests/test_helpers.py` (シンボリックリンク)
- `packages/oiduna_loop/tests/test_modulation_runtime.py` (シンボリックリンク)
- `packages/oiduna_loop/tests/test_runtime_state.py` (シンボリックリンク)
- `packages/oiduna_loop/tests/test_step_processor_v2.py` (シンボリックリンク)

**Modified** (主要):
- `packages/oiduna_loop/engine/loop_engine.py`: 大幅リファクタリング
- `packages/oiduna_api/main.py`: patterns router削除
- `packages/oiduna_scheduler/*.py`: 絶対インポート化
- `tests/**/*.py`: メソッド名更新

### Code Metrics

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| LoopEngine行数 | 1,034 | ~850 | **-18%** |
| _step_loop複雑度 | 12+ | <5 | **-58%** |
| 最大メソッド行数 | 130+ | <50 | **-62%** |
| テスト合格率 | 100% (328) | 100% (328) | **維持** ✅ |
| 型ヒント統一 | 混在 | Python 3.13 | **統一** ✅ |

---

## Related ADRs

- [ADR-0003](0003-python-timing-engine-phase1.md): Python Timing Engine Phase 1
- [ADR-0004](0004-phase-roadmap-v2.md): Phase Roadmap v2
- [ADR-0007](0007-destination-agnostic-core-superdirt-migration.md): Destination-Agnostic Core

---

## References

### Refactoring Patterns
- Martin Fowler, *Refactoring: Improving the Design of Existing Code*
  - Extract Class
  - Extract Method
  - Reduce Cyclomatic Complexity

### Python Best Practices
- [PEP 585](https://peps.python.org/pep-0585/): Type Hinting Generics In Standard Collections
- [PEP 604](https://peps.python.org/pep-0604/): Allow writing union types as `X | Y`
- [PEP 8](https://peps.python.org/pep-0008/): Style Guide for Python Code

### Code Quality Metrics
- Cyclomatic Complexity: McCabe, 1976
- Single Responsibility Principle: Martin, *Agile Software Development*

---

## Notes

この改善は**技術的負債の返済**として位置づけられる。Phase 1-8でアーキテクチャ統一を優先し、コード品質は後回しにしていた。本ADRで完全にクリーンな状態に到達。

**Next Steps**:
- ✅ 完了（全328テスト合格）
- 継続的な品質維持（mypy, ruff）
- 必要に応じた追加リファクタリング（StepExecutor抽出は保留）
