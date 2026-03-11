# ADR-017: IPC and Session Naming Standardization

## Status

**Accepted** - 2026-03-02

## Context

Oidunaプロジェクトにおいて、IPCプロトコルとSession層のイベント配信機構に命名上の混乱が存在していた。

### 問題1: IPC層のSink/Source命名の混乱

```python
# 旧命名（混乱しやすい）
class LoopEngine:
    def __init__(
        self,
        commands: CommandSource,    # Loop側で「受信」するのにSource?
        publisher: StateSink,       # Loop側で「送信」するのにSink?
    ):
        ...
```

**問題点**:
- 一般的に「Sink」= 受信先、「Source」= 送信元
- しかし`StateSink`は実際には**送信**している
- 変数名が`publisher`なのに、型は`StateSink`
- データフローの方向と命名が直感的に一致しない

### 問題2: EventSink vs StateSinkの混同

```python
# 異なるレイヤーで似た名前

【EventSink】 - Session層のCRUD イベント
定義: oiduna_session/managers/base.py
用途: track_created, pattern_updated 等

【StateSink】 - Loop層の状態配信
定義: oiduna_loop/ipc/protocols.py
用途: position, status, error 等
```

**問題点**:
- 両方とも「イベント/状態」を扱うが、**異なるレイヤー**
- `EventSink`と`StateSink`という名前が似ている
- どちらがどの責任を持つか不明確
- InProcessStateProducerが両方のProtocolを実装することで混乱が増す

## Decision

### 決定1: IPC層をProducer/Consumerパターンに統一

**新しい命名マッピング**:

| 旧名 | 新名 | 使用側 | 役割 |
|-----|------|--------|------|
| `CommandSink` | `CommandProducer` | API | コマンド送信 |
| `CommandSource` | `CommandConsumer` | Loop | コマンド受信 |
| `StateSink` | `StateProducer` | Loop | 状態送信 |
| `StateSource` | `StateConsumer` | API | 状態受信 |

**データフロー**:
```
API側(oiduna_api)      →  Loop側(oiduna_loop)
CommandProducer        →  CommandConsumer    (コマンド送信)
StateConsumer          ←  StateProducer      (状態受信)
```

**実装例**:
```python
# 新命名（明確）
class LoopEngine:
    def __init__(
        self,
        command_consumer: CommandConsumer,  # ✅ Loop側でcommandを消費
        state_producer: StateProducer,      # ✅ Loop側でstateを生産
    ):
        self._command_consumer = command_consumer
        self._state_producer = state_producer
```

### 決定2: Session層をSessionEventSinkに明確化

**新しい命名**:

| 旧名 | 新名 | レイヤー | 責任 |
|-----|------|---------|------|
| `EventSink` | `SessionEventSink` | Session層 | CRUD操作イベント配信 |

**実装例**:
```python
class SessionEventSink(Protocol):
    """
    Session層のCRUDイベント配信Protocol.

    Loop層のStateProducerとは異なる責任を持つ。
    """
    def _push(self, event: dict[str, Any]) -> None: ...

# Legacy alias
EventSink = SessionEventSink
```

### 後方互換性の維持

両方の変更において、既存の命名をlegacy aliasとして保持：

```python
# IPC層
CommandSink = CommandProducer      # DEPRECATED
CommandSource = CommandConsumer    # DEPRECATED
StateSink = StateProducer          # DEPRECATED
StateSource = StateConsumer        # DEPRECATED

# Session層
EventSink = SessionEventSink       # DEPRECATED
```

## Consequences

### メリット

#### 1. 命名の直感性向上

```python
# Producer/Consumerパターン
command_consumer.process_commands()  # ✅ consumeすることが明確
state_producer.send_position(...)    # ✅ produceすることが明確

# Session層の明確化
SessionEventSink  # ✅ Session層のイベントと明確
StateProducer     # ✅ Loop層の状態配信と明確
```

#### 2. レイヤー境界の明確化

```
【SessionEventSink】 - Session層
- CRUD操作イベント（track_created, pattern_updated等）
- 低頻度（ユーザー操作時）
- SessionManager が送信

【StateProducer】 - Loop層
- 再生状態（position, status, error等）
- 高頻度（毎ステップ～15秒）
- LoopEngine が送信
```

#### 3. 業界標準パターンとの整合

Producer/Consumerパターンは以下のシステムで採用されている標準的な命名：
- Apache Kafka
- RabbitMQ
- Redis Streams

