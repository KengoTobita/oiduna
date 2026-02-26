# クライアントリクエスト → ループ再生 完全フロー

**作成日**: 2026-02-26
**目的**: DistributionからのJSONリクエストが256ステップループに落とし込まれ、OSC/MIDI送信されるまでの完全な流れを追跡

---

## 概要

```
Distribution (MARS等)
  │
  │ HTTP POST /playback/pattern
  │ Content-Type: application/json
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│ CompiledSession JSON                                        │
│ {                                                           │
│   "environment": {...},    // BPM, scale, etc.             │
│   "tracks": {...},         // Track definitions            │
│   "sequences": {...},      // 256-step patterns            │
│   "mixer_lines": {...}     // Routing & effects            │
│ }                                                           │
└─────────────────────────────────────────────────────────────┘
  │
  │ ① ループデータ管理
  │ ② ルーティング解決
  │ ③ プロトコルチェック
  │ ④ 安定運用最適化
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│ ScheduledMessageBatch                                       │
│ {                                                           │
│   "messages": [                                            │
│     {                                                       │
│       "destination_id": "superdirt",                       │
│       "step": 0,                                           │
│       "params": {"s": "bd", "gain": 0.8, ...}              │
│     },                                                      │
│     ...                                                     │
│   ],                                                        │
│   "bpm": 120.0,                                            │
│   "pattern_length": 4.0                                    │
│ }                                                           │
└─────────────────────────────────────────────────────────────┘
  │
  │ MessageScheduler インデックス化
  │
  ▼
256 Step Loop (0 → 1 → 2 → ... → 255 → 0)
  │
  │ 各ステップで送信
  │
  ▼
OSC/MIDI 🔊
```

---

## Phase 1: クライアントからのリクエストJSON

### 具体例: キック＋スネア＋MIDIベースのパターン

```json
// POST /playback/pattern
// Content-Type: application/json

{
  "environment": {
    "bpm": 120.0,
    "scale": "C_minor",
    "default_gate": 0.9,
    "swing": 0.0,
    "loop_steps": 256
  },

  "tracks": {
    "kick": {
      "meta": {
        "track_id": "kick",
        "range_id": "default",
        "mute": false,
        "solo": false
      },
      "params": {
        "s": "bd",
        "s_path": "drum.acoustic.bd",
        "n": 0,
        "gain": 0.9,
        "pan": 0.5,
        "speed": 1.0,
        "begin": 0.0,
        "end": 1.0
      },
      "fx": {
        "room": 0.2,
        "size": 0.8,
        "delay_send": 0.0
      },
      "track_fx": {},
      "sends": [],
      "modulations": {},
      "destination_id": "superdirt",
      "mixer_line_id": "drums"
    },

    "snare": {
      "meta": {
        "track_id": "snare",
        "range_id": "default",
        "mute": false,
        "solo": false
      },
      "params": {
        "s": "sn",
        "s_path": "drum.acoustic.sn",
        "n": 0,
        "gain": 0.85,
        "pan": 0.5,
        "speed": 1.0,
        "begin": 0.0,
        "end": 1.0
      },
      "fx": {
        "room": 0.3,
        "size": 0.8,
        "delay_send": 0.1
      },
      "track_fx": {},
      "sends": [],
      "modulations": {},
      "destination_id": "superdirt",
      "mixer_line_id": "drums"
    },

    "bass": {
      "meta": {
        "track_id": "bass",
        "range_id": "default",
        "mute": false,
        "solo": false
      },
      "params": {
        "s": "",
        "n": 0,
        "gain": 1.0,
        "pan": 0.5,
        "speed": 1.0
      },
      "fx": {},
      "track_fx": {},
      "sends": [],
      "modulations": {},
      "destination_id": "volca_bass",
      "mixer_line_id": null
    }
  },

  "tracks_midi": {},

  "mixer_lines": {
    "drums": {
      "mixer_line_id": "drums",
      "destination_id": "superdirt",
      "orbit": 0,
      "track_ids": ["kick", "snare"],
      "spatial_fx": {
        "reverb_send": 0.25,
        "delay_send": 0.05
      }
    }
  },

  "sequences": {
    "kick": {
      "track_id": "kick",
      "events": [
        {"step": 0, "velocity": 1.0, "gate": 0.9},
        {"step": 16, "velocity": 0.9, "gate": 0.9},
        {"step": 32, "velocity": 1.0, "gate": 0.9},
        {"step": 48, "velocity": 0.9, "gate": 0.9}
      ]
    },

    "snare": {
      "track_id": "snare",
      "events": [
        {"step": 16, "velocity": 1.0, "gate": 0.85},
        {"step": 48, "velocity": 0.95, "gate": 0.85}
      ]
    },

    "bass": {
      "track_id": "bass",
      "events": [
        {"step": 0, "velocity": 0.9, "note": 36, "gate": 3.8},
        {"step": 8, "velocity": 0.85, "note": 43, "gate": 1.9},
        {"step": 16, "velocity": 0.9, "note": 36, "gate": 3.8},
        {"step": 24, "velocity": 0.8, "note": 38, "gate": 1.9}
      ]
    }
  },

  "scenes": {},

  "apply": {
    "timing": "bar",
    "track_ids": [],
    "scene_name": null
  }
}
```

