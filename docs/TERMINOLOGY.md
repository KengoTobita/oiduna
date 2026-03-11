# Oiduna用語集

**バージョン**: 3.0.0 (Schedule/Cued統合版)
**作成日**: 2026-02-27
**最終更新**: 2026-03-11

## クイックリファレンス

### 主要概念

| 用語 | 英語 | 説明 |
|------|------|------|
| LoopSchedule | Loop Schedule | 256ステップのループ実行時刻表（不変） |
| ScheduleEntry | Schedule Entry | 時刻表の1エントリ（step + destination + params） |
| LoopScheduler | Loop Scheduler | 時刻表を実行するエンジン |
| CuedChange | Cued Change | 将来のstepで実行する変更予約（DJ的なcue） |
| CuedChangeTimeline | Cued Change Timeline | 予約されたchangeの管理 |
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

#### 2️⃣ SessionChange（CRUD変更通知）

**定義**: Session層のデータ変更を通知する変更通知（辞書型）

**レイヤー**: Session層（oiduna_session）

**データ型**:
```python
{
    "type": str,     # 変更種別（例: "track_created"）
    "data": dict     # 変更固有データ
}
```

**変更種類** (29種):
- Client: `client_connected`, `client_disconnected`
- Track: `track_created`, `track_updated`, `track_deleted`
- Pattern: `pattern_created`, `pattern_updated`, `pattern_archived`, `pattern_moved`
- Environment: `environment_updated`
- Destination: `destination_removed`
- Timeline: `change_scheduled`, `change_cancelled`

**Protocol**: `SessionChangePublisher.publish(change: dict)`

**使用箇所**:
- `BaseManager._emit_change()` - 各Managerから発火
- `InProcessStateProducer.publish()` - SSE配信用キューに蓄積

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

**Note**: v3.1以前は「SessionEvent」と呼ばれていましたが、PatternEventとの混同を防ぐためv3.2で「SessionChange」にリネームされました。

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

**統合配信**: SessionChange と StateProducer の両方を統合配信

**例**:
```
event: pattern_created
data: {"pattern_id": "3e2b", "event_count": 2}

event: position
data: {"step": 0, "beat": 0, "cycle": 0.0}

event: heartbeat
data: {"timestamp": 1234567890.123}
```

**頻度**: 高頻度（SessionChange + StateProducer の統合）

---

#### Event用語の比較表

| 項目 | PatternEvent | SessionChange | SSE Event |
|------|-------------|---------------|-----------|
| **レイヤー** | ドメインモデル | Session層 | HTTP層 |
| **データ型** | PatternEvent class | dict | string |
| **目的** | 音楽的タイミング | CRUD変更通知 | HTTP配信 |
| **頻度** | 多数（パターン内） | 低頻度（操作時） | 高頻度（統合） |
| **送信先** | SessionCompiler | SSE endpoint | ブラウザ |
| **例** | `PatternEvent(step=0, ...)` | `{"type": "track_created"}` | `"event: ...\ndata: ...\n\n"` |

#### データフロー全体図

