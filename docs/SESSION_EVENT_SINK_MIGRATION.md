# SessionEventSink Migration Guide

## 概要

oiduna v2.1以降、Session層のイベント配信プロトコルを **EventSink → SessionEventSink** に改名しました。

この変更により、Loop層の`StateProducer`との混乱を解消し、責任が明確になります。

## 変更の背景

### 旧命名の問題点

```python
# 混乱しやすい命名

【EventSink】 - Session層のCRUD イベント
定義: oiduna_session/managers/base.py
用途: track_created, pattern_updated 等

【StateSink → StateProducer】 - Loop層の状態配信
定義: oiduna_loop/ipc/protocols.py
用途: position, status, error 等
```

**混乱のポイント**：
- 両方とも「イベント/状態」を扱うが、**異なるレイヤー**
- `EventSink`と`StateSink`という名前が似ている
- どちらがどの責任を持つか不明確

### 新命名（SessionEventSink）

```python
# 明確な命名

【SessionEventSink】 - Session層のCRUD イベント（新名称）
定義: oiduna_session/managers/base.py
用途: track_created, pattern_updated 等
呼び出し: SessionManager → SessionEventSink._push()

【StateProducer】 - Loop層の状態配信
定義: oiduna_loop/ipc/protocols.py
用途: position, status, error 等
呼び出し: LoopEngine → StateProducer.send_position()
```

**改善点**：
- ✅ Session層のイベントであることが一目瞭然
- ✅ Loop層の`StateProducer`との違いが明確
- ✅ レイヤー境界が命名から理解できる

---

## 新しい命名

| 旧名 | 新名 | レイヤー | 責任 |
|-----|------|---------|------|
| `EventSink` | `SessionEventSink` | Session層 | CRUD操作イベント配信 |

---

## データフロー図

### SessionEventSink のフロー

```
SessionManager (CRUD操作)
    ↓
BaseManager._emit_event()
    ↓
SessionEventSink._push()
    ↓
InProcessStateSink._queue
    ↓
SSE endpoint (/stream)
    ↓
クライアント（WebSocket経由）
```

### SessionEventSink と StateProducer の違い

```
【SessionEventSink】
送信者: SessionManager
イベント: track_created, pattern_updated, client_connected 等
頻度: 低頻度（ユーザー操作時）

【StateProducer】
送信者: LoopEngine
イベント: position, status, error, heartbeat 等
頻度: 高頻度（毎ステップ～15秒）

両方とも同じ InProcessStateSink._queue に流れる
    ↓
SSE endpoint で統一フォーマットで配信
```

---

## マイグレーション手順

### 段階1: 新しいProtocolを使用（推奨）

```python
# oiduna_session/managers/base.py

from oiduna_session.managers import SessionEventSink

class BaseManager:
    def __init__(
        self,
        session: Session,
        event_sink: SessionEventSink | None = None,  # 新しい型名
    ):
        self.event_sink = event_sink
```

### 段階2: 旧Protocolも互換性維持

既存の`EventSink`も引き続き使用可能です：

```python
# base.py で定義されているエイリアス
EventSink = SessionEventSink  # Legacy alias
```

### 段階3: SessionContainerでの使用

```python
from oiduna_session import SessionContainer
from oiduna_loop.ipc import InProcessStateSink

# InProcessStateSink は SessionEventSink Protocol を実装
sink = InProcessStateSink()
container = SessionContainer(event_sink=sink)
```

---

## 実装クラスの対応

### InProcessStateSink が両方のProtocolを実装

```python
# InProcessStateSink は2つの役割を担当

【StateProducer として】
- LoopEngine → API への状態配信
- send_position(), send_status() 等のメソッド

【SessionEventSink として】
- SessionManager → SSE への イベント配信
- _push() メソッド

同じ asyncio.Queue に両方のイベントが流れる
```

---

## イベントの種類

### SessionEventSink が配信するイベント