### JSONデータ構造の説明

#### Environment（グローバル設定）
```json
{
  "bpm": 120.0,           // テンポ（BPM）
  "scale": "C_minor",     // 音階（使用しない場合もある）
  "default_gate": 0.9,    // デフォルトゲート長
  "swing": 0.0,           // スウィング量
  "loop_steps": 256       // ループ長（常に256）
}
```

#### Track（トラック定義）
```json
{
  "meta": {
    "track_id": "kick",   // トラックID（一意）
    "mute": false,        // ミュート状態
    "solo": false         // ソロ状態
  },

  "params": {
    "s": "bd",            // サウンド名（SuperDirt用）
    "gain": 0.9,          // ゲイン
    "pan": 0.5,           // パン（0.0=L, 1.0=R）
    // ... その他のサウンドパラメータ
  },

  "fx": {
    "room": 0.2,          // リバーブ
    "delay_send": 0.0     // ディレイセンド
    // ... その他のエフェクト
  },

  "destination_id": "superdirt",     // 🆕 送信先ID
  "mixer_line_id": "drums"           // 🆕 MixerLine ID（任意）
}
```

**重要**: `destination_id` がルーティングを決定します。

#### Sequence（256ステップパターン）
```json
{
  "track_id": "kick",
  "events": [
    {
      "step": 0,          // ステップ番号（0-255）
      "velocity": 1.0,    // ベロシティ（0.0-1.0）
      "note": null,       // MIDIノート（SuperDirtでは不使用）
      "gate": 0.9         // ゲート長（ステップ単位）
    },
    // ... 他のイベント
  ]
}
```

#### MixerLine（ルーティング＋空間エフェクト）
```json
{
  "mixer_line_id": "drums",
  "destination_id": "superdirt",   // このMixerLineの送信先
  "orbit": 0,                       // SuperDirt orbit番号
  "track_ids": ["kick", "snare"],   // このMixerLineに属するTrack
  "spatial_fx": {
    "reverb_send": 0.25,
    "delay_send": 0.05
  }
}
```

**MixerLineの役割**:
- 複数Trackをグループ化
- 共通の送信先とorbitを指定
- 空間エフェクト（リバーブ/ディレイ）を共有

---

## Phase 2: Oiduna内部処理

### 2-1. HTTPリクエスト受信（API Layer）

```python
# oiduna_api/routes/playback.py

@router.post("/pattern")
async def load_pattern(
    body: dict,
    loop_service: LoopService = Depends(get_loop_service),
) -> dict:
    """
    CompiledSessionを受信

    bodyは上記JSONそのまま
    """
    engine = loop_service.get_engine()
    result = engine._handle_compile(body)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.message)

    return {"status": "ok"}
```

### 2-2. CompiledSession解析（①ループデータ管理）

```python
# oiduna_loop/engine/loop_engine.py

def _handle_compile(self, payload: dict[str, Any]) -> CommandResult:
    """
    CompiledSessionをパースして処理

    【①ループデータ管理】
    - CompiledSession として保持
    - RuntimeState に保存
    """
    try:
        # Pydanticバリデーション
        cmd = CompileCommand(**payload)
    except ValidationError as e:
        return CommandResult.error(f"Invalid compile command: {e}")

    # CompiledSession 生成
    session = CompiledSession.from_dict(payload)

    # 【①ループデータ管理】RuntimeStateに保存
    self.state.load_session(session)

    # 【②③④】変換＋バリデーション＋最適化
    messages = self._compile_session_to_messages(session)

    # MessageSchedulerに登録
    batch = ScheduledMessageBatch(
        messages=tuple(messages),
        bpm=session.environment.bpm,
        pattern_length=session.environment.loop_steps / 16.0
    )
    self._message_scheduler.load_messages(batch)

    return CommandResult.ok()
```

