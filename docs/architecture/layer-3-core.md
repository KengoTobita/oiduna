# Layer 3: コア層 (Execution Engine)

**パッケージ**: `oiduna_loop`, `oiduna_core`

**最終更新**: 2026-03-01

---

## 概要

コア層は、リアルタイムループ再生エンジンと通信プロトコル定義を担当します。256ステップのクロックを生成し、メッセージをOSC/MIDIで送信します。

### 責任

- ✅ リアルタイムループ再生（256ステップ）
- ✅ 高精度タイミング制御
- ✅ OSC/MIDI送信
- ✅ デスティネーションルーティング
- ✅ 通信プロトコル定義
- ❌ メッセージのスケジューリング（Layer 4に任せる）
- ❌ ビジネスロジック（Layer 2に任せる）

### 依存関係

```
oiduna_loop → oiduna_core
oiduna_core → なし（完全に独立）
```

**設計原則**: コア層は上位層（API、session）に依存しない

---

## oiduna_loop: ループエンジン

### ディレクトリ構造

```
oiduna_loop/
├── __init__.py
├── factory.py           # LoopEngine生成
├── engine.py            # LoopEngine本体
├── clock.py             # ClockGenerator
├── senders/
│   ├── osc_sender.py    # OSCSender
│   └── midi_sender.py   # MIDISender
├── router.py            # DestinationRouter
└── state.py             # RuntimeState
```

---

### LoopEngine: メインエンジン

リアルタイムでメッセージを送信するコアエンジン。

```python
class LoopEngine:
    def __init__(
        self,
        destinations: dict[str, DestinationConfig],
        clock_generator: ClockGenerator,
        destination_router: DestinationRouter
    ):
        self.destinations = destinations
        self.clock = clock_generator
        self.router = destination_router
        self.scheduler: Optional[MessageScheduler] = None
        self.state = RuntimeState()

    async def start(self) -> None:
        """ループ開始"""
        self.state.playback_state = PlaybackState.PLAYING
        await self.clock.start(self._on_step)

    async def stop(self) -> None:
        """ループ停止"""
        self.state.playback_state = PlaybackState.STOPPED
        await self.clock.stop()

    async def sync(self, scheduler: MessageScheduler) -> None:
        """新しいスケジューラーと同期"""
        self.scheduler = scheduler
        self.state.bpm = scheduler.batch.bpm
        self.clock.set_bpm(scheduler.batch.bpm)

    async def _on_step(self, step: int) -> None:
        """各ステップで呼ばれるコールバック"""
        if not self.scheduler:
            return

        # Layer 4からメッセージ取得（O(1)）
        messages = self.scheduler.get_at_step(step)

        # デスティネーションルーターで振り分け
        for msg in messages:
            await self.router.route(msg, self.destinations)

        self.state.current_step = step
```

**使用例**:
```python
# エンジン作成
engine = LoopEngineFactory.create_production(destinations)

# 開始
await engine.start()

# スケジューラー同期
scheduler = MessageScheduler(batch)
await engine.sync(scheduler)

# 停止
await engine.stop()
```

---

### ClockGenerator: 256ステップクロック

高精度タイミングでステップを刻む。

```python
class ClockGenerator:
    LOOP_STEPS = 256  # 固定

    def __init__(self, bpm: float = 120.0):
        self.bpm = bpm
        self.step = 0
        self._running = False
        self._callback: Optional[Callable] = None

    async def start(self, callback: Callable[[int], Awaitable[None]]) -> None:
        """ループ開始"""
        self._callback = callback
        self._running = True
        await self._loop()

    async def _loop(self) -> None:
        """メインループ"""
        step_duration = self._calculate_step_duration()
        start_time = asyncio.get_event_loop().time()

        while self._running:
            # コールバック実行
            if self._callback:
                await self._callback(self.step)

            # 次のステップへ
            self.step = (self.step + 1) % self.LOOP_STEPS

            # ドリフト補正
            expected_time = start_time + (self.step * step_duration)
            actual_time = asyncio.get_event_loop().time()
            sleep_time = expected_time - actual_time

            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

    def _calculate_step_duration(self) -> float:
        """1ステップの時間（秒）"""
        # 1分 = 60秒 = bpm拍 = bpm * 4四分音符
        # 256ステップ = 16ビート = 64四分音符
        beats_per_loop = 16
        seconds_per_beat = 60.0 / self.bpm
        loop_duration = beats_per_loop * seconds_per_beat
        return loop_duration / self.LOOP_STEPS

    def set_bpm(self, bpm: float) -> None:
        """BPM変更"""
        self.bpm = bpm
```

**重要な特徴**:

1. **ドリフト補正**: 累積誤差を自動調整
2. **固定256ステップ**: 変更不可（ハードコーディング）
3. **高精度**: asyncioで正確なタイミング