```
┌─────────────────────────────────────────────────────┐
│ ドメイン層: PatternEvent（音楽イベント）              │
│   Pattern.events: list[PatternEvent]                │
│       ↓ SessionCompiler                             │
│   LoopSchedule (256ステップ実行時刻表)               │
│       ↓ LoopScheduler                               │
│   音楽再生                                           │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Session層: SessionChange（CRUD変更通知）             │
│   BaseManager._emit_change()                        │
│       ↓ SessionChangePublisher.publish()            │
│   InProcessStateProducer._queue ←┐                      │
└──────────────────────────────┼──────────────────────┘
                               │
┌──────────────────────────────┼──────────────────────┐
│ Loop層: StateProducer（再生状態）                    │
│   LoopEngine.send_position() │                      │
│       ↓ StateProducer        │                      │
│   InProcessStateProducer._queue ─┘                      │
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
- **v3.2**: SessionEvent → SessionChange にリネーム（PatternEventとの明確な区別）
- SessionChangePublisher Protocol: SessionChange変更通知の配信インターフェース
- SSE Event は HTTP仕様の用語として明示

---

### Schedule/Cued用語（重要）

Oidunaでは「Schedule」という用語が**2つの異なる意味**で使用されていました（v3.0まで）。
v3.1以降、明確に分離されました。

#### 4️⃣ LoopSchedule（ループ実行時刻表）

**定義**: 256ステップの確定済み実行計画（不変）

**レイヤー**: Scheduler層（oiduna_scheduler）

**データ型**:
```python
LoopSchedule(
    entries: tuple[ScheduleEntry, ...],  # 全エントリ
    bpm: float,                          # テンポ
    pattern_length: float                # パターン長（サイクル）
)
```

**使用箇所**:
- `SessionCompiler.compile()` - Sessionからコンパイル
- `LoopScheduler.load_schedule()` - ループエンジンにロード
- `CuedChange.batch` - Timeline予約の実行内容

**例**:
```python
# Sessionをコンパイル
schedule = compiler.compile(session)
# → LoopSchedule(entries=(...), bpm=120.0)

# Schedulerにロード
scheduler = LoopScheduler()
scheduler.load_schedule(schedule)

# ステップごとに実行
entries = scheduler.get_entries_at_step(64)
```

**意味**: 列車の時刻表のような**確定済みプラン**
- 一度作ったら変わらない（frozen=True）
- 256ステップすべての実行内容が記載
- LoopSchedulerがこれを読んで実行

**頻度**: 低頻度（Session変更時のみコンパイル）

---

#### 5️⃣ ScheduleEntry（時刻表エントリ）

**定義**: LoopScheduleの1エントリ（step + destination + params）

**データ型**:
```python
ScheduleEntry(
    destination_id: str,     # 送信先ID
    cycle: float,            # サイクル位置 (0.0-4.0)
    step: int,               # ステップ番号 (0-255)
    params: dict[str, Any]   # 送信先依存パラメータ
)
```

**使用箇所**:
- `LoopSchedule.entries` - 時刻表の全エントリ
- `LoopScheduler.get_entries_at_step()` - 特定ステップのエントリ取得

**例**:
```python
# キックドラムエントリ
kick = ScheduleEntry(
    destination_id="superdirt",
    cycle=0.0,
    step=0,
    params={"s": "bd", "gain": 0.9}
)
```

**意味**: 時刻表の1行（「step 0でsuperdirtにbdを送信」）

---

#### 6️⃣ CuedChange（キューされた変更）

**定義**: 将来のglobal_stepで実行する変更予約

**レイヤー**: Timeline層（oiduna_timeline）

**データ型**:
```python
CuedChange(
    target_global_step: int,  # 実行予定step（累積カウンタ）
    batch: LoopSchedule,      # 実行内容
    client_id: str,           # 予約したクライアント
    change_id: str,           # 変更ID (UUID)
    description: str,         # 説明（オプション）
    cued_at: float,           # 予約時刻（Unix timestamp）
    sequence_number: int      # 同一step内の順序
)
```

**使用箇所**:
- `CuedChangeTimeline.cue_change()` - 変更を予約
- `CuedChangeTimeline.get_cued_at()` - 特定stepの予約取得
- `TimelineManager.cue_change()` - Session層からの予約

**例**:
```python
# step 1000でパターン変更を予約
change = CuedChange(
    target_global_step=1000,
    batch=new_pattern_schedule,
    client_id="alice",
    description="Drop the bass"
)

timeline.cue_change(change, current_step=500)
# → step 1000で自動適用
```

**意味**: DJ的な「次に出すトラック」
- まだ実行されていない（未来予約）
- global_stepが来たら自動適用
- 複数の変更を同一stepに予約可能（マージされる）

**頻度**: 中頻度（ライブコーディング中の変更予約）

---

#### 7️⃣ CuedChangeTimeline（予約管理）

**定義**: 予約されたCuedChangeのタイムライン管理

**データ型**: class

**主要メソッド**:
```python
timeline = CuedChangeTimeline()