### 2-3. CompiledSession → ScheduledMessage 変換

この処理で **②ルーティング + ③プロトコルチェック** を実施します。

```python
# oiduna_loop/engine/loop_engine.py

def _compile_session_to_messages(
    self,
    session: CompiledSession
) -> list[ScheduledMessage]:
    """
    CompiledSession → ScheduledMessage 変換

    【②ルーティング】Track → Destination解決
    【③プロトコルチェック】OSC/MIDI仕様検証
    """
    messages = []

    # 各Trackを処理
    for track_id, track in session.tracks.items():
        # Sequenceを取得
        sequence = session.sequences.get(track_id)
        if not sequence:
            logger.debug(f"Track '{track_id}' has no sequence, skipping")
            continue

        # Muteチェック
        if track.meta.mute:
            logger.debug(f"Track '{track_id}' is muted, skipping")
            continue

        # 【②ルーティング】destination_id解決
        destination_id = self._resolve_destination_id(track, session)

        # 【③プロトコルチェック】Validator取得
        validator = self._get_protocol_validator(destination_id)

        # 各Eventを処理
        for event in sequence:
            # Track + Event → params 生成
            params = self._merge_track_and_event(track, event, session)

            # 【③プロトコルチェック】バリデーション
            result = validator.validate_params(params)
            if not result.success:
                logger.error(
                    f"Protocol validation failed for track '{track_id}' "
                    f"at step {event.step}: {result.error_message}"
                )
                # エラーをスキップ（またはデフォルト値で続行）
                continue

            # ScheduledMessage生成
            messages.append(ScheduledMessage(
                destination_id=destination_id,
                cycle=event.step / 16.0,
                step=event.step,
                params=params
            ))

    # 【④安定運用】最適化
    messages = self._stability_manager.optimize_messages(messages)

    return messages
```

### 2-4. ルーティング解決（②）

```python
def _resolve_destination_id(
    self,
    track: Track,
    session: CompiledSession
) -> str:
    """
    Track → destination_id 解決

    優先順位:
    1. Track.destination_id（直接指定）
    2. MixerLine.destination_id（MixerLine経由）
    3. デフォルト（"superdirt"）
    """
    # 1. Track.destination_id が指定されていればそれを使用
    if track.destination_id:
        return track.destination_id

    # 2. MixerLine経由の場合
    if track.mixer_line_id:
        mixer_line = session.mixer_lines.get(track.mixer_line_id)
        if mixer_line and mixer_line.destination_id:
            return mixer_line.destination_id

    # 3. デフォルト
    return "superdirt"
```

### 2-5. Track + Event → params マージ

```python
def _merge_track_and_event(
    self,
    track: Track,
    event: Event,
    session: CompiledSession
) -> dict[str, Any]:
    """
    Track parameters + Event parameters → 最終params

    【Distributionの責任】
    - paramsの内容生成（Oidunaは解釈しない）

    【Oidunaの責任】
    - Track + Event のマージロジック
    - MixerLine からの orbit 取得
    """
    params = {}

    # Destination type 判定
    destination_id = self._resolve_destination_id(track, session)
    dest_config = self._destinations.get(destination_id)

    if isinstance(dest_config, OscDestinationConfig):
        # OSC (SuperDirt) 向けparams
        params = self._build_osc_params(track, event, session)

    elif isinstance(dest_config, MidiDestinationConfig):
        # MIDI向けparams
        params = self._build_midi_params(track, event, session)

    return params

def _build_osc_params(
    self,
    track: Track,
    event: Event,
    session: CompiledSession
) -> dict[str, Any]:
    """OSC (SuperDirt) 向けparams生成"""
    params = {}

    # TrackParams
    params["s"] = track.params.s
    params["n"] = track.params.n
    params["gain"] = track.params.gain * event.velocity  # velocity適用
    params["pan"] = track.params.pan
    params["speed"] = track.params.speed
    params["begin"] = track.params.begin
    params["end"] = track.params.end

    if track.params.cut is not None:
        params["cut"] = track.params.cut
    if track.params.legato is not None:
        params["legato"] = track.params.legato

    # FxParams
    if track.fx.room is not None:
        params["room"] = track.fx.room
    if track.fx.size is not None:
        params["size"] = track.fx.size
    if track.fx.delay_send is not None:
        params["delay"] = track.fx.delay_send
    if track.fx.cutoff is not None:
        params["cutoff"] = track.fx.cutoff
    # ... 他のエフェクト

    # MixerLine → orbit
    if track.mixer_line_id:
        mixer_line = session.mixer_lines.get(track.mixer_line_id)
        if mixer_line and mixer_line.orbit is not None:
            params["orbit"] = mixer_line.orbit

    # None値を除去（SuperDirtに送らない）
    params = {k: v for k, v in params.items() if v is not None}

    return params

def _build_midi_params(
    self,
    track: Track,
    event: Event,
    session: CompiledSession
) -> dict[str, Any]:
    """MIDI向けparams生成"""
    params = {}

    # MIDIノート（Event.noteから取得）
    if event.note is not None:
        params["note"] = event.note
        params["velocity"] = int(event.velocity * 127)  # 0.0-1.0 → 0-127

        # Gate → duration_ms変換
        step_duration_ms = (60_000 / session.environment.bpm) / 4  # 1ステップのms
        params["duration_ms"] = int(event.gate * step_duration_ms)

    # Gain → CC7 (Volume)
    if track.params.gain != 1.0:
        # 別のメッセージとして送る必要があるかも
        pass

    return params
```