#### 4. コードの可読性向上

変数名と型名が一致：
```python
# Before
publisher: StateSink          # 変数名とprotocol名が不一致

# After
state_producer: StateProducer  # 変数名とprotocol名が一致
```

### デメリット

#### 1. 既存コードの段階的移行が必要

- 影響範囲: IPC層（protocols.py, factory.py, loop_engine.py等）
- 影響範囲: Session層（managers/base.py, container.py, tests等）
- 移行期間中は両方の命名が共存

#### 2. ドキュメントの更新コスト

- Architecture図の更新
- Migration Guideの作成
- API ドキュメントの改訂

### リスク軽減策

1. **段階的廃止スケジュール**:
   - v2.1: 新Protocol追加、legacy aliasサポート
   - v2.2: 旧Protocolにdeprecation警告
   - v3.0: 旧Protocol削除

2. **完全な後方互換性**:
   - Legacy aliasにより既存コードがそのまま動作
   - テスト: 301 passed（全テスト成功）

3. **詳細なMigration Guide**:
   - IPC_NAMING_MIGRATION.md
   - SESSION_EVENT_SINK_MIGRATION.md

## Alternatives Considered

### 代替案1: Sender/Receiverパターン

```python
CommandSender / CommandReceiver
StateSender / StateReceiver
```

**却下理由**:
- Producer/Consumerほど明確でない
- 業界標準パターンとしての認知度が低い

### 代替案2: Publisher/Subscriberパターン

```python
CommandPublisher / CommandSubscriber
StatePublisher / StateSubscriber
```

**却下理由**:
- Pub/Subは複数の購読者を想定（oidunaは1:1）
- セマンティックな過剰性

### 代替案3: コメント強化のみ

既存の命名を維持し、詳細なコメントで補足。

**却下理由**:
- コードから直感的に理解できない
- 開発者が常にコメントを参照する必要がある
- 根本的な解決にならない

## Implementation

### 変更ファイル

**IPC層**:
- `oiduna_loop/ipc/protocols.py` - 新Protocol定義追加
- `oiduna_loop/ipc/in_process.py` - ドキュメント更新
- `oiduna_loop/engine/loop_engine.py` - パラメータ名更新
- `oiduna_loop/factory.py` - パラメータ名更新
- `oiduna_loop/protocols/__init__.py` - Export更新
- `oiduna_loop/tests/conftest.py` - テストfixture更新

**Session層**:
- `oiduna_session/managers/base.py` - SessionEventSink追加
- `oiduna_session/managers/__init__.py` - Export更新
- `oiduna_session/container.py` - 型ヒント更新
- `oiduna_session/tests/test_events.py` - Mock実装更新

**ドキュメント**:
- `docs/IPC_NAMING_MIGRATION.md` - IPC移行ガイド
- `docs/SESSION_EVENT_SINK_MIGRATION.md` - Session移行ガイド

### テスト結果

```
✅ 301 passed, 8 skipped
✅ oiduna_loop: 106 passed
✅ oiduna_session: 103 passed
✅ 全パッケージ: 問題なし
```

## References

- [IPC_NAMING_MIGRATION.md](../../IPC_NAMING_MIGRATION.md)
- [SESSION_EVENT_SINK_MIGRATION.md](../../SESSION_EVENT_SINK_MIGRATION.md)
- [Layer 5: Data Layer](../architecture/layer-5-data.md)
- Apache Kafka Producer/Consumer API: https://kafka.apache.org/documentation/
- RabbitMQ Producer/Consumer: https://www.rabbitmq.com/tutorials/tutorial-one-python.html

## Notes

### 命名原則

今後のoidunaプロジェクトにおける命名原則として以下を採用：

1. **Producer/Consumerパターン**: データフローを表現する際の標準命名
2. **レイヤー接頭辞**: 混乱を避けるため、レイヤー名を接頭辞として使用（SessionEventSink等）
3. **直感的な命名**: 変数名と型名を一致させ、データフローを明示

### 将来の拡張

この命名原則は、将来の以下の機能にも適用される：

- ZeroMQ/Redis等の外部IPC実装
- 複数のStateConsumer（Monitor、Logger等）
- クラスタリング時のノード間通信

---

**記録者**: Claude Sonnet 4.5
**承認日**: 2026-03-02
**実装バージョン**: v2.1
