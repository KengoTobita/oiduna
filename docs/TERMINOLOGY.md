# Oiduna用語集

**バージョン**: 2.0.0 (ScheduledMessageBatch統合版)
**作成日**: 2026-02-27

## クイックリファレンス

### 主要概念

| 用語 | 英語 | 説明 |
|------|------|------|
| ScheduledMessageBatch | Scheduled Message Batch | パターン全体を表現するデータ構造 |
| ScheduledMessage | Scheduled Message | 単一の送信イベント |
| MessageScheduler | Message Scheduler | ステップ別インデックス化 |
| DestinationRouter | Destination Router | 送信先別振り分け |
| RuntimeState | Runtime State | 再生状態管理 |

---

## Oidunaの核となる概念

### Oidunaとは

**定義**: Destination-Agnostic リアルタイム音楽パターン再生エンジン

**入力**: HTTP経由のJSON（ScheduledMessageBatch形式）
**出力**: OSC（SuperDirt等）+ MIDI（デバイス）+ カスタム送信先

**特徴**:
- 送信先に依存しない設計
- 256ステップループ（16ビート）
- O(1)高速メッセージ検索
- 拡張可能なアーキテクチャ

---

## データ構造の用語

### Event用語の分類（重要）

Oidunaでは「Event」という用語が**3つの異なる意味**で使用されています。
それぞれ異なるレイヤーに属し、目的が全く異なります。

#### 1️⃣ PatternEvent（パターン内音楽イベント）

**定義**: Pattern内の1つの音楽的イベント（ステップ、サイクル、パラメータ）

**レイヤー**: ドメインモデル層（oiduna_models）

**データ型**:
```python
PatternEvent(
    step: int,        # 0-255（量子化ステップ）
    cycle: float,     # 0.0-4.0（精密タイミング）
    params: dict      # 音響パラメータ
)
```

**使用箇所**:
- `Pattern.events: list[PatternEvent]` - パターンが持つ音楽イベントリスト
- SessionCompiler で ScheduledMessage に変換される

**例**:
```python
# キックドラム（ステップ0）
kick = PatternEvent(step=0, cycle=0.0, params={"sound": "bd", "gain": 0.8})

# ハイハット（ステップ64）
hihat = PatternEvent(step=64, cycle=1.0, params={"sound": "hh", "gain": 0.6})
```

**頻度**: 多数（パターンごとに0〜数百個）

---

#### 2️⃣ SessionEvent（CRUD操作イベント）

**定義**: Session層のデータ変更を通知するイベント（辞書型）

**レイヤー**: Session層（oiduna_session）

**データ型**:
```python
{
    "type": str,     # イベント種別（例: "track_created"）
    "data": dict     # イベント固有データ
}
```

**イベント種類** (29種):
- Client: `client_connected`, `client_disconnected`
- Track: `track_created`, `track_updated`, `track_deleted`
- Pattern: `pattern_created`, `pattern_updated`, `pattern_archived`, `pattern_moved`
- Environment: `environment_updated`
- Destination: `destination_removed`
- Timeline: `change_scheduled`, `change_cancelled`

**Protocol**: `SessionEventPublisher.publish(event: dict)`

**使用箇所**:
- `BaseManager._emit_event()` - 各Managerから発火
- `InProcessStateSink.publish()` - SSE配信用キューに蓄積

**例**:
```python
# パターン作成通知
{
    "type": "pattern_created",
    "data": {
        "pattern_id": "3e2b",
        "track_id": "0a1f",
        "client_id": "alice",
        "event_count": 2  # ← PatternEventが2個あることを通知
    }
}
```

**頻度**: 低頻度（ユーザー操作時のみ）

---

#### 3️⃣ SSE Event（HTTPストリーミングイベント）

**定義**: Server-Sent Events（HTTP仕様）のイベント形式

**レイヤー**: HTTP層（oiduna_api）

**データ型**: 文字列（HTTP SSE形式）
```
event: {event_type}
data: {json_data}

```

**使用箇所**:
- `/api/stream/events` endpoint
- `_sse_event()` - SSE形式への変換関数
- ブラウザの `EventSource` APIで受信