**BPM計算例**:
```
BPM 120の場合:
- 1拍 = 0.5秒
- 16ビート = 8秒
- 256ステップ = 8秒
- 1ステップ = 8 / 256 = 0.03125秒 (31.25ms)

BPM 140の場合:
- 1拍 = 0.4286秒
- 16ビート = 6.857秒
- 1ステップ = 6.857 / 256 = 0.02678秒 (26.78ms)
```

---

### DestinationRouter: 送信先振り分け

メッセージを適切な送信先に振り分ける。

```python
class DestinationRouter:
    def __init__(
        self,
        osc_sender: OSCSender,
        midi_sender: MIDISender
    ):
        self.osc_sender = osc_sender
        self.midi_sender = midi_sender

    async def route(
        self,
        msg: ScheduledMessage,
        destinations: dict[str, DestinationConfig]
    ) -> None:
        """メッセージをルーティング"""
        dest = destinations.get(msg.destination_id)
        if not dest:
            logger.warning(f"Unknown destination: {msg.destination_id}")
            return

        if dest.type == "osc":
            await self.osc_sender.send(dest, msg.params)
        elif dest.type == "midi":
            await self.midi_sender.send(dest, msg.params)
        else:
            logger.error(f"Unknown destination type: {dest.type}")
```

**動作フロー**:
```
ScheduledMessage
  ↓
destination_id を確認
  ↓
  ├─ type == "osc" → OSCSender
  └─ type == "midi" → MIDISender
```

---

### OSCSender: OSCメッセージ送信

SuperDirt等へのOSC送信。

```python
from pythonosc import udp_client

class OSCSender:
    def __init__(self):
        self._clients: dict[tuple[str, int], udp_client.SimpleUDPClient] = {}

    async def send(
        self,
        dest: OscDestinationConfig,
        params: dict[str, Any]
    ) -> None:
        """OSCメッセージ送信"""
        # クライアント取得（キャッシュ）
        key = (dest.host, dest.port)
        if key not in self._clients:
            self._clients[key] = udp_client.SimpleUDPClient(
                dest.host,
                dest.port
            )

        client = self._clients[key]

        # OSCメッセージ送信
        # /dirt/play sound bd orbit 0 ...
        args = []
        for k, v in params.items():
            args.extend([k, v])

        client.send_message(dest.address, args)
```

**送信例**:
```python
# メッセージ
msg = ScheduledMessage(
    destination_id="superdirt",
    step=0,
    cycle=0.0,
    params={"sound": "bd", "gain": 0.8, "orbit": 0}
)

# OSC送信（SuperDirtへ）
# /dirt/play sound bd gain 0.8 orbit 0
```

---

### MIDISender: MIDIメッセージ送信

MIDI機器への送信。

```python
import mido

class MIDISender:
    def __init__(self):
        self._ports: dict[str, mido.ports.BaseOutput] = {}

    async def send(
        self,
        dest: MidiDestinationConfig,
        params: dict[str, Any]
    ) -> None:
        """MIDIメッセージ送信"""
        # ポート取得（キャッシュ）
        if dest.port_name not in self._ports:
            self._ports[dest.port_name] = mido.open_output(dest.port_name)

        port = self._ports[dest.port_name]

        # MIDI Note Onメッセージ作成
        note = params.get("note", 60)
        velocity = params.get("velocity", 100)
        channel = params.get("channel", dest.channel)

        msg = mido.Message(
            'note_on',
            note=note,
            velocity=velocity,
            channel=channel - 1  # 0-15に変換
        )

        port.send(msg)

        # Note Off（duration後）
        duration = params.get("duration", 0.1)
        await asyncio.sleep(duration)
        off_msg = mido.Message('note_on', note=note, velocity=0, channel=channel - 1)
        port.send(off_msg)
```

**送信例**:
```python
# メッセージ
msg = ScheduledMessage(
    destination_id="volca",
    step=64,
    cycle=1.0,
    params={"note": 60, "velocity": 100, "duration": 0.5}
)

# MIDI送信（Volca Keysへ）
# Note On: C4 (60), velocity 100
# (0.5秒後)
# Note Off: C4 (60)
```

---

### RuntimeState: 実行状態

```python
@dataclass
class RuntimeState:
    """ループエンジンの実行状態"""
    playing: bool = False
    current_step: int = 0
    bpm: float = 120.0
    loop_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "playing": self.playing,
            "current_step": self.current_step,
            "bpm": self.bpm,
            "loop_count": self.loop_count
        }
```

