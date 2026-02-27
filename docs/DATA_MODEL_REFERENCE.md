# データモデルリファレンス

**バージョン**: 3.0.0 (ScheduledMessageBatch統合版)
**更新日**: 2026-02-27

> **Single Source of Truth**: このドキュメントはデータモデルの概念とアーキテクチャを説明します。詳細な型定義、フィールド名、デフォルト値などは実際のコードを参照してください。コードが真実の源です。

## 目次

1. [ScheduledMessageBatchアーキテクチャ](#1-scheduledmessagebatchアーキテクチャ)
2. [なぜこの設計なのか](#2-なぜこの設計なのか)
3. [データモデルの場所](#3-データモデルの場所)
4. [データフロー](#4-データフロー)
5. [拡張機能との連携](#5-拡張機能との連携)

---

## 1. ScheduledMessageBatchアーキテクチャ

Oidunaは**ScheduledMessageBatch**形式でパターンデータを受け取り、リアルタイムで再生します。これはフラットなメッセージリスト構造で、送信先に依存しない設計です。

```
┌────────────────────────────────────────────────────────────┐
│ ScheduledMessageBatch                                       │
│                                                            │
│  messages: tuple[ScheduledMessage, ...]                    │
│    ├─ destination_id: str  (送信先ID)                      │
│    ├─ cycle: float         (サイクル位置: 0.0-4.0)        │
│    ├─ step: int            (ステップ番号: 0-255)          │
│    └─ params: dict[str, Any] (送信先依存パラメータ)        │
│                                                            │
│  bpm: float                (テンポ)                        │
│  pattern_length: float     (パターン長: サイクル単位)      │
└────────────────────────────────────────────────────────────┘
```

### 1.1 ScheduledMessage（スケジュール済みメッセージ）

**定義**: `packages/oiduna_scheduler/scheduler_models.py:14`

**責任**: 1つの送信イベントを表現

**主要なフィールド**:
- **destination_id**: 送信先ID（例: "superdirt", "volca_bass"）
  - destinations.yamlで定義された送信先のID
  - DestinationRouterが自動的に振り分け

- **cycle**: サイクル位置（0.0から始まる浮動小数点）
  - TidalCyclesのcycle概念に対応
  - 4.0サイクル = 4小節（16ビート = 256ステップ）

- **step**: ステップ番号（0-255、256ステップループ）
  - 1/16音符単位の粒度
  - MessageSchedulerのインデックスキーとして使用

- **params**: 送信先依存のパラメータ（dict[str, Any]）
  - SuperDirtの場合: s, gain, pan, orbit, room等
  - MIDIの場合: note, velocity, duration_ms, channel等
  - カスタム送信先の場合: 任意のパラメータ

**型定義**:
```python
@dataclass(frozen=True, slots=True)
class ScheduledMessage:
    destination_id: str
    cycle: float
    step: int
    params: dict[str, Any]
```

**paramsの例（SuperDirt向け）**:
```python
{
    "s": "bd",          # サウンド名（必須）
    "gain": 0.8,        # ゲイン
    "pan": 0.5,         # パン（0.0=左, 0.5=中央, 1.0=右）
    "room": 0.3,        # リバーブセンド量
    "size": 0.8,        # リバーブサイズ
    "orbit": 0,         # オービット番号（0-11）
    "cps": 0.5          # Cycles Per Second（BPM由来）
}
```

**paramsの例（MIDI向け）**:
```python
{
    "note": 60,         # MIDIノート番号（C4）
    "velocity": 100,    # ベロシティ（0-127）
    "duration_ms": 250, # ノート長（ミリ秒）
    "channel": 0        # MIDIチャンネル（0-15）
}
```

### 1.2 ScheduledMessageBatch（スケジュール済みメッセージバッチ）

**定義**: `packages/oiduna_scheduler/scheduler_models.py:79`

**責任**: パターン全体を表現

**型定義**:
```python
@dataclass(frozen=True)
class ScheduledMessageBatch:
    messages: tuple[ScheduledMessage, ...]
    bpm: float = 120.0
    pattern_length: float = 4.0  # サイクル単位
```

**主要な特性**:
- **イミュータブル**: `frozen=True`により変更不可
- **メモリ効率**: `tuple`により固定長配列として最適化
- **type-safe**: mypyによる型チェック

### 1.3 MessageScheduler（メッセージスケジューラ）

**定義**: `packages/oiduna_scheduler/scheduler.py:17`

**責任**: ScheduledMessageBatchを高速検索可能な形式に変換

**主要な機能**:
```python
class MessageScheduler:
    def load_messages(self, batch: ScheduledMessageBatch) -> None:
        # ステップ別インデックス構築
        self._step_index: dict[int, list[int]] = {}

        for i, msg in enumerate(batch.messages):
            step = msg.step
            if step not in self._step_index:
                self._step_index[step] = []
            self._step_index[step].append(i)

    def get_messages_for_step(self, step: int) -> list[ScheduledMessage]:
        # O(1)検索
        indices = self._step_index.get(step, [])
        return [self._messages[i] for i in indices]
```

**パフォーマンス特性**:
- **インデックス構築**: O(N)（一度だけ）
- **ステップ検索**: O(1)（毎ステップ実行、120 BPMで125msごと）

**なぜインデックス化するのか**:
リアルタイム再生時（120 BPMで125msごと）に高速検索が必要なため。線形探索（O(N)）では大規模パターンで遅延が発生します。

### 1.4 DestinationRouter（送信先ルーター）

**定義**: `packages/oiduna_scheduler/router.py:17`

**責任**: メッセージを送信先別に振り分けて送信

**処理フロー**:
```python
class DestinationRouter:
    def send_messages(self, messages: list[ScheduledMessage]) -> None:
        # 送信先別にグループ化
        by_destination: dict[str, list[ScheduledMessage]] = {}
        for msg in messages:
            dest_id = msg.destination_id
            if dest_id not in by_destination:
                by_destination[dest_id] = []
            by_destination[dest_id].append(msg)

        # 各送信先に送信
        for dest_id, msgs in by_destination.items():
            sender = self._senders.get(dest_id)
            if sender:
                for msg in msgs:
                    sender.send_message(msg.params)
```

**送信先の種類**:
- **OscDestinationSender**: OSCプロトコル（SuperDirt等）
- **MidiDestinationSender**: MIDIプロトコル（MIDIデバイス）
- **カスタムSender**: 拡張機能で追加可能

**設定ファイル**: `destinations.yaml`
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

---

## 2. なぜこの設計なのか

### 2.1 Destination-Agnostic（送信先非依存）

**問題**: 以前のアーキテクチャはSuperDirt専用だった

**解決策**: params: dict[str, Any]により任意の送信先に対応
- SuperDirt: `{"s": "bd", "orbit": 0}`
- MIDI: `{"note": 60, "channel": 0}`
- カスタム: 任意のパラメータ

**利点**:
- 新しい送信先を追加しやすい
- 送信先固有の最適化が可能
- テストしやすい（モック送信先を簡単に作成）

### 2.2 フラット構造

**問題**: 階層構造（Environment/Track/Sequence）は複雑で、変換コストが高かった

**解決策**: フラットなメッセージリストに統一
- 階層を持たない単純な配列
- ステップとパラメータのみ

**利点**:
- デバッグしやすい
- 変換処理が不要
- メモリ効率が良い

### 2.3 イミュータブル設計

すべてのデータモデルは`frozen=True`でイミュータブルです。

**理由**:
- **予測可能性**: データの状態が変わらないため、デバッグが容易
- **並行性**: マルチスレッド環境で安全
- **キャッシュ**: ハッシュ可能なため、効率的なキャッシングが可能
- **メモリ**: 不変オブジェクトはPythonインタプリタによって最適化される

### 2.4 型安全性の限界と実用性のバランス

**型安全性が低い部分**: `params: dict[str, Any]`

**なぜ型を緩くするのか**:
- 送信先ごとに異なるパラメータセットが必要
- 拡張機能で新しいパラメータを追加可能にする
- 実行時バリデーションで補完（DestinationSender側で型チェック）

**代替案として検討したアプローチ**:
1. **TypedDict**: 各送信先用にSuperDirtParams, MidiParams等を定義
   - 欠点: 拡張性が低い、Union型が複雑になる

2. **Pydantic BaseModel**: 実行時バリデーション
   - 欠点: パフォーマンスオーバーヘッド（ループ内で125msごと）

3. **Generic型パラメータ**: ScheduledMessage[T]
   - 欠点: 複雑さが増す、実用的でない

**現在の選択**: `dict[str, Any]` + DestinationSender側でのバリデーション
- シンプル
- 拡張可能
- パフォーマンスが良い

### 2.5 O(1)検索の重要性

**問題**: 線形探索では大規模パターンで遅延が発生

**解決策**: MessageSchedulerによるステップ別インデックス
```python
# 線形探索: O(N) - 遅い
messages_at_step = [msg for msg in all_messages if msg.step == current_step]

# インデックス検索: O(1) - 高速
message_indices = step_index[current_step]
messages_at_step = [all_messages[i] for i in message_indices]
```

**実測パフォーマンス**（256ステップ、1000メッセージ）:
- 線形探索: ~10ms per step → 不可（125msの制約を超える）
- インデックス検索: ~0.1ms per step → OK

---

## 3. データモデルの場所

### 3.1 Oiduna Scheduler（パターンデータ）

**場所**: `packages/oiduna_scheduler/`

| ファイル | 主要なモデル | 説明 |
|---------|------------|------|
| `scheduler_models.py` | ScheduledMessageBatch, ScheduledMessage | パターンデータの定義 |
| `scheduler.py` | MessageScheduler | インデックス化とメッセージ取得 |
| `router.py` | DestinationRouter | 送信先別振り分け |
| `senders.py` | OscDestinationSender, MidiDestinationSender | プロトコル別送信実装 |

**依存関係**:
```
scheduler_models.py  (データ定義)
        ↓
scheduler.py  (インデックス化)
        ↓
router.py  (振り分け)
        ↓
senders.py  (送信)
```

### 3.2 Oiduna Loop State（状態管理）

**場所**: `packages/oiduna_loop/state/`

| ファイル | 主要なモデル | 説明 |
|---------|------------|------|
| `runtime_state.py` | RuntimeState | 再生状態、BPM、Mute/Solo管理 |
| `playback_state.py` | PlaybackState (enum) | PLAYING, PAUSED, STOPPED |
| `position.py` | Position | ループ内の現在位置（step, beat, bar, cycle） |

**RuntimeStateの責任**:
- BPM管理（set_bpm()）
- Mute/Solo管理（set_track_mute(), set_track_solo()）
- メッセージフィルタリング（filter_messages()）
- 再生状態管理（playing, paused, stopped）

### 3.3 Oiduna API（HTTP API）

**場所**: `packages/oiduna_api/`

| ファイル | 主要なモデル | 説明 |
|---------|------------|------|
| `models/session.py` | SessionRequest (Pydantic) | POST /playback/sessionのリクエスト |
| `routes/playback.py` | - | 再生制御エンドポイント |
| `routes/tracks.py` | - | Mute/Soloエンドポイント |

**SessionRequest**（Pydantic）:
```python
class SessionRequest(BaseModel):
    messages: list[dict[str, Any]]  # ScheduledMessageのJSON表現
    bpm: float = 120.0
    pattern_length: float = 4.0
```

### 3.4 MARS DSL Runtime（DSLコンパイラ側）

**場所**: `Modular_Audio_Real-time_Scripting/mars_dsl/`

**役割**: DSL構文をScheduledMessageBatchに変換するための中間表現

**主要なモデル**: RuntimeSession, RuntimeEnvironment, RuntimeTrack, RuntimeSequence

**変換処理**: MARS側でScheduledMessageBatchを直接生成
```
DSL → RuntimeSession → ScheduledMessageBatch
```

### 3.5 Extension System（拡張機能）

**場所**: `packages/oiduna_api/extensions/`

| ファイル | 主要なモデル | 説明 |
|---------|------------|------|
| `pipeline.py` | ExtensionPipeline | 拡張機能のチェーン実行 |
| `base.py` | Extension (Protocol) | 拡張機能の基底プロトコル |

**拡張機能の役割**:
- ScheduledMessageBatchの変換
- パラメータの追加・変更
- メッセージのフィルタリング

---

## 4. データフロー

### 4.1 全体フロー

```
┌─────────────────────────────────────────────────────────────┐
│ 1. ユーザー                                                  │
│    ↓ MARS DSLコード                                         │
├─────────────────────────────────────────────────────────────┤
│ 2. MARS DSL Compiler                                        │
│    ├─ Larkパーサー (DSL → AST)                               │
│    ├─ RuntimeSession生成                                     │
│    └─ ScheduledMessageBatch生成                             │
│       ↓ HTTP POST /playback/session (JSON)                  │
├─────────────────────────────────────────────────────────────┤
│ 3. Oiduna API                                               │
│    ├─ SessionRequest (Pydantic) デシリアライズ               │
│    └─ ExtensionPipeline.apply()                             │
│       ↓ ScheduledMessageBatch                               │
├─────────────────────────────────────────────────────────────┤
│ 4. Oiduna Loop Engine                                       │
│    ├─ MessageScheduler.load_messages()                      │
│    │   └─ ステップ別インデックス構築                          │
│    └─ ループ再生（256ステップ）                              │
│       ├─ MessageScheduler.get_messages_for_step()           │
│       ├─ RuntimeState.filter_messages() (Mute/Solo)         │
│       └─ DestinationRouter.send_messages()                  │
│          ├─→ OscDestinationSender → SuperCollider           │
│          └─→ MidiDestinationSender → MIDIデバイス           │
├─────────────────────────────────────────────────────────────┤
│ 5. サウンド再生                                              │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 コンパイル＆適用フロー（詳細）

**ステップ1: DSLコンパイル（MARS側）**
```python
# mars_dsl/compiler.py
dsl_code = "Track(\"bd\"): Sound: s = bd\nbd = x8888~"
runtime_session = compiler.compile_v5(dsl_code)

# ScheduledMessageBatch生成
batch = convert_to_scheduled_messages(runtime_session)
# batch.messages = [
#     ScheduledMessage(destination_id="superdirt", step=0, params={"s": "bd", ...}),
#     ScheduledMessage(destination_id="superdirt", step=16, params={"s": "bd", ...}),
#     ...
# ]
```

**ステップ2: HTTP送信（MARS → Oiduna）**
```python
# mars_api/oiduna_client.py
response = requests.post(
    "http://localhost:8000/playback/session",
    json={
        "messages": [msg.to_dict() for msg in batch.messages],
        "bpm": batch.bpm,
        "pattern_length": batch.pattern_length
    }
)
```

**ステップ3: API受信（Oiduna側）**
```python
# oiduna_api/routes/playback.py
@router.post("/playback/session")
async def load_session(request: SessionRequest):
    # Pydanticバリデーション
    batch = ScheduledMessageBatch(
        messages=tuple(ScheduledMessage(**m) for m in request.messages),
        bpm=request.bpm,
        pattern_length=request.pattern_length
    )

    # 拡張機能適用
    batch = extension_pipeline.apply(batch)

    # MessageSchedulerに読み込み
    message_scheduler.load_messages(batch)

    return {"status": "ok"}
```

**ステップ4: ループ再生（Oiduna Loop Engine）**
```python
# oiduna_loop/engine/loop_engine.py
async def _step_loop(self):
    while self.state.playing:
        current_step = self.state.position.step

        # ステップのメッセージを取得（O(1)）
        messages = self.message_scheduler.get_messages_for_step(current_step)

        # Mute/Soloフィルタリング
        messages = self.state.filter_messages(messages)

        # 送信先別に振り分けて送信
        self.destination_router.send_messages(messages)

        # 次のステップへ
        await asyncio.sleep(step_duration)  # 120 BPMで125ms
        self.state.position.advance_step()
```

### 4.3 Mute/Soloフィルタリング

**RuntimeState.filter_messages()**:
```python
# oiduna_loop/state/runtime_state.py
def filter_messages(self, messages: list[ScheduledMessage]) -> list[ScheduledMessage]:
    # 早期リターン: Mute/Soloが設定されていない場合
    if not self._track_mute and not self._track_solo:
        return messages  # コピーなし

    # フィルタリング
    return [
        msg for msg in messages
        if (track_id := msg.params.get("track_id")) is None
        or self.is_track_active(track_id)
    ]

def is_track_active(self, track_id: str) -> bool:
    # Soloが設定されている場合
    if self._track_solo:
        return track_id in self._track_solo

    # Muteが設定されている場合
    if track_id in self._track_mute:
        return False

    return True
```

---

## 5. 拡張機能との連携

### 5.1 ExtensionPipeline

**定義**: `packages/oiduna_api/extensions/pipeline.py`

**役割**: ScheduledMessageBatchを変換する拡張機能のチェーン

**使用例**:
```python
# oiduna_api/main.py
extension_pipeline = ExtensionPipeline()

# 拡張機能の登録
extension_pipeline.register(MyCustomExtension())

# 適用
@app.post("/playback/session")
async def load_session(request: SessionRequest):
    batch = create_batch_from_request(request)

    # 拡張機能適用
    batch = extension_pipeline.apply(batch)

    # ループエンジンに読み込み
    message_scheduler.load_messages(batch)
```

### 5.2 拡張機能の実装例

**パラメータ追加拡張**:
```python
# oiduna-extension-superdirt/orbit_mapper.py
class OrbitMapperExtension:
    """MixerLine情報からorbitパラメータを追加"""

    def apply(self, batch: ScheduledMessageBatch) -> ScheduledMessageBatch:
        new_messages = []

        for msg in batch.messages:
            # track_idからorbitを決定
            track_id = msg.params.get("track_id")
            orbit = self.get_orbit_for_track(track_id)

            # paramsにorbitを追加
            new_params = {**msg.params, "orbit": orbit}
            new_msg = ScheduledMessage(
                destination_id=msg.destination_id,
                cycle=msg.cycle,
                step=msg.step,
                params=new_params
            )
            new_messages.append(new_msg)

        return ScheduledMessageBatch(
            messages=tuple(new_messages),
            bpm=batch.bpm,
            pattern_length=batch.pattern_length
        )
```

### 5.3 拡張機能の登録

**設定ファイル**: `oiduna_extensions.yaml`
```yaml
extensions:
  - name: orbit_mapper
    enabled: true
    module: oiduna_extension_superdirt.orbit_mapper
    class: OrbitMapperExtension
    config:
      default_orbit: 0
```

---

## 詳細情報の参照方法

### コードを読む

1. **Pythonファイルを直接読む**: コードが最も正確で最新の情報源です
2. **型ヒントを確認**: 各フィールドの型がドキュメントとして機能します
3. **docstringを読む**: クラスやフィールドのdocstringに説明があります
4. **テストコードを参照**: `tests/`ディレクトリのテストコードが使用例を示しています

### 推奨ツール

- **IDEのジャンプ機能**: VSCodeやPyCharmで定義にジャンプ
- **mypy**: 型チェックで整合性を確認
  ```bash
  uv run mypy packages/oiduna_scheduler/
  ```
- **pytest**: テストコードで実際の使用方法を確認
  ```bash
  uv run pytest packages/oiduna_loop/tests/ -v
  ```

---

## 関連ドキュメント

- [ARCHITECTURE.md](ARCHITECTURE.md) - システム全体のアーキテクチャ
- [MIGRATION_GUIDE_SCHEDULED_MESSAGE_BATCH.md](MIGRATION_GUIDE_SCHEDULED_MESSAGE_BATCH.md) - アーキテクチャ統合ガイド
- [ARCHITECTURE_UNIFICATION_COMPLETE.md](ARCHITECTURE_UNIFICATION_COMPLETE.md) - 統合完了記録
- [EXTENSION_DEVELOPMENT_GUIDE.md](EXTENSION_DEVELOPMENT_GUIDE.md) - 拡張機能開発ガイド

---

## コードリファレンス

すべての詳細情報はコードを参照してください：

**Oiduna Scheduler**:
- `packages/oiduna_scheduler/scheduler_models.py` - ScheduledMessageBatch定義
- `packages/oiduna_scheduler/scheduler.py` - MessageScheduler実装
- `packages/oiduna_scheduler/router.py` - DestinationRouter実装
- `packages/oiduna_scheduler/senders.py` - Sender実装

**Oiduna Loop**:
- `packages/oiduna_loop/state/runtime_state.py` - RuntimeState実装
- `packages/oiduna_loop/engine/loop_engine.py` - ループエンジン実装

**Oiduna API**:
- `packages/oiduna_api/models/session.py` - SessionRequest定義
- `packages/oiduna_api/routes/playback.py` - 再生制御エンドポイント
- `packages/oiduna_api/extensions/pipeline.py` - ExtensionPipeline実装

---

**バージョン**: 3.0.0 (ScheduledMessageBatch統合版)
**更新日**: 2026-02-27
**作成者**: Claude Code
**ドキュメント方針**: 概念とアーキテクチャのみ記載、詳細はコードを参照
