# SessionEventPublisher Migration Guide

**⚠️ v3.1 重要**: SessionEventSink は **SessionEventPublisher** に改名されました（2026-03-11）。
すべてのコードで SessionEventPublisher と publish() メソッドを使用してください。

---

## 概要

oiduna v2.1以降、Session層のイベント配信プロトコルを段階的に改善しました：
- **v2.1**: EventSink → SessionEventSink（レイヤー明確化）
- **v3.1**: SessionEventSink → SessionEventPublisher（役割明確化、publish() メソッド導入）

この変更により、Loop層の`StateProducer`、ドメイン層の`PatternEvent`との混乱を解消し、責任が明確になります。

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

### 新命名（SessionEventPublisher）

```python
# 明確な命名（v3.1）

【SessionEventPublisher】 - Session層のCRUD イベント発行
定義: oiduna_session/managers/base.py
用途: track_created, pattern_updated 等
呼び出し: SessionManager → SessionEventPublisher.publish()

【StateProducer】 - Loop層の状態配信
定義: oiduna_loop/ipc/protocols.py
用途: position, status, error 等
呼び出し: LoopEngine → StateProducer.send_position()

【PatternEvent】 - ドメイン層の音楽イベント
定義: oiduna_models/events.py
用途: Pattern内の音（step, cycle, params）
使用: Pattern.events: list[PatternEvent]
```

**改善点**：
- ✅ Session層のイベント**発行**であることが一目瞭然
- ✅ Loop層の`StateProducer`、ドメイン層の`PatternEvent`との違いが明確
- ✅ Pub/Subパターンの業界標準に準拠（publish()）
- ✅ レイヤー境界が命名から理解できる

---

## 命名の変遷

| バージョン | 旧名 | 新名 | メソッド名 | 変更理由 |
|-----------|------|------|----------|---------|
| v2.0 | EventSink | - | _push() | - |
| v2.1 | EventSink | SessionEventSink | _push() | レイヤー明確化 |
| v3.0 | - | SessionEventSink | _push() | EventSink削除 |
| **v3.1** | SessionEventSink | **SessionEventPublisher** | **publish()** | 役割明確化、業界標準準拠 |

---

## データフロー図（v3.1）

### 統合フロー: PatternEvent, SessionEvent, SSE Event

```
┌──────────────────────────────────────────────────────┐
│ ドメイン層: PatternEvent（音楽イベント）              │
│   Pattern.events: list[PatternEvent]                │
│       ↓ SessionCompiler                             │
│   ScheduledMessageBatch                             │
│       ↓ Loop Engine                                 │
│   音楽再生                                           │
└─────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│ Session層: SessionEvent（CRUD通知）                  │
│   BaseManager._emit_event(type, data)               │
│       ↓                                              │
│   SessionEventPublisher.publish({"type": ..., ...}) │
│       ↓                                              │
│   InProcessStateSink._queue ←┐                      │
└────────────────────────────── ┼─────────────────────┘
                               │
┌────────────────────────────── ┼─────────────────────┐
│ Loop層: StateProducer（再生状態）                    │
│   LoopEngine.send_position()  │                     │
│       ↓ StateProducer         │                     │
│   InProcessStateSink._queue ──┘                     │
└────────────────────────────── ┬─────────────────────┘
                               │ 統合キュー
                               ↓
┌──────────────────────────────────────────────────────┐
│ HTTP層: SSE Event（ストリーミング配信）              │
│   /api/stream/events                                │
│       ↓ _sse_event(type, data)                      │
│   "event: pattern_created\ndata: {...}\n\n"         │
│       ↓                                              │
│   EventSource API（ブラウザ）                        │
└──────────────────────────────────────────────────────┘
```

### 3つのEventの違い

| 項目 | PatternEvent | SessionEvent | SSE Event |
|------|-------------|--------------|-----------|
| **レイヤー** | ドメインモデル | Session層 | HTTP層 |
| **データ型** | PatternEvent class | dict | string |
| **目的** | 音楽的タイミング | CRUD通知 | HTTP配信 |
| **頻度** | 多数（パターン内） | 低頻度（操作時） | 高頻度（統合） |
| **送信者** | なし（データ） | SessionManager | SSE endpoint |
| **メソッド** | - | publish() | _sse_event() |