**統合配信**: SessionEvent と StateProducer の両方を統合配信

**例**:
```
event: pattern_created
data: {"pattern_id": "3e2b", "event_count": 2}

event: position
data: {"step": 0, "beat": 0, "cycle": 0.0}

event: heartbeat
data: {"timestamp": 1234567890.123}
```

**頻度**: 高頻度（SessionEvent + StateProducer の統合）

---

#### Event用語の比較表

| 項目 | PatternEvent | SessionEvent | SSE Event |
|------|-------------|--------------|-----------|
| **レイヤー** | ドメインモデル | Session層 | HTTP層 |
| **データ型** | PatternEvent class | dict | string |
| **目的** | 音楽的タイミング | CRUD通知 | HTTP配信 |
| **頻度** | 多数（パターン内） | 低頻度（操作時） | 高頻度（統合） |
| **送信先** | SessionCompiler | SSE endpoint | ブラウザ |
| **例** | `PatternEvent(step=0, ...)` | `{"type": "track_created"}` | `"event: ...\ndata: ...\n\n"` |

#### データフロー全体図

```
┌─────────────────────────────────────────────────────┐
│ ドメイン層: PatternEvent（音楽イベント）              │
│   Pattern.events: list[PatternEvent]                │
│       ↓ SessionCompiler                             │
│   ScheduledMessageBatch                             │
│       ↓ Loop Engine                                 │
│   音楽再生                                           │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Session層: SessionEvent（CRUD通知）                  │
│   BaseManager._emit_event()                         │
│       ↓ SessionEventPublisher.publish()             │
│   InProcessStateSink._queue ←┐                      │
└──────────────────────────────┼──────────────────────┘
                               │
┌──────────────────────────────┼──────────────────────┐
│ Loop層: StateProducer（再生状態）                    │
│   LoopEngine.send_position() │                      │
│       ↓ StateProducer        │                      │
│   InProcessStateSink._queue ─┘                      │
└──────────────────────────────┬──────────────────────┘
                               │ 統合キュー
                               ↓
┌─────────────────────────────────────────────────────┐
│ HTTP層: SSE Event（ストリーミング配信）              │
│   /api/stream/events                                │
│       ↓ _sse_event()                                │
│   EventSource API（ブラウザ）                        │
└─────────────────────────────────────────────────────┘
```

#### 命名の歴史

- **v3.0以前**: 全て「Event」と呼ばれ、混乱の原因
- **v3.1**: PatternEvent に改名、SessionEventPublisher Protocol導入
- SessionEvent は Protocol名（SessionEventPublisher）で区別
- SSE Event は HTTP仕様の用語として明示

---

### パターンデータ

| 用語 | 型 | 説明 |
|------|---|------|
| ScheduledMessageBatch | dataclass | パターン全体（messages + bpm + pattern_length） |
| ScheduledMessage | dataclass | 単一イベント（destination_id + cycle + step + params） |
| params | dict[str, Any] | 送信先依存のパラメータ |

**ScheduledMessageBatchの構造**:
```python
ScheduledMessageBatch
├── messages: tuple[ScheduledMessage, ...]
├── bpm: float (デフォルト: 120.0)
└── pattern_length: float (デフォルト: 4.0サイクル)
```

**ScheduledMessageの構造**:
```python
ScheduledMessage
├── destination_id: str (例: "superdirt", "volca_bass")
├── cycle: float (サイクル位置: 0.0-4.0)
├── step: int (ステップ番号: 0-255)
└── params: dict[str, Any] (送信先依存)
```

### 再生状態

| 用語 | 型 | 説明 |
|------|---|------|
| RuntimeState | class | 再生状態、BPM、Mute/Solo管理 |
| PlaybackState | enum | PLAYING, PAUSED, STOPPED |
| Position | dataclass | ループ内の現在位置 |

**PlaybackState**:
- `PLAYING`: 再生中
- `PAUSED`: 一時停止（位置を保持）
- `STOPPED`: 停止（位置を0にリセット）

**Position**:
```python
Position
├── step: int (0-255)
├── beat: int (0-15)
├── bar: int (0-3)
└── cycle: float (0.0-4.0)
```