# 予約追加
success, msg = timeline.cue_change(change, current_step)

# 特定stepの予約取得
changes = timeline.get_cued_at(global_step)

# 過去予約のクリーンアップ
timeline.cleanup_past(current_step)
```

**制約**:
- MAX_CHANGES_PER_STEP: 同一stepに最大10個の変更
- MAX_MESSAGES_PER_BATCH: 1つのLoopScheduleに最大5000エントリ
- CLEANUP_INTERVAL: 1000ステップごとに過去予約を自動削除

**意味**: 「いつ何を実行するか」の予定表管理

---

#### Schedule/Cued用語の比較表

| 項目 | LoopSchedule | CuedChange |
|------|-------------|-----------|
| **意味** | 確定済み実行時刻表 | 未来の変更予約 |
| **状態** | 不変（frozen=True） | 可変（タイムラインから削除可能） |
| **時制** | 過去完了（配置済み） | 未来（予約中） |
| **類推** | 列車の時刻表 | DJのキューリスト |
| **実行** | LoopSchedulerが毎step読む | global_stepが来たら適用 |
| **頻度** | 低頻度（Session変更時） | 中頻度（パターン変更時） |
| **データ** | 256step全体 | 1つの変更内容 |

#### 命名の歴史（Schedule/Cued）

- **v3.0以前**: ScheduledMessageBatch / ScheduledMessage / MessageScheduler
  - 問題: "Scheduled"が「確定済み」と「予約中」の2つの意味で混在
- **v3.1**: LoopSchedule / ScheduleEntry / LoopScheduler（確定済み実行時刻表）
  - ScheduledChange → CuedChange（未来予約）
  - 明確に分離: Schedule = 確定、Cued = 予約

---

### ID形式の体系

| ID種別 | 形式 | 例 | 用途 | バリデーション |
|--------|------|-----|------|--------------|
| Session ID | 8桁hexadecimal | `a1b2c3d4` | セッション識別子 | 自動生成 |
| Client ID | 4桁hexadecimal | `0a1f` | クライアント識別子 | 自動生成またはユーザー定義 |
| Track ID | 4桁hexadecimal | `3e2b` | トラック識別子 | Track model で検証 |
| Pattern ID | 4桁hexadecimal | `7f8a` | パターン識別子 | Pattern model で検証 |
| Destination ID | 英数字+ハイフン/アンダースコア | `superdirt`, `volca_bass` | 送信先識別子 | destinations.yamlで定義 |

**ID生成**:
- Session/Client/Track/Pattern IDは`packages/oiduna_models/id_generator.py`で生成
- Destination IDはdestinations.yamlで手動定義（英数字+ハイフン/アンダースコア許可）

**コード参照**:
- `packages/oiduna_models/id_generator.py:7` - generate_session_id()
- `packages/oiduna_models/id_generator.py:12` - generate_client_id()
- `packages/oiduna_models/track.py:15` - track_id validation
- `packages/oiduna_models/pattern.py:14` - pattern_id validation

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

### レイヤーアーキテクチャ（Layer 1-4）

Oidunaは4層のデータ変換アーキテクチャで構成されています:

| Layer | 名称 | 責務 | データ形式 | パッケージ |
|-------|------|------|-----------|-----------|
| **Layer 1** | 階層モデル層 | ユーザー向けデータ構造 | Session → Track → Pattern → PatternEvent | oiduna_models |
| **Layer 2** | メッセージフォーマット層 | プロトコル非依存の表現 | ScheduledMessageBatch → ScheduledMessage | oiduna_scheduler/scheduler_models.py |
| **Layer 3** | スケジューリング・ルーティング層 | パフォーマンス最適化 | MessageScheduler（O(1)検索）、DestinationRouter | oiduna_scheduler/scheduler.py, router.py |
| **Layer 4** | プロトコル実装層 | 送信先固有の処理 | OscDestinationSender、MidiDestinationSender | oiduna_scheduler/senders.py |

**データフロー**:
```
Layer 1: Session/Track/Pattern/PatternEvent (ユーザーフレンドリー)
           ↓ SessionCompiler