### 2-6. プロトコルバリデーション（③）

```python
def _get_protocol_validator(
    self,
    destination_id: str
) -> ProtocolValidator:
    """destination typeに応じたValidatorを返す"""
    dest_config = self._destinations.get(destination_id)

    if isinstance(dest_config, OscDestinationConfig):
        return OscValidator()
    elif isinstance(dest_config, MidiDestinationConfig):
        return MidiValidator()
    else:
        return NoOpValidator()

# oiduna_protocol/validators.py

class OscValidator(ProtocolValidator):
    """OSCプロトコルバリデータ"""

    def validate_params(self, params: dict[str, Any]) -> ValidationResult:
        # 基本型チェック
        for key, value in params.items():
            if not isinstance(value, (int, float, str, bool)):
                return ValidationResult.error(
                    f"OSC param '{key}' has unsupported type: {type(value)}"
                )

        # メッセージサイズチェック（推定）
        estimated_size = len(str(params))  # 簡易推定
        if estimated_size > 65536:
            return ValidationResult.error(
                f"OSC message too large: {estimated_size} > 65536"
            )

        return ValidationResult.ok()

class MidiValidator(ProtocolValidator):
    """MIDIプロトコルバリデータ"""

    def validate_params(self, params: dict[str, Any]) -> ValidationResult:
        # Note範囲チェック
        if "note" in params:
            note = params["note"]
            if not isinstance(note, int) or not (0 <= note <= 127):
                return ValidationResult.error(
                    f"MIDI note must be 0-127, got: {note}"
                )

        # Velocity範囲チェック
        if "velocity" in params:
            velocity = params["velocity"]
            if not isinstance(velocity, int) or not (0 <= velocity <= 127):
                return ValidationResult.error(
                    f"MIDI velocity must be 0-127, got: {velocity}"
                )

        # Channel範囲チェック
        if "channel" in params:
            channel = params["channel"]
            if not isinstance(channel, int) or not (0 <= channel <= 15):
                return ValidationResult.error(
                    f"MIDI channel must be 0-15, got: {channel}"
                )

        return ValidationResult.ok()
```

### 2-7. メッセージ最適化（④安定運用）

```python
# oiduna_loop/stability/manager.py

class StabilityManager:
    def optimize_messages(
        self,
        messages: list[ScheduledMessage]
    ) -> list[ScheduledMessage]:
        """
        メッセージ最適化

        - ソート（step順、destination順）
        - 重複削除
        - OSC Bundle候補マーク（TODO）
        """
        # Step順、Destination順にソート
        sorted_messages = sorted(
            messages,
            key=lambda m: (m.step, m.destination_id)
        )

        # 重複削除（同一step、同一destination、同一params）
        # TODO: 実装

        return sorted_messages
```

---

## Phase 3: 変換結果（具体例）

### 上記JSONから生成されるScheduledMessageBatch