### 送信先

| 用語 | 説明 |
|------|------|
| Destination | 送信先（SuperDirt、MIDIデバイス、カスタム） |
| destination_id | 送信先の識別子（destinations.yamlで定義） |
| DestinationRouter | 送信先別振り分けクラス |
| DestinationSender | 送信先固有の送信実装 |

**送信先の種類**:
- **OscDestinationSender**: OSCプロトコル（SuperDirt等）
- **MidiDestinationSender**: MIDIプロトコル（MIDIデバイス）
- **カスタムSender**: 拡張機能で追加可能

---

## 処理フロー用語

### コア処理

| 用語 | 説明 |
|------|------|
| MessageScheduler | ScheduledMessageBatchをインデックス化 |
| ステップインデックス | dict[int, list[int]] によるO(1)検索 |
| DestinationRouter | destination_idによる自動振り分け |
| filter_messages | Mute/Soloによるメッセージフィルタリング |

**MessageSchedulerの処理**:
```
ScheduledMessageBatch
  ↓ load_messages()
ステップ別インデックス構築
  ↓ get_messages_for_step(step)
該当ステップのメッセージリスト (O(1))
```

**DestinationRouterの処理**:
```
list[ScheduledMessage]
  ↓ send_messages()
送信先別にグループ化
  ↓
各DestinationSenderに送信
  ├→ OscDestinationSender → OSC送信
  └→ MidiDestinationSender → MIDI送信
```

### 拡張機能

| 用語 | 説明 |
|------|------|
| Extension | 拡張機能（ScheduledMessageBatchを変換） |
| ExtensionPipeline | 拡張機能のチェーン実行 |
| BeforeSend Hook | メッセージ送信前の変換フック |

**ExtensionPipelineの処理**:
```
ScheduledMessageBatch
  ↓ apply()
Extension 1 (変換)
  ↓
Extension 2 (変換)
  ↓
変換後のScheduledMessageBatch
```

---

## 音楽用語

### 時間単位

| 用語 | 説明 | 換算 |
|------|------|------|
| ステップ | 1/16音符単位 | 256ステップ = 16ビート |
| ビート | 4分音符単位 | 16ビート = 4小節 |
| サイクル | TidalCycles由来の単位 | 4.0サイクル = 4小節 |
| BPM | Beats Per Minute | 120 BPM = 2ビート/秒 |

**時間換算表（120 BPM）**:
| 単位 | 時間 |
|------|------|
| 1ステップ | 125ms |
| 1ビート | 500ms |
| 1小節 | 2秒 |
| 1サイクル | 2秒 |

### パラメータ

| 用語 | 説明 | 範囲 |
|------|------|------|
| gain | ゲイン（音量） | 0.0-2.0（推奨: 0.0-1.0） |
| pan | パン（左右定位） | 0.0（左）-0.5（中央）-1.0（右） |
| velocity | ベロシティ（強さ） | 0.0-1.0（SuperDirt）、0-127（MIDI） |
| note | MIDIノート番号 | 0-127（60=C4） |

### SuperDirt固有用語

| 用語 | 説明 |
|------|------|
| orbit | オービット番号（出力チャンネル） | 0-11 |
| s | サウンド名（例: "bd", "sn"） | 文字列 |
| n | サンプル番号 | 整数 |
| room | リバーブセンド量 | 0.0-1.0 |
| size | リバーブサイズ | 0.0-1.0 |
| delay_send | ディレイセンド量 | 0.0-1.0 |

---

## 技術用語

### アーキテクチャ

| 用語 | 説明 |
|------|------|
| Destination-Agnostic | 送信先に依存しない設計 |
| フラット構造 | 階層を持たないメッセージリスト |
| イミュータブル | 変更不可能（frozen=True） |
| 型安全 | mypyによる静的型チェック |
| O(1)検索 | ステップインデックスによる定数時間検索 |

### パフォーマンス

