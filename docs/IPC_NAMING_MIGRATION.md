# IPC and Event Naming Migration Guide

**⚠️ v3.1 重要**: 複数の命名改善が実施されました（2026-03-11）：
- Loop層IPC: CommandSink/Source, StateSink/Source → Producer/Consumer（v3.0完了）
- ドメイン層: Event → **PatternEvent**（v3.1）
- Session層: SessionEventSink → **SessionEventPublisher**（v3.1）

詳細は [ADR-0021](knowledge/adr/0021-backward-compatibility-removal.md) を参照。

---

## 概要

oiduna v2.1以降、命名を段階的に改善し、用語の曖昧性を解消しました：

1. **Loop層IPC命名**（v2.1-v3.0）: Producer/Consumerパターン
2. **ドメイン層Event命名**（v3.1）: Event → PatternEvent
3. **Session層EventSink命名**（v3.1）: SessionEventSink → SessionEventPublisher

この変更により、データの流れる方向と命名が直感的に一致し、コードの可読性が向上します。

**移行タイムライン**:
- **v2.1**: Producer/Consumer導入（IPC）
- **v3.0**: Sink/Source旧名を完全削除（ADR-0021）
- **v3.1**: Event → PatternEvent、SessionEventPublisher導入

## 変更の背景

### 旧命名の問題点（Sink/Source）

```python
# 旧命名（混乱しやすい）
class LoopEngine:
    def __init__(
        self,
        commands: CommandSource,    # Loop側で「受信」するのにSource?
        publisher: StateSink,       # Loop側で「送信」するのにSink?
    ):
        self._commands = commands
        self._publisher = publisher
```

**混乱のポイント**：
- 一般的に「Sink」= 受信先、「Source」= 送信元
- しかし`StateSink`は実際には**送信**している
- 変数名が`publisher`なのに、型は`StateSink`

### 新命名（Producer/Consumer）

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

**改善点**：
- Producer = 送信（生産）、Consumer = 受信（消費）が一目瞭然
- 変数名と型名が一致
- データフローが直感的

---

## 新しい命名マッピング

| 旧名 | 新名 | 使用側 | 役割 |
|-----|------|--------|------|
| `CommandSink` | `CommandProducer` | API | コマンド送信 |
| `CommandSource` | `CommandConsumer` | Loop | コマンド受信 |
| `StateSink` | `StateProducer` | Loop | 状態送信 |
| `StateSource` | `StateConsumer` | API | 状態受信 |

---

## データフロー図

```
┌──────────────────┐                    ┌───────────────────┐
│   oiduna_api     │                    │   oiduna_loop     │
├──────────────────┤                    ├───────────────────┤
│ CommandProducer  │ ─── commands ───►  │ CommandConsumer   │
│                  │                    │                   │
│ StateConsumer    │ ◄─── state ─────   │ StateProducer     │
└──────────────────┘                    └───────────────────┘
```

---

## マイグレーション手順

### 段階1: 新しいProtocolを使用（推奨）

```python
# oiduna_loop/engine/loop_engine.py

from oiduna_loop.protocols import CommandConsumer, StateProducer

def __init__(
    self,
    osc: OscOutput,
    midi: MidiOutput,
    command_consumer: CommandConsumer,  # 新しいパラメータ名
    state_producer: StateProducer,      # 新しいパラメータ名
):
    self._command_consumer = command_consumer
    self._state_producer = state_producer
```

### 段階2: 旧Protocolの削除（v3.0で完了）

**⚠️ 重要**: 旧Protocol名は **v3.0（2026-03-11）で完全削除されました**。

```python
# ❌ 動作しなくなったコード（v3.0以降）
from oiduna_loop.ipc.protocols import CommandSource
# ImportError: cannot import name 'CommandSource'

# ❌ Union型も削除
command_consumer: CommandConsumer | CommandSource  # エラー

# ✅ 正しいコード
from oiduna_loop.ipc.protocols import CommandConsumer
command_consumer: CommandConsumer
```

### 段階3: Factoryでの使用

```python
# oiduna_loop/factory.py

def create_loop_engine(
    osc_host: str = "127.0.0.1",
    osc_port: int = 57120,
    midi_port: str | None = None,
    command_consumer: CommandConsumer | None = None,  # 新しいパラメータ
    state_producer: StateProducer | None = None,      # 新しいパラメータ
    # Legacy parameters (deprecated)
    command_source: CommandSource | None = None,
    state_sink: StateSink | None = None,
) -> LoopEngine:
    # Legacy parameterのフォールバック
    final_command_consumer = command_consumer or command_source
    final_state_producer = state_producer or state_sink

    return LoopEngine(
        command_consumer=final_command_consumer,
        state_producer=final_state_producer,
    )
```