```python
# _compile_session_to_messages() の出力

messages = [
    # Kick track
    ScheduledMessage(
        destination_id="superdirt",
        cycle=0.0,
        step=0,
        params={
            "s": "bd",
            "n": 0,
            "gain": 0.9,      # track.gain * event.velocity = 0.9 * 1.0
            "pan": 0.5,
            "speed": 1.0,
            "begin": 0.0,
            "end": 1.0,
            "room": 0.2,
            "size": 0.8,
            "orbit": 0,       # MixerLine "drums" から取得
        }
    ),
    ScheduledMessage(
        destination_id="superdirt",
        cycle=1.0,
        step=16,
        params={
            "s": "bd",
            "n": 0,
            "gain": 0.81,     # 0.9 * 0.9
            "pan": 0.5,
            "speed": 1.0,
            "begin": 0.0,
            "end": 1.0,
            "room": 0.2,
            "size": 0.8,
            "orbit": 0,
        }
    ),

    # Snare track
    ScheduledMessage(
        destination_id="superdirt",
        cycle=1.0,
        step=16,
        params={
            "s": "sn",
            "n": 0,
            "gain": 0.85,
            "pan": 0.5,
            "speed": 1.0,
            "begin": 0.0,
            "end": 1.0,
            "room": 0.3,
            "size": 0.8,
            "delay": 0.1,
            "orbit": 0,       # 同じMixerLine
        }
    ),

    # Bass track
    ScheduledMessage(
        destination_id="volca_bass",
        cycle=0.0,
        step=0,
        params={
            "note": 36,       # C2
            "velocity": 114,  # int(0.9 * 127)
            "duration_ms": 475,  # gate=3.8 steps * 125ms/step
        }
    ),
    ScheduledMessage(
        destination_id="volca_bass",
        cycle=0.5,
        step=8,
        params={
            "note": 43,       # G2
            "velocity": 107,  # int(0.85 * 127)
            "duration_ms": 237,  # gate=1.9 steps
        }
    ),

    # ... 他のイベント
]

# ScheduledMessageBatch 生成
batch = ScheduledMessageBatch(
    messages=tuple(messages),  # 上記メッセージリスト
    bpm=120.0,
    pattern_length=16.0  # 256 steps / 16 = 16 cycles
)
```

### データ変換の追跡

#### Track "kick" + Event (step=0)

```
入力 (CompiledSession):
  track.params.s = "bd"
  track.params.gain = 0.9
  track.params.pan = 0.5
  track.fx.room = 0.2
  track.mixer_line_id = "drums"

  event.step = 0
  event.velocity = 1.0

  mixer_line.orbit = 0

↓ _merge_track_and_event()

出力 (ScheduledMessage.params):
  {
    "s": "bd",
    "gain": 0.9,     # track.gain * event.velocity
    "pan": 0.5,
    "room": 0.2,
    "orbit": 0       # MixerLineから取得
  }
```

#### Track "bass" + Event (step=0)

```
入力 (CompiledSession):
  track.destination_id = "volca_bass"

  event.step = 0
  event.note = 36
  event.velocity = 0.9
  event.gate = 3.8

  session.environment.bpm = 120

↓ _build_midi_params()

計算:
  velocity_midi = int(0.9 * 127) = 114
  step_duration_ms = (60000 / 120) / 4 = 125ms
  duration_ms = int(3.8 * 125) = 475ms

出力 (ScheduledMessage.params):
  {
    "note": 36,
    "velocity": 114,
    "duration_ms": 475
  }
```

---

## Phase 4: MessageScheduler インデックス化

### インデックス構造

```python
# MessageScheduler.load_messages(batch) 実行後

_messages_by_step = {
    0: [
        ScheduledMessage("superdirt", 0.0, 0, {"s": "bd", ...}),  # kick
        ScheduledMessage("volca_bass", 0.0, 0, {"note": 36, ...}),  # bass
    ],

    8: [
        ScheduledMessage("volca_bass", 0.5, 8, {"note": 43, ...}),  # bass
    ],

    16: [
        ScheduledMessage("superdirt", 1.0, 16, {"s": "bd", ...}),  # kick
        ScheduledMessage("superdirt", 1.0, 16, {"s": "sn", ...}),  # snare
        ScheduledMessage("volca_bass", 1.0, 16, {"note": 36, ...}),  # bass
    ],

    24: [
        ScheduledMessage("volca_bass", 1.5, 24, {"note": 38, ...}),  # bass
    ],

    32: [
        ScheduledMessage("superdirt", 2.0, 32, {"s": "bd", ...}),  # kick
    ],

    48: [
        ScheduledMessage("superdirt", 3.0, 48, {"s": "bd", ...}),  # kick
        ScheduledMessage("superdirt", 3.0, 48, {"s": "sn", ...}),  # snare
    ],

    # ... 他のステップ
}

# 空ステップはインデックスに存在しない（メモリ効率）
# 例: step=1, 2, 3, ... 7 は空（イベントなし）
```

