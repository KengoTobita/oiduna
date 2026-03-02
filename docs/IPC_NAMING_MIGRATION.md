# IPC Naming Migration Guide

## 概要

oiduna v2.1以降、IPCプロトコルの命名を**Producer/Consumerパターン**に移行しました。

この変更により、データの流れる方向と命名が直感的に一致し、コードの可読性が向上します。

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

### 段階2: 旧Protocolも互換性維持

既存の`CommandSource`, `StateSink`も引き続き使用可能です：

```python
# 互換性のため、両方の型を受け入れる
command_consumer: CommandConsumer | CommandSource
state_producer: StateProducer | StateSink
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
| **v2.1** (現在) | 新Protocolを追加 | CommandProducer, CommandConsumer, StateProducer, StateConsumer追加 |
| **v2.2** | 旧Protocol警告 | CommandSink, CommandSource, StateSink, StateSourceにdeprecation警告 |
| **v3.0** | 旧Protocol削除 | 旧Protocolを完全削除 |

---

## よくある質問

### Q1: 既存のコードは動作し続けますか？

**A**: はい。旧パラメータ名（`commands`, `publisher`）も互換性のため引き続きサポートされます。

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

---

## まとめ

### メリット

✅ **明確性**: Producer/Consumerで役割が一目瞭然
✅ **一貫性**: 変数名と型名が一致
✅ **直感性**: データフローが命名から理解できる
✅ **標準性**: 業界標準パターン（Kafka, RabbitMQ等）

### 互換性

✅ 旧Protocolも引き続き動作
✅ 段階的な移行が可能
✅ 全テストがパス（301 passed）

---

**更新日**: 2026-03-02
**適用バージョン**: v2.1以降