Layer 2: ScheduledMessageBatch (Destination-Agnostic)
           ↓ MessageScheduler.load_messages()
Layer 3: Step-indexed dict[int, list[int]] (O(1)検索)
           ↓ DestinationRouter.send_messages()
Layer 4: OSC/MIDI送信 (プロトコル固有)
```

**依存方向**:
```
API → Session → Models
API → Loop → Scheduler → Models
      └─────────────────→
```

**Single Responsibility原則**:
- Layer 1: データバリデーションのみ（Pydantic）
- Layer 2: メッセージ形式の標準化
- Layer 3: 高速検索とルーティング
- Layer 4: プロトコル変換と送信

**コード参照**:
- Layer 1: `packages/oiduna_models/`
- Layer 2: `packages/oiduna_scheduler/scheduler_models.py`
- Layer 3: `packages/oiduna_scheduler/scheduler.py`, `router.py`
- Layer 4: `packages/oiduna_scheduler/senders.py`

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
| バー（小節） | 4ビート単位 | 4バー = 1ループ |
| サイクル | TidalCycles由来の単位 | 4.0サイクル = 1ループ |
| BPM | Beats Per Minute | 120 BPM = 2ビート/秒 |

**正確なタイミング仕様（固定）**:
```
1 step    = 1/16 note
4 steps   = 1 beat (1/4 note)
16 steps  = 1 bar (4 beats)
64 steps  = 4 bars
256 steps = 16 beats = 4 bars = 1 loop = 4.0 cycles (固定長)
```

**重要な設計制約**:
- **256-step固定ループ**: Oidunaのコアアーキテクチャ（変更不可）
- **step vs cycle**: PatternEventは両方を持つ
  - `step: int` (0-255) - 量子化されたステップ番号（インデックス用）
  - `cycle: float` (0.0-4.0) - 精密なタイミング（TidalCycles互換）
- **position_update_interval**:
  - `"beat"`: 4ステップごと（1ビート）に位置更新通知
  - `"bar"`: 16ステップごと（1バー）に位置更新通知

**時間換算表（120 BPM）**:
| 単位 | ステップ数 | 時間 |
|------|-----------|------|
| 1ステップ | 1 | 125ms |
| 1ビート | 4 | 500ms |
| 1バー（小節） | 16 | 2秒 |
| 1ループ | 256 | 32秒 |
| 1サイクル | 64 | 8秒 |

**コード参照**:
- `packages/oiduna_models/events.py:10-11` - PatternEvent (step/cycle fields)
- `packages/oiduna_loop/engine/loop_engine.py:23` - LOOP_STEPS = 256 定数
- `packages/oiduna_models/environment.py:14` - position_update_interval

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

### IPC通信（Producer/Consumerパターン）

Oidunaは**API層とLoop層の間**で双方向のIPC通信を行います。

#### Commandフロー（API → Loop）

| 役割 | クラス | 実装 | 用途 |
|------|--------|------|------|
| Producer | CommandProducer | ZeroMQ PUB or In-Process Queue | APIがコマンドを送信 |
| Consumer | CommandConsumer | ZeroMQ SUB or In-Process Queue | Loopがコマンドを受信 |

**コマンド種類**:
- `Play`, `Stop`, `Pause` - 再生制御
- `Compile` - パターンコンパイル
- `Mute`, `Solo` - トラックミュート/ソロ
- `SetBpm` - BPM変更

#### Stateフロー（Loop → API）

| 役割 | クラス | 実装 | 用途 |
|------|--------|------|------|
| Producer | StateProducer | InProcessStateProducer or ZeroMQ | Loopが状態を送信 |
| Consumer | StateConsumer | In-Process Queue | APIが状態を受信 |

**状態種類**:
- Position - ステップ/ビート/バー/サイクル位置
- PlaybackState - PLAYING/PAUSED/STOPPED
- Errors - エラー通知
- TrackInfo - トラック状態

**IPC実装の種類**:
- **InProcessStateProducer**: キューベース（単一プロセス用）
- **ZeroMQ**: プロセス間通信（マルチプロセス用）

**プロトコル定義**:
```python
# packages/oiduna_loop/ipc/protocols.py
class CommandProducer(Protocol):
    def send_command(self, command: Command) -> None: ...

