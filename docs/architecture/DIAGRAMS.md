# Oiduna アーキテクチャ図

**バージョン**: 1.0.0
**作成日**: 2026-03-11
**対象**: Oiduna開発者

このドキュメントは、Oidunaシステムのアーキテクチャを視覚化したMermaid図を提供します。

## 目次

1. [Layer 1-4 処理フロー](#layer-1-4-処理フロー)
2. [Producer/Consumer IPC関係](#producerconsumer-ipc関係)
3. [SessionContainer + Managers構成](#sessioncontainer--managers構成)
4. [パッケージ間依存関係](#パッケージ間依存関係)
5. [Event用語の3つの文脈](#event用語の3つの文脈)

---

## Layer 1-4 処理フロー

Oidunaは4層のデータ変換アーキテクチャで構成されています。

```mermaid
flowchart TB
    subgraph Layer1["Layer 1: 階層モデル層（ユーザー向け）"]
        Session[Session]
        Track[Track]
        Pattern[Pattern]
        PatternEvent[PatternEvent]

        Session -->|contains| Track
        Track -->|contains| Pattern
        Pattern -->|contains| PatternEvent
    end

    subgraph Layer2["Layer 2: メッセージフォーマット層（プロトコル非依存）"]
        LS[LoopSchedule]
        SE[ScheduleEntry]

        SMB -->|contains tuple| SM
    end

    subgraph Layer3["Layer 3: スケジューリング・ルーティング層（最適化）"]
        LS[LoopScheduler<br/>O1 step lookup]
        DR[DestinationRouter<br/>destination grouping]

        MS -->|routes to| DR
    end

    subgraph Layer4["Layer 4: プロトコル実装層"]
        OSC[OscDestinationSender]
        MIDI[MidiDestinationSender]

        DR -->|OSC protocol| OSC
        DR -->|MIDI protocol| MIDI
    end

    Layer1 -->|SessionCompiler| Layer2
    Layer2 -->|load_messages| Layer3
    Layer3 -->|send_messages| Layer4

    OSC -->|pythonosc| SuperDirt[SuperDirt/SuperCollider]
    MIDI -->|mido| Device[MIDI Device]

    style Layer1 fill:#e1f5ff
    style Layer2 fill:#fff4e1
    style Layer3 fill:#ffe1f5
    style Layer4 fill:#e1ffe1
```

**責務の分離**:
- **Layer 1**: データバリデーションのみ（Pydantic）
- **Layer 2**: Destination-Agnosticな表現（frozen dataclass）
- **Layer 3**: パフォーマンス最適化（O(1)検索、ルーティング）
- **Layer 4**: プロトコル固有の送信処理

**コード参照**:
- Layer 1: `packages/oiduna_models/`
- Layer 2: `packages/oiduna_scheduler/scheduler_models.py`
- Layer 3: `packages/oiduna_scheduler/scheduler.py`, `router.py`
- Layer 4: `packages/oiduna_scheduler/senders.py`

---

## Producer/Consumer IPC関係

API層とLoop層の間で双方向のIPC通信を行います。

```mermaid
flowchart LR
    subgraph API["API層（FastAPI）"]
        CP[CommandProducer<br/>send_command]
        SC[StateConsumer<br/>consume]
    end

    subgraph Loop["Loop層（LoopEngine）"]
        CC[CommandConsumer<br/>receive_command]
        SP[StateProducer<br/>publish]
    end

    subgraph Commands["Command Types"]
        Play[Play]
        Stop[Stop]
        Pause[Pause]
        Compile[Compile]
        Mute[Mute/Solo]
        SetBpm[SetBpm]
    end

    subgraph States["State Types"]
        Position[Position<br/>step/beat/bar/cycle]
        Playback[PlaybackState<br/>PLAYING/PAUSED/STOPPED]
        Errors[Errors]
        TrackInfo[TrackInfo]
    end

    CP -->|Command Flow| CC
    Commands -.->|types| CP

    SP -->|State Flow| SC
    States -.->|types| SP

    style API fill:#e1f5ff
    style Loop fill:#ffe1e1
    style Commands fill:#fff4e1
    style States fill:#e1ffe1
```

**実装の種類**:
- **InProcessStateProducer**: キューベース（単一プロセス）
- **ZeroMQ**: プロセス間通信（マルチプロセス）

**プロトコル定義**: `packages/oiduna_loop/ipc/protocols.py`

---

## SessionContainer + Managers構成

SessionContainerは6つの専門Managerを集約します。

```mermaid
classDiagram
    class SessionContainer {
        +ClientManager clients
        +TrackManager tracks
        +PatternManager patterns
        +EnvironmentManager environment
        +DestinationManager destinations
        +TimelineManager timeline
    }

    class ClientManager {
        +create(client_id, name, source)
        +get(client_id)
        +delete(client_id)
        -_emit_event(type, data)
    }

    class TrackManager {
        +create(track_id, name, dest_id)
        +get(track_id)
        +update(track_id, updates)
        +delete(track_id)
        -_emit_event(type, data)
    }

    class PatternManager {
        +create(pattern_id, track_id, events)
        +get(pattern_id)
        +update(pattern_id, updates)
        +archive(pattern_id)
        +move(pattern_id, new_track_id)
        -_emit_event(type, data)
    }

    class EnvironmentManager {
        +get()
        +update(updates)
        -_emit_event(type, data)
    }

    class DestinationManager {
        +get_all()
        +remove(destination_id)
    }

    class TimelineManager {
        +schedule_change(step, change)
        +cancel_change(change_id)
    }

    class BaseManager {
        <<Protocol>>
        +_emit_event(type, data)*
    }

    class SessionChangePublisher {
        <<Protocol>>
        +publish(event)*
    }

    SessionContainer --> ClientManager
    SessionContainer --> TrackManager
    SessionContainer --> PatternManager
    SessionContainer --> EnvironmentManager
    SessionContainer --> DestinationManager
    SessionContainer --> TimelineManager

    ClientManager ..|> BaseManager
    TrackManager ..|> BaseManager
    PatternManager ..|> BaseManager
    EnvironmentManager ..|> BaseManager

    BaseManager ..> SessionChangePublisher : uses
```

**設計パターン**:
- **Container Pattern**: SessionContainerは軽量コンテナ（Facadeパターン廃止）
- **Single Responsibility**: 各Managerは単一ドメインのCRUD操作のみ
- **Protocol-Based**: BaseManagerとSessionChangePublisherでインターフェース定義

**コード参照**:
- `packages/oiduna_session/container.py` - SessionContainer
- `packages/oiduna_session/managers/base.py` - BaseManager protocol
- `packages/oiduna_session/managers/*_manager.py` - 各Manager実装

---

## パッケージ間依存関係

単方向依存を維持し、循環依存を避けます。

```mermaid
flowchart TD
    API[oiduna_api<br/>FastAPI routes]
    Session[oiduna_session<br/>SessionContainer + Managers]
    Loop[oiduna_loop<br/>LoopEngine]
    Scheduler[oiduna_scheduler<br/>LoopScheduler + Router]
    Models[oiduna_models<br/>Pydantic models]
    Auth[oiduna_auth<br/>Authentication]
    Timeline[oiduna_timeline<br/>Timeline management]

    API --> Session
    API --> Loop
    API --> Auth

    Session --> Models
    Session --> Auth

    Loop --> Scheduler
    Loop --> Models

    Scheduler --> Models

    Timeline --> Models

    style Models fill:#e1f5ff
    style API fill:#ffe1e1
    style Session fill:#fff4e1
    style Loop fill:#e1ffe1
    style Scheduler fill:#f5e1ff
```

**依存ルール**:
- **oiduna_models**: 最下層、他に依存しない
- **oiduna_scheduler**: modelsのみに依存
- **oiduna_session**: models、authに依存
- **oiduna_loop**: scheduler、modelsに依存
- **oiduna_api**: 上位層、すべてに依存可能

**循環依存の禁止**:
```python
# ✅ OK: Higher layer → Lower layer
from oiduna_models import Track
from oiduna_scheduler import LoopScheduler

# ❌ NG: Lower layer → Higher layer
# oiduna_models内で oiduna_api をimportしてはいけない
```

**コード参照**: 各パッケージの`__init__.py`と`pyproject.toml`

---

## Event用語の3つの文脈

Oidunaでは「Event」という用語が**3つの異なる文脈**で使用されます。

```mermaid
flowchart TB
    subgraph Domain["ドメイン層: PatternEvent（音楽イベント）"]
        PE[PatternEvent<br/>step: int<br/>cycle: float<br/>params: dict]
        Pattern[Pattern.events]

        Pattern -->|contains| PE
        PE -->|SessionCompiler| LS[LoopSchedule]
    end

    subgraph SessionLayer["Session層: SessionChange（CRUD変更通知）"]
        SE[SessionChange dict<br/>type: str<br/>data: dict]
        Manager[BaseManager._emit_change]
        Publisher[SessionChangePublisher.publish]

        Manager -->|emits| SE
        SE -->|published via| Publisher
    end

    subgraph HTTP["HTTP層: SSE Event（ストリーミング配信）"]
        SSE["SSE Event string<br/>event: type<br/>data: json"]
        Stream["/api/stream/events"]
        Browser[EventSource API]

        Stream -->|sends| SSE
        SSE -->|received by| Browser
    end

    SMB -->|to LoopEngine| Audio[Audio Playback]

    Publisher -->|queued to| Queue[InProcessStateProducer._queue]
    Queue -->|merged with| Stream

    style Domain fill:#e1f5ff
    style SessionLayer fill:#fff4e1
    style HTTP fill:#e1ffe1
```

**比較表**:

| 項目 | PatternEvent | SessionChange | SSE Event |
|------|-------------|---------------|-----------|
| **レイヤー** | ドメインモデル | Session層 | HTTP層 |
| **データ型** | PatternEvent class | dict | string |
| **目的** | 音楽的タイミング | CRUD変更通知 | HTTP配信 |
| **頻度** | 多数（パターン内） | 低頻度（操作時） | 高頻度（統合） |
| **送信先** | SessionCompiler | SSE endpoint | ブラウザ |

**データフロー**:
1. **PatternEvent**: Pattern → LoopSchedule → LoopEngine → 音楽再生
2. **SessionChange**: Manager → SessionChangePublisher → InProcessStateProducer queue
3. **SSE Event**: InProcessStateProducer queue → /api/stream/events → ブラウザ

**コード参照**:
- PatternEvent: `packages/oiduna_models/events.py`
- SessionChange: `packages/oiduna_session/managers/base.py`
- SSE Event: `packages/oiduna_api/routes/stream.py`

---

## 追加の図

### Timing Model（タイミングモデル）

```mermaid
flowchart LR
    subgraph Loop["1 Loop = 256 steps = 4.0 cycles"]
        subgraph Bar0["Bar 0 (0-15 steps)"]
            Beat0["Beat 0<br/>0-3 steps"]
            Beat1["Beat 1<br/>4-7 steps"]
            Beat2["Beat 2<br/>8-11 steps"]
            Beat3["Beat 3<br/>12-15 steps"]
        end

        subgraph Bar1["Bar 1 (16-31 steps)"]
            Beat4["..."]
        end

        subgraph Bar2["Bar 2 (32-47 steps)"]
            Beat8["..."]
        end

        subgraph Bar3["Bar 3 (48-63 steps)"]
            Beat12["..."]
        end

        Bar0 --> Bar1
        Bar1 --> Bar2
        Bar2 --> Bar3
    end

    Loop -->|repeats| Loop

    style Bar0 fill:#e1f5ff
    style Bar1 fill:#fff4e1
    style Bar2 fill:#ffe1f5
    style Bar3 fill:#e1ffe1
```

**時間単位の関係式**:
```
1 step    = 1/16 note
4 steps   = 1 beat (1/4 note)
16 steps  = 1 bar (4 beats)
256 steps = 16 beats = 4 bars = 1 loop = 4.0 cycles
```

**BPMと時間**（120 BPM）:
- 1 step = 125ms
- 1 beat = 500ms
- 1 bar = 2秒
- 1 loop = 32秒

**コード参照**: `packages/oiduna_loop/engine/loop_engine.py:23` (LOOP_STEPS = 256)

---

## まとめ

これらの図は、Oidunaシステムのアーキテクチャを視覚的に理解するためのリファレンスです。

**重要な設計原則**:
1. **Layer分離**: Layer 1-4で責務を明確に分離
2. **双方向IPC**: Producer/Consumerパターンで疎結合
3. **Manager分離**: SessionContainerで単一責任原則を実現
4. **単方向依存**: パッケージ間の循環依存を排除
5. **Event用語の区別**: 3つの異なる文脈を明確化

**参考ドキュメント**:
- [ARCHITECTURE.md](../ARCHITECTURE.md) - システム全体のアーキテクチャ
- [TERMINOLOGY.md](../TERMINOLOGY.md) - 用語集
- [OIDUNA_CONCEPTS.md](../OIDUNA_CONCEPTS.md) - 設計哲学
- [CODING_CONVENTIONS.md](../CODING_CONVENTIONS.md) - コーディング規約

---

**バージョン**: 1.0.0
**作成日**: 2026-03-11
**メンテナンス**: アーキテクチャ変更時は図を更新