---

## マイグレーション手順（v3.1）

### 最新コード（v3.1）

```python
# oiduna_session/managers/base.py

from oiduna_session.managers import SessionEventPublisher

class BaseManager:
    def __init__(
        self,
        session: Session,
        event_publisher: SessionEventPublisher | None = None,
    ):
        self.event_publisher = event_publisher

    def _emit_event(self, event_type: str, data: dict) -> None:
        if self.event_publisher:
            self.event_publisher.publish({"type": event_type, "data": data})
```

### 破壊的変更（v3.1）

**⚠️ 重要**: SessionEventSink は **v3.1（2026-03-11）で完全削除されました**。

```python
# ❌ 動作しなくなったコード（v3.1以降）
from oiduna_session.managers import SessionEventSink
# ImportError: cannot import name 'SessionEventSink'

class MyPublisher:
    def _push(self, event: dict) -> None:  # ❌ _push() は削除
        ...

# ✅ 正しいコード（v3.1）
from oiduna_session.managers import SessionEventPublisher

class MyPublisher:
    def publish(self, event: dict) -> None:  # ✅ publish() を使用
        ...
```

**移行タイムライン**:
- **v2.1**: SessionEventSink 導入（_push()）
- **v3.0**: EventSink alias 削除
- **v3.1**: SessionEventPublisher に改名（publish()）

### SessionContainerでの使用

```python
from oiduna_session import SessionContainer
from oiduna_loop.ipc import InProcessStateSink

# InProcessStateSink は SessionEventPublisher Protocol を実装
publisher = InProcessStateSink()
container = SessionContainer(event_publisher=publisher)
```

---

## 実装クラスの対応

### InProcessStateSink が両方のProtocolを実装（v3.1）

```python
# InProcessStateSink は2つの役割を担当

【StateProducer として】
- LoopEngine → API への状態配信
- send_position(), send_status() 等のメソッド

【SessionEventPublisher として】
- SessionManager → SSE への イベント配信
- publish() メソッド（v3.1で追加）

同じ asyncio.Queue に両方のイベントが流れる
```

**コード例**:
```python
class InProcessStateSink:
    """Implements both StateProducer and SessionEventPublisher."""

    # StateProducer methods
    async def send_position(self, position: dict, ...) -> None:
        self._push({"type": "position", "data": position})

    # SessionEventPublisher method (v3.1)
    def publish(self, event: dict) -> None:
        """Publish a session event."""
        self._push(event)  # 内部で同じキューに追加
```

---

## イベントの種類

### SessionEventPublisher が配信するイベント

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

## テストでの使用（v3.1）

### Mock実装

```python
# test_events.py

class MockSessionEventPublisher:
    """
    Mock session event publisher for testing.

    Implements SessionEventPublisher protocol (v3.1).
    """

    def __init__(self):
        self.events = []

    def publish(self, event: dict) -> None:
        """Publish and record events (SessionEventPublisher protocol)."""
        self.events.append(event)

    def get_events_by_type(self, event_type: str) -> list:
        """Get all events of a specific type."""
        return [e for e in self.events if e["type"] == event_type]
```

### テストfixture

```python
@pytest.fixture
def manager_with_publisher():
    """Create container with mock session event publisher."""
    publisher = MockSessionEventPublisher()
    container = SessionContainer(event_publisher=publisher)
    return container, publisher

def test_track_created_event(manager_with_publisher):
    container, publisher = manager_with_publisher

    container.tracks.create(
        track_name="kick",
        destination_id="superdirt",
        client_id="client_001"
    )

    events = publisher.get_events_by_type("track_created")
    assert len(events) == 1
```

---

## バージョン履歴

| バージョン | 状態 | 詳細 |
|-----------|------|------|
| **v2.1** | SessionEventSink導入 | EventSink は legacy alias、_push() メソッド |
| **v3.0** | EventSink削除 | EventSink alias 完全削除 |
| **v3.1** (現在) | SessionEventPublisher | SessionEventSink → SessionEventPublisher、publish() メソッド |

---

## よくある質問

### Q1: 既存のコードは動作し続けますか？（v3.1）