---

## Phase 5: ループへの適用と再生

### ステップループ処理

```python
# oiduna_loop/engine/loop_engine.py

async def _step_loop(self) -> None:
    """256ステップループ（16th note単位）"""
    while self._running:
        if not self.state.playing:
            await asyncio.sleep(0.001)
            continue

        # 現在のステップ位置
        current_step = self.state.position.step  # 0-255

        # 【ステップ処理】このステップで鳴らすメッセージを取得
        scheduled_messages = self._message_scheduler.get_messages_at_step(
            current_step
        )

        if scheduled_messages:
            logger.debug(
                f"Step {current_step}: {len(scheduled_messages)} messages"
            )

            # Runtime hooks（拡張機能、例: cps注入）
            for hook in self._before_send_hooks:
                scheduled_messages = hook(
                    scheduled_messages,
                    self.state.bpm,
                    current_step
                )

            # 【送信】DestinationRouter経由で送信
            self._destination_router.send_messages(scheduled_messages)

        # ステップを進める
        self.state.advance_step()  # 0 → 1 → ... → 255 → 0

        # Drift補正付きスリープ
        step_duration = self.state.step_duration  # 60/bpm/4秒
        await self._drift_corrected_sleep(step_duration)
```

### 具体的なタイムライン（BPM=120、最初の2サイクル）

```
Time (ms)  Step  Actions
─────────────────────────────────────────────────────────────
0          0     ● Kick (SuperDirt OSC)
                 ● Bass Note=36 (MIDI)

125        1     (empty)
250        2     (empty)
...
1000       8     ● Bass Note=43 (MIDI)

1125       9     (empty)
...
2000       16    ● Kick (SuperDirt OSC)
                 ● Snare (SuperDirt OSC)
                 ● Bass Note=36 (MIDI)

2125       17    (empty)
...
3000       24    ● Bass Note=38 (MIDI)

...
4000       32    ● Kick (SuperDirt OSC)

...
```

**ステップ間隔**: 125ms（BPM=120の場合、60000ms / 120 / 4 = 125ms）

---

## Phase 6: 送信処理

### DestinationRouter での振り分け

```python
# oiduna_scheduler/router.py

def send_messages(self, messages: list[ScheduledMessage]) -> None:
    """メッセージをdestination別に振り分けて送信"""

    # Destination別にグルーピング
    by_destination = defaultdict(list)
    for msg in messages:
        by_destination[msg.destination_id].append(msg)

    # 各Destinationに送信
    for dest_id, dest_messages in by_destination.items():
        sender = self._senders.get(dest_id)
        if sender is None:
            logger.warning(f"Destination '{dest_id}' not registered")
            continue

        # 個別送信（TODO: Bundle対応）
        for msg in dest_messages:
            sender.send_message(msg.params)
```

### Step 16 の送信例

```python
# Step 16 で取得されたメッセージ
messages = [
    ScheduledMessage("superdirt", 1.0, 16, {"s": "bd", "gain": 0.81, ...}),
    ScheduledMessage("superdirt", 1.0, 16, {"s": "sn", "gain": 0.85, ...}),
    ScheduledMessage("volca_bass", 1.0, 16, {"note": 36, "velocity": 114, ...}),
]

# Grouping
by_destination = {
    "superdirt": [msg1, msg2],
    "volca_bass": [msg3],
}

# 送信
# superdirt → OscDestinationSender
sender = OscDestinationSender("127.0.0.1", 57120, "/dirt/play")

# msg1
sender.send_message({"s": "bd", "gain": 0.81, "orbit": 0, ...})
  → OSC: /dirt/play [s, bd, gain, 0.81, orbit, 0, ...]

# msg2
sender.send_message({"s": "sn", "gain": 0.85, "orbit": 0, ...})
  → OSC: /dirt/play [s, sn, gain, 0.85, orbit, 0, ...]

# volca_bass → MidiDestinationSender
sender = MidiDestinationSender("USB MIDI 1", default_channel=0)

# msg3
sender.send_message({"note": 36, "velocity": 114, "duration_ms": 475})
  → MIDI: note_on note=36 vel=114 ch=0
  → (475ms後) MIDI: note_off note=36 ch=0
```