```python
【Client イベント】
- client_connected    : クライアント接続
- client_disconnected : クライアント切断

【Track イベント】
- track_created  : トラック作成
- track_updated  : トラック更新
- track_deleted  : トラック削除

【Pattern イベント】
- pattern_created : パターン作成
- pattern_updated : パターン更新
- pattern_deleted : パターン削除

【Environment イベント】
- environment_updated : 環境設定更新
```

---

## テストでの使用

### Mock実装

```python
# test_events.py

class MockSessionEventSink:
    """
    Mock session event sink for testing.

    Implements SessionEventSink protocol.
    """

    def __init__(self):
        self.events = []

    def _push(self, event: dict) -> None:
        """Record pushed events."""
        self.events.append(event)

    def get_events_by_type(self, event_type: str) -> list:
        """Get all events of a specific type."""
        return [e for e in self.events if e["type"] == event_type]


# Legacy alias
MockEventSink = MockSessionEventSink
```

### テストfixture

```python
@pytest.fixture
def manager_with_sink():
    """Create container with mock session event sink."""
    sink = MockSessionEventSink()
    container = SessionContainer(event_sink=sink)
    return container, sink

def test_track_created_event(manager_with_sink):
    container, sink = manager_with_sink

    container.tracks.create(
        track_id="track_001",
        track_name="kick",
        destination_id="superdirt",
        client_id="client_001"
    )

    events = sink.get_events_by_type("track_created")
    assert len(events) == 1
```

---

## 廃止予定スケジュール

| バージョン | 状態 | 詳細 |
|-----------|------|------|
| **v2.1** (現在) | 新Protocolを追加 | SessionEventSink 追加、EventSink は legacy alias |
| **v2.2** | 旧Protocol警告 | EventSink に deprecation 警告 |
| **v3.0** | 旧Protocol削除 | EventSink を完全削除 |

---

## よくある質問

### Q1: 既存のコードは動作し続けますか？

**A**: はい。`EventSink`は`SessionEventSink`のエイリアスとして引き続きサポートされます。

```python
# 旧コード（v2.1でも動作）
from oiduna_session.managers import EventSink

class BaseManager:
    def __init__(self, session, event_sink: EventSink = None):
        ...
```

### Q2: いつ新しい命名に移行すべきですか？

**A**: 新しいコードは即座に新命名を使用することを推奨します。既存コードは段階的に移行できます。

### Q3: SessionEventSink と StateProducer の違いは？

**A**:

| 項目 | SessionEventSink | StateProducer |
|------|------------------|---------------|
| **レイヤー** | Session層（API） | Loop層 |
| **送信者** | SessionManager | LoopEngine |
| **イベント** | CRUD操作 | 再生状態 |
| **頻度** | 低頻度（ユーザー操作） | 高頻度（毎ステップ） |
| **メソッド** | `_push()` のみ | `send_position()`, `send_status()` 等 |

### Q4: InProcessStateSink が両方のProtocolを実装する理由は？

**A**: SSE endpoint で**すべてのイベント**を統一フォーマットで配信するため。クライアントは単一接続で、Session層のCRUD操作もLoop層の再生状態も受け取ります。

---

## 変更ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `managers/base.py` | SessionEventSink Protocol 追加、EventSink を alias に |
| `managers/__init__.py` | SessionEventSink をエクスポート |
| `container.py` | 型ヒントを SessionEventSink に更新 |
| `tests/test_events.py` | MockSessionEventSink 追加 |

---

## まとめ

### メリット

✅ **明確性**: Session層のイベントであることが一目瞭然
✅ **混乱解消**: Loop層のStateProducerとの違いが明確
✅ **一貫性**: レイヤー別の命名規則が統一
✅ **ドキュメント性**: コードから設計意図が理解できる

### 互換性

✅ 旧EventSinkも引き続き動作
✅ 段階的な移行が可能
✅ 全テストがパス（301 passed）

---

**更新日**: 2026-03-02
**適用バージョン**: v2.1以降