| 用語 | 説明 |
|------|------|
| ステップインデックス | dict[int, list[int]] によるO(1)検索 |
| 早期リターン | 条件を満たさない場合の早期終了 |
| リスト内包表記 | Pythonの効率的なリスト生成構文 |
| walrus演算子 | := による式内での変数代入 |

### 通信プロトコル

| 用語 | 説明 |
|------|------|
| OSC | Open Sound Control（SuperDirt通信） |
| MIDI | Musical Instrument Digital Interface |
| HTTP | REST API（パターンデータ受信） |
| SSE | Server-Sent Events（リアルタイム状態配信） |

---

## Oiduna vs MARS DSL

### 責任の違い

| 機能 | Oiduna | MARS DSL |
|------|--------|----------|
| DSL構文解析 | ❌ | ✅ |
| プロジェクト管理 | ❌ | ✅ |
| ScheduledMessageBatch生成 | ❌（受信のみ） | ✅ |
| ループ再生 | ✅ | ❌ |
| OSC/MIDI送信 | ✅ | ❌ |
| HTTP API | ✅（再生制御） | ✅（コンパイル） |

### データ交換

**MARS → Oiduna**:
```
DSL → RuntimeSession → ScheduledMessageBatch
                            ↓ HTTP POST
                       Oiduna受信
```

**形式**: ScheduledMessageBatch JSON
```json
{
  "messages": [
    {
      "destination_id": "superdirt",
      "cycle": 0.0,
      "step": 0,
      "params": {"s": "bd", "gain": 0.8}
    }
  ],
  "bpm": 120.0,
  "pattern_length": 4.0
}
```

---

## params（パラメータ）の詳細

### SuperDirt向けparams

**基本パラメータ**:
```python
{
    "s": "bd",          # サウンド名（必須）
    "n": 0,             # サンプル番号
    "gain": 0.8,        # ゲイン
    "pan": 0.5,         # パン
    "speed": 1.0,       # 再生速度
    "orbit": 0          # オービット番号
}
```

**エフェクトパラメータ**:
```python
{
    "room": 0.3,        # リバーブセンド
    "size": 0.8,        # リバーブサイズ
    "delay_send": 0.2,  # ディレイセンド
    "delay_time": 0.5,  # ディレイタイム
    "cutoff": 1000,     # フィルターカットオフ
    "resonance": 0.3    # フィルターレゾナンス
}
```

### MIDI向けparams

**ノートオンパラメータ**:
```python
{
    "note": 60,         # MIDIノート番号（C4）
    "velocity": 100,    # ベロシティ（0-127）
    "duration_ms": 250, # ノート長（ミリ秒）
    "channel": 0        # MIDIチャンネル（0-15）
}
```

**コントロールチェンジパラメータ**:
```python
{
    "cc": 74,           # CCナンバー（フィルターカットオフ）
    "value": 64,        # CC値（0-127）
    "channel": 0        # MIDIチャンネル（0-15）
}
```

### カスタム送信先params

拡張機能で任意のパラメータを定義可能:
```python
{
    "custom_param_1": "value",
    "custom_param_2": 123,
    # ...任意のkey-value
}
```

---

## よくある質問

### Q: 「3層IR」や「CompiledSession」はどこに行ったのか？

**A**: アーキテクチャ統合により、ScheduledMessageBatch形式に統一されました。階層構造（Environment/Track/Sequence）はMARS側でScheduledMessageBatchに変換されてからOidunaに送信されます。

詳細: [MIGRATION_GUIDE_SCHEDULED_MESSAGE_BATCH.md](MIGRATION_GUIDE_SCHEDULED_MESSAGE_BATCH.md)

### Q: params: dict[str, Any] の型安全性は？

**A**: `dict[str, Any]`は送信先に依存しないために採用されています。型安全性はDestinationSender側でのバリデーションで補完されます。

代替案（TypedDict、Pydantic）も検討しましたが、拡張性とパフォーマンスのバランスから現在の設計を選択しています。