### OSC送信の詳細

```python
# oiduna_scheduler/senders.py

class OscDestinationSender:
    def send_message(self, params: dict[str, Any]) -> None:
        """OSCメッセージ送信"""
        # params → OSC args format変換
        args = []
        for key, value in params.items():
            args.extend([key, value])

        # UDP送信
        self._client.send_message(self.address, args)

# 実際のOSCパケット（Wiresharkで見た場合）
# Address: /dirt/play
# Args: [
#   "s", "bd",
#   "gain", 0.81,
#   "pan", 0.5,
#   "orbit", 0,
#   "room", 0.2,
#   ...
# ]
```

### MIDI送信の詳細

```python
# oiduna_scheduler/senders.py

class MidiDestinationSender:
    def send_message(self, params: dict[str, Any]) -> None:
        """MIDIメッセージ送信"""
        if "note" in params:
            note = params["note"]
            velocity = params["velocity"]
            channel = params.get("channel", self.default_channel)

            # Note On送信
            self._port.send(mido.Message(
                "note_on",
                note=note,
                velocity=velocity,
                channel=channel
            ))

            # Note Off スケジューリング（TODO: duration_ms使用）
            # 現在は外部管理

# 実際のMIDIバイト（ハードウェアで見た場合）
# Note On: 0x90 0x24 0x72  (ch=0, note=36, vel=114)
# Note Off: 0x80 0x24 0x00 (475ms後)
```

---

## 完全フロー図（詳細版）

```
Distribution (MARS)
  │
  │ DSL Source
  │ kick [bd 0 _ _]
  │ snare [_ sn _ sn]
  │ bass {C2:4 G2:2 C2:4 Eb2:2}
  │
  ▼ MARS Compiler
  │
┌─────────────────────────────────────────────────────────────┐
│ CompiledSession JSON                                        │
│ {                                                           │
│   environment: {bpm: 120, ...},                            │
│   tracks: {                                                │
│     kick: {params: {s: "bd"}, destination_id: "superdirt"},│
│     snare: {...},                                          │
│     bass: {destination_id: "volca_bass"}                   │
│   },                                                       │
│   sequences: {                                             │
│     kick: {events: [{step:0}, {step:16}, ...]},           │
│     snare: {events: [{step:16}, {step:48}]},              │
│     bass: {events: [{step:0, note:36}, ...]}              │
│   },                                                       │
│   mixer_lines: {drums: {orbit: 0, ...}}                   │
│ }                                                           │
└─────────────────────────────────────────────────────────────┘
  │
  │ HTTP POST /playback/pattern
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│ Oiduna API Layer                                           │
│ - Pydantic validation                                      │
└─────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│ ① ループデータ管理                                          │
│ RuntimeState.load_session(session)                         │
│ - CompiledSession保持                                      │
│ - Environment/Track/Sequence階層維持                       │
└─────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│ ② ルーティング解決                                          │
│ _resolve_destination_id(track, session)                    │
│                                                             │
│ kick → track.destination_id = "superdirt"                  │
│        mixer_line.orbit = 0                                │
│                                                             │
│ bass → track.destination_id = "volca_bass"                 │
└─────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│ Track + Event → params マージ                               │
│ _merge_track_and_event(track, event, session)             │
│                                                             │
│ kick(step=0):                                              │
│   params = {s: "bd", gain: 0.9, orbit: 0, ...}            │
│                                                             │
│ bass(step=0):                                              │
│   params = {note: 36, velocity: 114, duration_ms: 475}    │
└─────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│ ③ プロトコルチェック                                        │
│ validator.validate_params(params)                          │
│                                                             │
│ OscValidator:                                              │
│   - 基本型チェック（int/float/str/bool）                   │
│   - メッセージサイズ < 64KB                                │
│                                                             │
│ MidiValidator:                                             │
│   - note ∈ [0, 127]                                        │
│   - velocity ∈ [0, 127]                                    │
│   - channel ∈ [0, 15]                                      │
└─────────────────────────────────────────────────────────────┘
  │
  │ ✅ Validation OK
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│ ScheduledMessage 生成                                       │
│                                                             │
│ [                                                           │
│   ScheduledMessage("superdirt", 0, {...}),  # kick         │
│   ScheduledMessage("volca_bass", 0, {...}), # bass         │
│   ScheduledMessage("superdirt", 16, {...}), # kick         │
│   ScheduledMessage("superdirt", 16, {...}), # snare        │
│   ...                                                       │
│ ]                                                           │
└─────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│ ④ 安定運用最適化                                            │
│ StabilityManager.optimize_messages(messages)               │
│                                                             │
│ - ソート（step順、destination順）                          │
│ - 重複削除                                                  │
│ - Bundle候補マーク（TODO）                                 │
└─────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│ MessageScheduler インデックス化                             │
│ _messages_by_step = {                                      │
│   0: [msg_kick, msg_bass],                                 │
│   16: [msg_kick, msg_snare, msg_bass],                     │
│   ...                                                       │
│ }                                                           │
└─────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│ ループエンジン起動待機                                       │
│ POST /playback/start                                       │
└─────────────────────────────────────────────────────────────┘
  │
  ▼
╔═════════════════════════════════════════════════════════════╗
║ ステップループ（256 steps, 16th note resolution）           ║
╚═════════════════════════════════════════════════════════════╝
  │
  ├─ Step 0 (time=0ms)
  │   ├─ get_messages_at_step(0) → [msg_kick, msg_bass]
  │   ├─ DestinationRouter.send_messages([msg_kick, msg_bass])
  │   │   ├─ "superdirt" → OscSender.send({"s": "bd", ...})
  │   │   │   └─ OSC → 127.0.0.1:57120 /dirt/play 🔊
  │   │   └─ "volca_bass" → MidiSender.send({"note": 36, ...})
  │   │       └─ MIDI → note_on 36 🔊
  │   └─ sleep(125ms)
  │
  ├─ Step 1-15 (empty)
  │   └─ sleep(125ms) × 15
  │
  ├─ Step 16 (time=2000ms)
  │   ├─ get_messages_at_step(16) → [msg_kick, msg_snare, msg_bass]
  │   ├─ DestinationRouter.send_messages([...])
  │   │   ├─ "superdirt" → kick 🔊 + snare 🔊
  │   │   └─ "volca_bass" → note_on 36 🔊
  │   └─ sleep(125ms)
  │
  ├─ ...
  │
  └─ Step 255
      └─ Loop back to Step 0
```

