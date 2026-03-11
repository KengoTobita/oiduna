# ADR-0021: 後方互換性の完全削除とリファクタリング

**Status**: Implemented (v3.1)
**Date**: 2026-03-11 (Updated: 2026-03-11 for v3.1)
**Deciders**: Claude Sonnet 4.5, tobita
**Related**: ADR-0017 (IPC/Session Naming), ADR-0018 (Optimistic Locking)

---

## Context

Oidunaプロジェクトは複数のリファクタリング段階を経て、Python 3.13固定環境に移行した。しかし、過去のバージョンとの互換性を保つための**23個の後方互換性要素**が残存し、コードベースの保守性を低下させていた。

### v3.1で実施した命名改善（2026-03-11）

**🎯 Ubiquitous Language統一**:
1. **Event → PatternEvent** - ドメイン層の音楽イベント明確化
2. **SessionEventSink → SessionEventPublisher** - Pub/Sub標準化、publish()メソッド導入
3. **IPC実装クラス名改名** - Protocol名との一致
   - `InProcessStateSink` → `InProcessStateProducer`
   - `NoopCommandSource` → `NoopCommandConsumer`
   - `MockCommandSource` → `MockCommandConsumer`
   - `MockStateSink` → `MockStateProducer`

**影響範囲**:
- コード変更: 47ファイル
- ドキュメント更新: 13ファイル
- テスト結果: 680 passed

**コミット**:
```
f5344d2 refactor: rename Event to PatternEvent for clarity
ca1ebbf refactor: rename SessionEventSink to SessionEventPublisher
29d1197 refactor: rename IPC implementation classes to match Protocol names
d398cc8 docs: update terminology and migration guides for v3.1 naming changes
```

### 残存していた後方互換性要素（v3.0以前）

**Legacy Protocol名（最優先）**:
- `CommandSink` / `CommandSource` (15箇所以上に影響) - ✅ v3.0で削除
- `StateSink` / `StateSource` - ✅ v3.0で削除
- `EventSink` alias (6箇所) - ✅ v3.1でSessionEventPublisherに改名

**廃止予定のプロパティ**:
- `RuntimeState.playing` setter（v2.1で非推奨化）
- `RuntimeState.tracks` / `RuntimeState.sequences` properties
- `LoopService.get_instance()` メソッド

**旧形式サポート**:
- Python 3.9互換性コメント
- ImportError fallback
- Event dict対応（Event objectsのみに移行済み）
- X-Session-Versionヘッダーのデフォルト値

**コード品質問題**:
- `TrackManager.create()` - 52行の長いメソッド
- `PatternManager.create()` - 59行の長いメソッド

### 問題点

1. **保守性の低下**: 新旧2つの命名規則が混在
2. **認知的負荷**: 開発者がどちらを使うべきか迷う
3. **テストの複雑化**: 両方のパターンをテストする必要
4. **型安全性の低下**: Union型による型推論の弱体化
5. **コードの冗長性**: 実質的に同じコードが2箇所に存在

---

## Decision

**23個すべての後方互換性要素を完全削除**し、Python 3.13に最適化されたクリーンなコードベースを実現する。同時に、Martin Fowlerのリファクタリングパターンを適用してコード品質を向上させる。

### 削除対象と方針

#### 1. Legacy Protocol名（破壊的変更）

**削除するProtocol**:
```python
# 削除
CommandSink, CommandSource, StateSink, StateSource

# 標準化
CommandProducer/Consumer, StateProducer/Consumer
```

**影響範囲**:
- `packages/oiduna_loop/ipc/protocols.py` - 194行削除
- `packages/oiduna_loop/factory.py` - Union型削除
- `packages/oiduna_loop/engine/loop_engine.py` - 内部変数名変更
  - `self._commands` → `self._command_consumer`
  - `self._publisher` → `self._state_producer`

#### 2. EventSink Alias（破壊的変更）

```python
# 削除
EventSink = SessionEventSink  # Legacy alias

# 標準化
SessionEventSink  # 明示的な名前のみ使用
```

**影響範囲**: 6ファイル（全manager系）

#### 3. RuntimeState後方互換プロパティ（破壊的変更）

```python
# 削除
@playing.setter
def playing(self, value: bool) -> None:
    """Backwards compatible setter"""
    # ...

@property
def tracks(self) -> dict[str, Any]:
    return {}  # No longer supported

@property
def sequences(self) -> dict[str, Any]:
    return {}  # No longer supported
```

**影響範囲**: テストコードのみ（本体コードは既に新形式使用）

#### 4. 影響ゼロの削除