詳細: [DATA_MODEL_REFERENCE.md](DATA_MODEL_REFERENCE.md#24-型安全性の限界と実用性のバランス)

### Q: ステップインデックスとは何か？

**A**: ステップ番号をキーとした辞書（dict[int, list[int]]）で、O(1)でメッセージを検索できます。

線形探索（O(N)）では大規模パターンで125msの制約を超えるため、インデックス化が必須です。

```python
# ステップ0のメッセージを取得（O(1)）
message_indices = step_index[0]  # [0, 5, 12]
messages = [all_messages[i] for i in message_indices]
```

### Q: destination_idはどこで定義するのか？

**A**: `destinations.yaml` で定義します。

```yaml
destinations:
  - id: superdirt
    type: osc
    host: 127.0.0.1
    port: 57120
    address: /dirt/play

  - id: volca_bass
    type: midi
    port_name: "Volca Bass"
    default_channel: 0
```

### Q: Mute/Soloはどう動作するのか？

**A**: RuntimeState.filter_messages()がtrack_idに基づいてフィルタリングします。

```python
# Solo設定時: solo指定されたtrackのみ再生
if track_solo:
    return track_id in track_solo

# Mute設定時: mute指定されたtrackを除外
if track_id in track_mute:
    return False
```

paramsに`track_id`が含まれていない場合は常に再生されます。

---

## 用語の使い分け例

### ✅ 良い例

```
「OidunaはScheduledMessageBatch形式でパターンデータを受け取り、
MessageSchedulerでステップ別インデックスを構築します。
DestinationRouterがdestination_idに基づいて送信先を振り分け、
OscDestinationSenderとMidiDestinationSenderが実際の送信を行います。」
```

### ❌ 悪い例

```
「OidunaはCompiledSessionを受け取り、3層IRを処理します。
TrackとEventSequenceからOSCメッセージを生成します。」
```

理由：
- CompiledSession、3層IR、Track、EventSequenceは旧アーキテクチャ
- 現在の実装と一致しない

---

---

## API層の用語（Phase 4-5追加）

### SessionContainer

**定義**: SessionManagerを置き換える軽量コンテナパターン

**構造**:
```python
SessionContainer
├── clients: ClientManager       # Client CRUD
├── tracks: TrackManager         # Track CRUD
├── patterns: PatternManager     # Pattern CRUD
├── environment: EnvironmentManager
└── destinations: DestinationManager
```

**使用例**:
```python
container = SessionContainer()
container.clients.create("alice", "Alice", "mars")
container.tracks.create("kick", "Kick Track", ...)
```

**詳細**: [knowledge/adr/0010-session-container-refactoring.md](knowledge/adr/0010-session-container-refactoring.md)

### oiduna_models / oiduna_auth / oiduna_session

**Phase 4で追加された新規パッケージ**:
- `oiduna_models`: Session/Track/Pattern/Event/Client データモデル
- `oiduna_auth`: UUID Token認証システム
- `oiduna_session`: SessionContainer + 専門マネージャー

**詳細**: [../IMPLEMENTATION_COMPLETE.md](../IMPLEMENTATION_COMPLETE.md)

**Note**: これらはAPI層の実装詳細です。コアループエンジン（ScheduledMessageBatch処理）とは独立しています。

---

## 参照ドキュメント

- [ARCHITECTURE.md](ARCHITECTURE.md) - システム全体のアーキテクチャ
- [DATA_MODEL_REFERENCE.md](DATA_MODEL_REFERENCE.md) - データモデル詳細
- [OIDUNA_CONCEPTS.md](OIDUNA_CONCEPTS.md) - Oidunaのコンセプト
- [archive/MIGRATION_GUIDE_SCHEDULED_MESSAGE_BATCH.md](archive/MIGRATION_GUIDE_SCHEDULED_MESSAGE_BATCH.md) - 移行ガイド (archive)
- [../IMPLEMENTATION_COMPLETE.md](../IMPLEMENTATION_COMPLETE.md) - Phase 1-5完了サマリー
- [knowledge/adr/0010-session-container-refactoring.md](knowledge/adr/0010-session-container-refactoring.md) - SessionContainer ADR

---

**バージョン**: 2.1.0 (SessionContainer追加版)
**作成日**: 2026-02-27
**最終更新**: 2026-02-28 (Phase 5完了)
**メンテナンス**: 用語追加時はこのファイルを更新