---

## まとめ: 責任範囲の明確化

### Distribution（MARS等）の責任

```json
{
  "tracks": {
    "kick": {
      "params": {
        "s": "bd",          // ✅ Distribution決定
        "gain": 0.9,        // ✅ Distribution決定
        // カスタムパラメータも自由
        "my_custom_param": 42
      },
      "destination_id": "superdirt"  // ✅ Distribution決定
    }
  }
}
```

**責任**:
- 音楽的判断（どの音をいつ鳴らすか）
- Track.params の内容生成
- カスタムパラメータの追加
- ルーティング指定（destination_id）

### Oidunaの責任（4つ）

#### ①ループデータ管理
```python
RuntimeState.load_session(session)
# - CompiledSession保持
# - Environment/Track/Sequence階層維持
# - Scene管理
```

#### ②ルーティング解決
```python
destination_id = _resolve_destination_id(track, session)
# - Track.destination_id
# - MixerLine.destination_id
# - 追跡可能性
```

#### ③プロトコルチェック
```python
validator.validate_params(params)
# - OSC仕様（型、サイズ）
# - MIDI仕様（範囲）
# - 早期エラー検出
```

#### ④安定運用
```python
StabilityManager.optimize_messages(messages)
# - Bundle化（TODO）
# - GC（TODO）
# - Drift補正（実装済み）
```

---

## 次のアクション

1. **Protocol Validator 実装**
   - `oiduna_protocol/validators.py` 作成
   - OscValidator / MidiValidator

2. **Track.destination_id フィールド追加**
   - `oiduna_core/ir/track.py` 修正
   - デフォルト値: "superdirt"

3. **_compile_session_to_messages() 実装**
   - `oiduna_loop/engine/loop_engine.py`
   - ルーティング + バリデーション + 変換

4. **テスト作成**
   - 上記JSONを使った統合テスト
   - プロトコルバリデーションのユニットテスト

この流れで進めてよろしいでしょうか？