class CommandConsumer(Protocol):
    def receive_command(self) -> Command | None: ...

class StateProducer(Protocol):
    def publish(self, state: dict) -> None: ...

class StateConsumer(Protocol):
    def consume(self) -> list[dict]: ...
```

**データフロー全体図**:
```
┌─────────────────────────────────────────────────────┐
│ API層（FastAPI）                                     │
│   CommandProducer.send_command() ────┐              │
│   StateConsumer.consume() ←──────────┼──┐          │
└──────────────────────────────────────┼──┼───────────┘
                                       │  │
                          Command      │  │ State
                                       │  │
┌──────────────────────────────────────┼──┼───────────┐
│ Loop層（LoopEngine）                  │  │           │
│   CommandConsumer.receive_command() ←┘  │           │
│   StateProducer.publish() ──────────────┘          │
└─────────────────────────────────────────────────────┘
```

**コード参照**:
- `packages/oiduna_loop/ipc/protocols.py:10-40` - Protocol定義
- `packages/oiduna_loop/ipc/command_receiver.py` - CommandConsumer実装
- `packages/oiduna_loop/ipc/state_publisher.py` - StateProducer実装

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

### Manager Pattern（専門マネージャー）

SessionContainerは**6つの専門Manager**を集約し、各Managerが単一責任を持ちます。

| Manager | 責務 | 主要メソッド | データモデル |
|---------|------|-------------|-------------|
| **ClientManager** | Client CRUD | create(), get(), delete() | ClientInfo |
| **TrackManager** | Track CRUD | create(), get(), update(), delete() | Track |
| **PatternManager** | Pattern CRUD | create(), get(), update(), archive(), move() | Pattern |
| **EnvironmentManager** | グローバル設定 | get(), update() | Environment |
| **DestinationManager** | 送信先管理 | get_all(), remove() | OscDestinationConfig, MidiDestinationConfig |
| **TimelineManager** | スケジュール変更 | schedule_change(), cancel_change() | TimelineChange |

#### BaseManager プロトコル

全Managerは`BaseManager`プロトコルを実装:
```python
class BaseManager(Protocol):
    def _emit_change(self, change_type: str, data: dict) -> None:
        """SessionChangePublisherに変更通知を発行"""
```

#### SessionChangePublisher プロトコル

ManagerがCRUD操作を通知するためのプロトコル:
```python
class SessionChangePublisher(Protocol):
    def publish(self, change: dict) -> None:
        """SessionChange変更通知を配信"""
```

**変更通知発行フロー**:
```
Manager.create() / update() / delete()
  ↓ _emit_change()
SessionChangePublisher.publish()
  ↓
InProcessStateProducer._queue
  ↓
SSE endpoint (/api/stream/events)
  ↓
クライアント（ブラウザ）
```

**コード参照**:
- `packages/oiduna_session/container.py:10-30` - SessionContainer
- `packages/oiduna_session/managers/base.py:8-15` - BaseManager protocol
- `packages/oiduna_session/managers/client_manager.py` - ClientManager
- `packages/oiduna_session/managers/track_manager.py` - TrackManager
- `packages/oiduna_session/managers/pattern_manager.py` - PatternManager

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

**バージョン**: 2.2.0 (アーキテクチャ概念拡充版)
**作成日**: 2026-02-27
**最終更新**: 2026-03-11 (ID体系、Layer 1-4、IPC、Manager pattern追加)
**メンテナンス**: 用語追加時はこのファイルを更新