**SSEでの配信**:
```python
# SSEエンドポイント（Layer 1）
@router.get("/stream")
async def stream(engine: LoopEngine = Depends(get_loop_engine)):
    async def event_generator():
        while True:
            state = engine.state.to_dict()
            yield f"data: {json.dumps(state)}\n\n"
            await asyncio.sleep(0.1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

---

## oiduna_core: 通信プロトコル定義

### ディレクトリ構造

```
oiduna_core/
├── __init__.py
└── protocols.py         # 抽象インターフェース
```

### IPC Protocol

MARSとOidunaの通信インターフェース定義。

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class MessageBatchProtocol(Protocol):
    """メッセージバッチの抽象インターフェース"""

    def to_dict(self) -> dict:
        """辞書に変換"""
        ...

    @classmethod
    def from_dict(cls, data: dict) -> "MessageBatchProtocol":
        """辞書から生成"""
        ...
```

**目的**:
- 将来的なプロトコル変更に対応（HTTP → gRPC等）
- 実装の詳細を隠蔽
- テスタビリティ向上

---

## 再接続処理

### SuperCollider接続断への対応

```python
class OSCSender:
    async def send(self, dest, params):
        try:
            # 通常送信
            client.send_message(dest.address, args)
        except OSError as e:
            logger.warning(f"OSC send failed: {e}")
            # クライアントを再作成
            del self._clients[(dest.host, dest.port)]
            # 次回送信時に再接続
```

### MIDI機器接続断への対応

```python
class MIDISender:
    async def send(self, dest, params):
        try:
            # 通常送信
            port.send(msg)
        except Exception as e:
            logger.warning(f"MIDI send failed: {e}")
            # ポートを閉じて再オープン
            self._ports[dest.port_name].close()
            del self._ports[dest.port_name]
            # 次回送信時に再接続
```

---

## Rust移植の考慮事項

### 優先度: 最高 🔥

パフォーマンスクリティカルかつ並行処理が重要。

### Rust実装の方針

```rust
use tokio::time::{interval, Duration};

pub struct LoopEngine {
    destinations: HashMap<String, DestinationConfig>,
    clock: ClockGenerator,
    router: DestinationRouter,
    scheduler: Option<MessageScheduler>,
}

impl LoopEngine {
    pub async fn start(&mut self) {
        let step_duration = self.clock.calculate_step_duration();
        let mut interval = interval(Duration::from_secs_f64(step_duration));

        loop {
            interval.tick().await;
            self.on_step().await;
        }
    }

    async fn on_step(&mut self) {
        let messages = self.scheduler.as_ref()
            .map(|s| s.get_at_step(self.clock.step))
            .unwrap_or_default();

        for msg in messages {
            self.router.route(msg, &self.destinations).await;
        }

        self.clock.step = (self.clock.step + 1) % 256;
    }
}
```

### パフォーマンス向上見込み

- タイミング精度: 10倍向上（tokioのtimer）
- CPU使用率: 50-70%削減
- メモリ使用量: 30-40%削減
- 並行処理: Rustのasync/awaitで安全

---

## テスト例

```python
@pytest.mark.asyncio
async def test_loop_engine_step_callback():
    """ステップコールバックのテスト"""
    called_steps = []

    async def callback(step: int):
        called_steps.append(step)

    clock = ClockGenerator(bpm=120.0)

    # 5ステップだけ実行
    asyncio.create_task(clock.start(callback))
    await asyncio.sleep(0.2)  # 5ステップ分
    await clock.stop()

    assert len(called_steps) == 5
    assert called_steps == [0, 1, 2, 3, 4]

def test_destination_router_osc():
    """OSCルーティングのテスト"""
    osc_sender = Mock()
    midi_sender = Mock()
    router = DestinationRouter(osc_sender, midi_sender)

    dest = OscDestinationConfig(
        id="superdirt",
        type="osc",
        host="127.0.0.1",
        port=57120,
        address="/dirt/play"
    )
    msg = ScheduledMessage("superdirt", 0, 0.0, {"sound": "bd"})

    await router.route(msg, {"superdirt": dest})

    osc_sender.send.assert_called_once()
    midi_sender.send.assert_not_called()
```

---

## まとめ

### コア層の重要性

1. **パフォーマンスクリティカル**: リアルタイム処理
2. **高精度タイミング**: ドリフト補正
3. **送信先抽象化**: DestinationRouterで統一
4. **Rust移植最優先**: 最大の高速化効果

### 設計判断

- **256ステップ固定**: シンプルさ優先
- **asyncio**: Python標準ライブラリ
- **ドリフト補正**: 累積誤差防止
- **再接続処理**: 堅牢性確保

### 次のステップ

コア層を理解したら：
1. [Layer 2: アプリケーション層](./layer-2-application.md)でビジネスロジックを理解
2. [データフロー例](./data-flow-examples.md)で全体の流れを確認

---

**関連ドキュメント**:
- `packages/oiduna_loop/README.md`
- `packages/oiduna_core/README.md`
- ADR-0003: Python Timing Engine Phase 1
- ADR-0011: Rust Acceleration Strategy