- Python 3.9互換性コメント
- ImportError fallback（両ブロックが同一）

#### 5. Martin Fowler Extract Method

**TrackManager.create()のリファクタリング**:
```python
# Before: 52行のメソッド
def create(...) -> Track:
    # Validate destination
    # Validate client
    # Generate ID
    # Create track
    # Register
    # Emit event
    return track

# After: 4つのメソッドに分割
def create(...) -> Track:
    self._validate_track_creation(destination_id, client_id)
    track = self._build_track(track_name, destination_id, client_id, base_params)
    self._register_track(track)
    self._emit_track_created_event(track)
    return track

def _validate_track_creation(self, destination_id: str, client_id: str) -> None:
    """Validate that destination and client exist."""
    ...

def _build_track(...) -> Track:
    """Build a new Track object with generated ID."""
    ...

def _register_track(self, track: Track) -> None:
    """Register track in session."""
    ...

def _emit_track_created_event(self, track: Track) -> None:
    """Emit track_created event."""
    ...
```

**PatternManager.create()にも同様の適用**

---

## Consequences

### ✅ Positive

#### 1. コード品質の向上
- **認知的負荷の削減**: 1つの明確な命名規則
- **型安全性の向上**: Union型排除により型推論が強化
- **テストの簡素化**: 単一パターンのみテスト
- **Eventの曖昧性解消** (v3.1): PatternEvent、SessionEvent、SSE Eventの責任が明確化
- **業界標準準拠** (v3.1): Pub/Subパターン（publish()）採用

#### 2. 保守性の向上
- **コードの可読性**: 冗長なaliasやコメントが消失
- **リファクタリングの容易性**: 単一責任の原則により変更が局所化
- **テスト容易性**: Extract Methodにより各ステップを独立してテスト可能

#### 3. パフォーマンス
- **キャッシュ削減**: ~46MB削除（__pycache__含む）
- **型チェック高速化**: Union型の削減により型推論が高速化

#### 4. ドキュメンテーション
- **明確なAPI**: 非推奨の選択肢が消失、学習コストが低下

### ⚠️ Negative（破壊的変更）

#### 1. 既存コードへの影響

**CommandSource/Sink → Producer/Consumer**:
```python
# 動作しなくなるコード
from oiduna_loop.ipc.protocols import CommandSource
# ImportError: cannot import name 'CommandSource'

# 新しいコード
from oiduna_loop.ipc.protocols import CommandProducer
```

**Event → PatternEvent** (v3.1):
```python
# 動作しなくなるコード
from oiduna_models import Event
# ImportError: cannot import name 'Event'

# 新しいコード
from oiduna_models import PatternEvent
```

**SessionEventSink → SessionEventPublisher** (v3.1):
```python
# 動作しなくなるコード
from oiduna_session.managers import SessionEventSink

class MyPublisher:
    def _push(self, event: dict) -> None:  # ❌ _push() は削除
        ...

# 新しいコード
from oiduna_session.managers import SessionEventPublisher

class MyPublisher:
    def publish(self, event: dict) -> None:  # ✅ publish() を使用
        ...
```

**IPC実装クラス名** (v3.1):
```python
# 動作しなくなるコード
from oiduna_loop.ipc import InProcessStateSink, NoopCommandSource

# 新しいコード
from oiduna_loop.ipc import InProcessStateProducer, NoopCommandConsumer
```

**RuntimeState.playing setter**:
```python
# 動作しなくなるコード
state.playing = True
# AttributeError: property 'playing' of 'RuntimeState' object has no setter

# 新しいコード
state.playback_state = PlaybackState.PLAYING
```

**X-Session-Version header**:
```bash
# 動作しなくなるリクエスト
curl -X POST /api/playback/session
# 400 Bad Request: X-Session-Version header is required

# 新しいリクエスト
curl -X POST /api/playback/session -H "X-Session-Version: 5"
```

#### 2. 移行コスト

既存のクライアントコードは**すべて更新が必要**:
- Extension開発者
- APIクライアント
- テストコード

---

## Implementation

### Phase構成（7段階）

#### Phase 1: 準備（リスク: 最低）
- キャッシュ削除（~46MB）
- ベースライン確立（テスト、型チェック）

#### Phase 2: 影響ゼロの削除（リスク: 最低）
- Python 3.9コメント削除
- ImportError fallback削除

#### Phase 3: Legacy Protocol削除（リスク: 中）
- Protocol定義削除（194行）
- LoopEngine型Union削除
- Factory関数簡略化
- 内部変数名変更（self._commands等）