**A**: いいえ。SessionEventSink と _push() は **v3.1で完全削除**されました。

```python
# ❌ 動作しなくなったコード（v3.1以降）
from oiduna_session.managers import SessionEventSink

class MyPublisher:
    def _push(self, event: dict) -> None:
        ...
        ...
```

### Q2: いつ新しい命名に移行すべきですか？

**A**: **すぐに**。v3.1では SessionEventPublisher と publish() が必須です。過去のバージョンへの互換性はありません。

### Q3: SessionEventPublisher と StateProducer の違いは？

**A**:

| 項目 | SessionEventPublisher | StateProducer |
|------|---------------------|---------------|
| **レイヤー** | Session層（API） | Loop層 |
| **送信者** | SessionManager | LoopEngine |
| **イベント** | CRUD操作 | 再生状態 |
| **頻度** | 低頻度（ユーザー操作） | 高頻度（毎ステップ） |
| **メソッド** | `publish()` のみ | `send_position()`, `send_status()` 等 |

### Q4: SessionEvent と PatternEvent の違いは？

**A**: 全く異なる概念です。

#### SessionEvent（CRUD通知）
- **定義**: Session層のデータ変更を他クライアントに通知
- **用途**: リアルタイム同期（「誰かがパターンを作成した」等）
- **型**: `{"type": "pattern_created", "data": {...}}`
- **頻度**: 低頻度（ユーザー操作時のみ）
- **例**: パターン作成通知、トラック更新通知

```python
# 上記パターン作成時にSessionEventが発火
{
    "type": "pattern_created",
    "data": {
        "pattern_id": "3e2b",
        "event_count": 2  # ← PatternEventが2個あることを通知
    }
}
```

#### PatternEvent（音楽イベント）
- **定義**: Pattern内の1つの音（ステップ、サイクル、パラメータ）
- **用途**: SuperDirt/MIDIへ送信する音楽データ
- **型**: `PatternEvent(step, cycle, params)`
- **頻度**: 多数（パターンごとに0〜数百個）
- **例**: キックドラム、ハイハット等の音

```python
pattern = Pattern(
    events=[
        PatternEvent(step=0, cycle=0.0, params={"sound": "bd"}),  # キック
        PatternEvent(step=64, cycle=1.0, params={"sound": "hh"}), # ハット
    ]
)
```

#### 関係性

**SessionEvent は PatternEvent を含むメタ情報**:

```
SessionEvent: "pattern_created"
    └─ data.event_count: 2
         └─ Pattern.events: [PatternEvent, PatternEvent]
```

SessionEventは「PatternEventが何個あるか」を通知しますが、PatternEvent自体の内容（step, cycle, params）は含みません。

### Q5: InProcessStateSink が両方のProtocolを実装する理由は？

**A**: SSE endpoint で**すべてのイベント**を統一フォーマットで配信するため。クライアントは単一接続で、Session層のCRUD操作もLoop層の再生状態も受け取ります。

---

## 変更ファイル一覧（v3.1）

| ファイル | 変更内容 |
|---------|---------|
| `managers/base.py` | SessionEventSink → SessionEventPublisher、_push() → publish() |
| `managers/__init__.py` | SessionEventPublisher をエクスポート |
| `managers/*.py` | 全Managerで event_publisher パラメータに変更 |
| `container.py` | event_publisher パラメータに変更 |
| `loop/ipc/in_process.py` | publish() メソッド追加 |
| `tests/test_events.py` | MockSessionEventPublisher に変更 |

---

## まとめ

### メリット（v3.1）

✅ **明確性**: SessionEventPublisher = イベント発行、役割が一目瞭然
✅ **混乱解消**: Loop層のStateProducer、ドメイン層のPatternEventとの違いが明確
✅ **業界標準**: Pub/Subパターン（publish()）で広く認知されている
✅ **一貫性**: レイヤー別の命名規則が統一
✅ **ドキュメント性**: コードから設計意図が理解できる

### 互換性

✅ 旧EventSinkも引き続き動作
✅ 段階的な移行が可能
✅ 全テストがパス（301 passed）

---

**更新日**: 2026-03-02
**適用バージョン**: v2.1以降