---

## 実装クラスの対応

### NoopCommandSource → CommandConsumer実装

```python
# in_process.py

class NoopCommandSource:
    """
    No-op command consumer (CommandConsumer protocol).

    Implements CommandConsumer protocol (formerly CommandSource).

    This class satisfies both CommandConsumer and CommandSource (legacy) protocols.
    """
    async def process_commands(self) -> int:
        return 0
```

### InProcessStateSink → StateProducer実装

```python
# in_process.py

class InProcessStateSink:
    """
    In-process state producer (StateProducer protocol).

    Implements StateProducer protocol (formerly StateSink).

    This class satisfies both StateProducer and StateSink (legacy) protocols.
    """
    async def send_position(...) -> None:
        ...
```

---

## テストでの使用

### Fixture更新例

```python
# conftest.py

@pytest.fixture
def test_engine(
    mock_osc: MockOscOutput,
    mock_midi: MockMidiOutput,
    mock_commands: MockCommandSource,
    mock_publisher: MockStateSink,
) -> LoopEngine:
    engine = LoopEngine(
        osc=mock_osc,
        midi=mock_midi,
        command_consumer=mock_commands,  # 新しいパラメータ名
        state_producer=mock_publisher,   # 新しいパラメータ名
    )
    return engine
```

---

## 廃止予定スケジュール

| バージョン | 状態 | 詳細 |
|-----------|------|------|
| **v2.1** | 新Protocolを追加 | CommandProducer, CommandConsumer, StateProducer, StateConsumer追加 |
| **v2.2** | 旧Protocol警告 | CommandSink, CommandSource, StateSink, StateSourceにdeprecation警告 |
| **v3.0** | 旧Protocol削除 | IPC旧Protocolを完全削除（2026-03-11） |
| **v3.1** (現在) | Event/EventSink改名 | Event → PatternEvent、SessionEventSink → SessionEventPublisher |

---

## よくある質問

### Q1: 既存のコードは動作し続けますか？

**A**: **いいえ（v3.0以降）**。旧Protocol名（CommandSink/Source, StateSink/Source）は完全削除されました。
すべてのコードで新しいProducer/Consumer命名を使用する必要があります。

```python
# 旧コード（v2.1でも動作）
engine = LoopEngine(
    osc=osc,
    midi=midi,
    commands=command_source,  # 旧パラメータ名
    publisher=state_sink,     # 旧パラメータ名
)
```

### Q2: いつ新しい命名に移行すべきですか？

**A**: 新しいコードは即座に新命名を使用することを推奨します。既存コードは段階的に移行できます。

### Q3: 内部変数名も変更されましたか？

**A**: はい。LoopEngine内部では：
- `self._commands` → `self._command_consumer` （エイリアスとして`_commands`も残存）
- `self._publisher` → `self._state_producer` （エイリアスとして`_publisher`も残存）

### Q4: Event → PatternEvent の変更理由は？（v3.1）

**A**: 「Event」という用語が3つの異なる意味で使われ、混乱を引き起こしていました：

1. **PatternEvent（旧Event）**: ドメイン層の音楽イベント（step, cycle, params）
2. **SessionEvent**: Session層のCRUD通知（dict型）
3. **SSE Event**: HTTP層のServer-Sent Events（string）

「Event」から「PatternEvent」への改名により、役割が明確になりました。

詳細は [TERMINOLOGY.md](TERMINOLOGY.md) の「Event用語の分類」セクションを参照。

---

## まとめ

### メリット（v3.1）

✅ **明確性**: Producer/Consumerで役割が一目瞭然
✅ **一貫性**: 変数名と型名が一致
✅ **直感性**: データフローが命名から理解できる
✅ **標準性**: 業界標準パターン（Kafka, RabbitMQ等）
✅ **Event曖昧性解消**: PatternEvent、SessionEvent、SSE Eventの責任が明確

### 互換性（v3.1）

❌ **後方互換性なし**: 旧Protocol名（CommandSink/Source, StateSink/Source）は完全削除
❌ **後方互換性なし**: Event → PatternEvent、SessionEventSink → SessionEventPublisher
✅ 全テストがパス（680 passed）
✅ 型安全性維持（mypy strict）

---

**更新日**: 2026-03-11
**適用バージョン**: v3.1以降