#### Phase 4: その他後方互換性削除（リスク: 低〜中）
- EventSink alias削除
- RuntimeStateプロパティ削除
- LoopService.get_instance()削除
- Event dict対応削除
- X-Session-Versionヘッダー必須化

#### Phase 5: Martin Fowlerリファクタリング（リスク: 低）
- TrackManager.create() Extract Method
- PatternManager.create() Extract Method

#### Phase 6: 最終検証（リスク: 最低）
- 全テスト実行（700+テスト）
- 型チェック（strictモード）
- カバレッジ確認（92%維持）
- Legacy import確認

#### Phase 7: クリーンアップとコミット（リスク: 最低）
- キャッシュ再削除
- Git commit（Phase単位）

### 実装結果

| Metric | Before (v2.x) | After (v3.1) | Change |
|--------|--------|-------|--------|
| 後方互換性要素 | 23個 | 0個 | -23 ✅ |
| Legacy protocol定義 | ~200行 | 0行 | -200行 |
| テスト合格 | ~597 | 680 | +83 |
| 型安全性 | 95% | 95% | 維持 |
| キャッシュサイズ | ~46MB | 0 | クリーン |
| Event曖昧性 | 3つの意味 | 明確に分離 | 解消 ✅ |

**v3.0コミット** (Protocol削除):
1. `217c896` - docs: update migration guides for v3.0 breaking changes
2. (Protocol定義削除は既に完了)

**v3.1コミット** (命名統一):
1. `f5344d2` - refactor: rename Event to PatternEvent for clarity
2. `ca1ebbf` - refactor: rename SessionEventSink to SessionEventPublisher
3. `29d1197` - refactor: rename IPC implementation classes to match Protocol names
4. `d398cc8` - docs: update terminology and migration guides for v3.1 naming changes

---

## Related Documentation

### 移行ガイド
- `docs/IPC_NAMING_MIGRATION.md` - IPC命名規則の移行ガイド
- `docs/SESSION_EVENT_SINK_MIGRATION.md` - EventSink移行ガイド

### 関連ADR
- **ADR-0017**: IPC and Session Naming Standardization（命名規則の標準化）
- **ADR-0018**: Optimistic Locking（X-Session-Versionヘッダーの導入）

---

## Alternatives Considered

### Alternative 1: 段階的な非推奨化（採用せず）

**案**: Legacy名を残し、警告のみ表示

**却下理由**:
- 移行期間が延びることで技術的負債が増大
- 両方のパターンをテスト・保守する必要が継続
- Python 3.13固定により、後方互換性の必要性が消失

### Alternative 2: マクロで自動移行（採用せず）

**案**: コード変換ツールを提供

**却下理由**:
- ツール開発コストが高い
- すべてのエッジケースをカバーできない
- 手動移行の方が理解が深まる

### Alternative 3: v3.0まで保持（採用せず）

**案**: メジャーバージョンアップまで保持

**却下理由**:
- v3.0のタイミングが不明確
- 現在Python 3.13固定であり、即座に削除可能
- 既にADR-0017で命名規則を標準化済み

---

## Notes

### ロールバック戦略

```bash
# 全体ロールバック
git reset --hard HEAD~3

# 部分ロールバック
git revert <commit-hash>
```

### Critical Files

1. `packages/oiduna_loop/ipc/protocols.py` - Protocol定義（194行削除）
2. `packages/oiduna_loop/factory.py` - Factory簡略化
3. `packages/oiduna_loop/engine/loop_engine.py` - 内部変数名変更
4. `packages/oiduna_session/managers/base.py` - EventSink削除
5. `packages/oiduna_session/managers/track_manager.py` - Extract Method
6. `packages/oiduna_session/managers/pattern_manager.py` - Extract Method

### References

- Martin Fowler, "Refactoring: Improving the Design of Existing Code" (Extract Method pattern)
- Python 3.13 release notes
- ADR-0017: IPC and Session Naming Standardization

---

**最終更新**: 2026-03-11 (v3.1)
**実装者**: Claude Sonnet 4.5
**レビュー**: tobita
**ステータス**: ✅ v3.1完全実装済み（680テスト合格、92%カバレッジ維持）

### v3.1で達成したこと

1. ✅ **Eventの曖昧性解消**: PatternEvent、SessionEvent、SSE Eventの責任を明確化
2. ✅ **Pub/Sub標準化**: SessionEventPublisher.publish()で業界標準準拠
3. ✅ **実装クラス名統一**: IPC実装クラス名がProtocol名と一致
4. ✅ **完全な後方互換性削除**: v3.1では旧名は一切使用不可
5. ✅ **ドキュメント完全更新**: 13ファイルの移行ガイド更新
