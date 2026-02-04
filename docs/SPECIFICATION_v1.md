# Oiduna Core 仕様書 v1.0

**作成日**: 2026-01-31
**対象バージョン**: Oiduna Core v1.0

---

## 目次

1. [設計哲学](#設計哲学)
2. [基本仕様](#基本仕様)
3. [IRデータモデル](#irデータモデル)
4. [マイクロタイミング（offset_ms）](#マイクロタイミングoffset_ms)
5. [Distribution側の責任](#distribution側の責任)
6. [標準的な実装パターン](#標準的な実装パターン)
7. [変則的な実装パターン](#変則的な実装パターン)
8. [REST API仕様](#rest-api仕様)
9. [Client Metadata共有](#client-metadata共有)
10. [実装例](#実装例)

---

## 設計哲学

### Oidunaのミッション

```
1. 「使用技術的に出来ません」をなくす
2. 「標準的な方法では驚くほど簡単に」実装できる
3. 「変則的なこともDistribution側で調整すれば可能」
```

### 責任の分離

```
┌─────────────────────────────────────────────────────┐
│                  Oiduna Core                        │
│  - 256 step固定フォーマットのプレイヤー              │
│  - 拍子・音楽理論の概念なし                          │
│  - 既に解決済みのnote番号を受信・再生                │
│  - シンプル・安定・高速                              │
└─────────────────────────────────────────────────────┘
                      ▲
                      │ IR (JSON)
                      │ (具体的なnote番号)
                      │
┌─────────────────────┴───────────────────────────────┐
│              Distribution（複数可能）                │
│  - DSLパース・コンパイル                             │
│  - 音高解決（スケール・コード → note番号）           │
│  - 拍子・音楽理論の処理                              │
│  - Oidunaフォーマットへの変換                        │
│  - 創意工夫・独自実装                                │
└─────────────────────────────────────────────────────┘
```

**設計原則**:
- **Oiduna**: シンプルな共通プラットフォーム、音楽理論レスなプレイヤー
- **Distribution**: 音楽的な創意工夫を実現、音高解決を担当
- **責任分離**: 音楽理論処理はDistribution側、再生制御はOiduna側

---

## 基本仕様

### 不変条件（絶対に守る）

```python
LOOP_STEPS = 256  # 固定、変更不可
```

**意味**:
1. **1 sequence = 256 steps**
2. **1 sequence = 1 loop**
3. **step 255 → step 0でループバック**

### ステップグリッド構造（4/4拍子基準）

```
256 steps = 16 bars × 16 steps/bar
         = 16 bars × 4 beats/bar × 4 steps/beat

step構造:
  0    4    8    12   16   20   24   28   ...  252  256
  |    |    |    |    |    |    |    |         |    |
  beat beat beat beat (bar 2...)              (bar 16)

1 step = 16分音符（4/4拍子 @ 120 BPM基準）
```

**重要**: これは基準であり、Distribution側で再解釈可能

### タイミング

**120 BPM基準**:
```
1 step = 60000ms / 120 BPM / 4 = 125ms
256 steps = 32秒
```

**BPM可変**:
```
step_duration_ms = 60000 / BPM / 4
total_duration_sec = 256 × step_duration_ms / 1000
```

---

## IRデータモデル

### Environment

```python
@dataclass
class Environment:
    bpm: float = 120.0              # テンポ（Distribution指定）
    default_gate: float = 1.0       # デフォルトゲート長
    swing: float = 0.0              # スウィング量
    loop_steps: int = 256           # ★ 固定（変更不可）

# 注意: 音楽理論情報（スケール、コード進行等）は含まない
# 音楽理論処理はDistribution側で管理
# Distribution側でnote番号に解決済みのIRを受け取る
```

**v1.1で削除予定のフィールド**:
- `scale: str` - スケール情報（Distribution側で管理すべき）
- `chords: list[Chord]` - コード進行（Distribution側で管理すべき）

**削除理由**: Oiduna Coreは既に具体的なMIDIノート番号に解決済みのIRを受け取るため、音楽理論情報は不要。旧システム(MARS)ではバックエンド側で音高解決を行っていたが、Oidunaでは音高解決はDistribution側の責任。

### Event（マイクロタイミング対応）

```python
@dataclass(frozen=True, slots=True)
class Event:
    step: int              # 0-255（グリッド位置、必須）
    velocity: float = 1.0  # 0.0-1.0（ベロシティ）
    note: int | None = None  # MIDIノート番号（メロディ用）
    gate: float = 1.0      # ゲート長比率

    # ★ v1.0で追加
    offset_ms: float = 0.0  # マイクロタイミングオフセット（ミリ秒）
                            # 負の値 = 早める、正の値 = 遅らせる
                            # 推奨範囲: -62.5 ~ +62.5（約±半step）
```

**JSON例**:
```json
{
  "step": 0,
  "velocity": 1.0,
  "gate": 1.0,
  "note": null,
  "offset_ms": 10.42
}
```

### EventSequence

```python
@dataclass
class EventSequence:
    track_id: str
    _events: tuple[Event, ...]  # 複数イベント可
    _step_index: dict[int, list[int]]  # O(1)検索用インデックス
```

**重要**: 1つのstepに**複数のEvent**を配置可能

**例（三連譜）**:
```json
{
  "track_id": "hihat",
  "events": [
    {"step": 0, "offset_ms": 0.0, "velocity": 1.0},
    {"step": 0, "offset_ms": 166.67, "velocity": 0.8},
    {"step": 0, "offset_ms": 333.33, "velocity": 0.8}
  ]
}
```

### CompiledSession（トップレベル）

```python
@dataclass
class CompiledSession:
    environment: Environment
    tracks: dict[str, Track]              # SuperDirtトラック
    tracks_midi: dict[str, TrackMidi]     # MIDIトラック
    mixer_lines: dict[str, MixerLine]     # ミキサーライン
    sequences: dict[str, EventSequence]   # イベントシーケンス
    scenes: dict[str, Scene]              # シーン定義
    apply: ApplyCommand | None            # 適用タイミング
```

---

## マイクロタイミング（offset_ms）

### 目的

**256 stepグリッドでは表現できない細かいタイミングを実現**:
- 三連譜（8分音符3連、16分音符3連）
- 5連符、7連符などのポリリズム
- 32分音符、64分音符
- スウィング・シャッフル
- フラム、ロール
- ヒューマナイゼーション

### 仕様

**フィールド**: `offset_ms: float`

**意味**: グリッドステップからのオフセット時間（ミリ秒）

**値の範囲**:
- 理論上: 任意の浮動小数点数
- 推奨: `-62.5 ~ +62.5`（約±半step @ 120 BPM）
- 実用: `-125 ~ +125`（約±1 step）

**処理**:
```python
# Oiduna Core内部処理
base_time = step * step_duration
actual_time = base_time + (offset_ms / 1000.0)
```

### 使用例

#### 三連譜（8分音符3連）

```python
# 1拍（500ms @ 120 BPM）を3分割
triplet_interval = 500 / 3  # 166.67ms

events = [
    Event(step=0, offset_ms=0.0),           # 1つ目
    Event(step=0, offset_ms=166.67),        # 2つ目
    Event(step=0, offset_ms=333.33)         # 3つ目
]
```

#### 32分音符

```python
# 16分音符（125ms @ 120 BPM）を2分割
note_32nd = 125 / 2  # 62.5ms

events = [
    Event(step=0, offset_ms=0.0),      # 1つ目
    Event(step=0, offset_ms=62.5),     # 2つ目
    Event(step=1, offset_ms=0.0),      # 3つ目
    Event(step=1, offset_ms=62.5)      # 4つ目
]
```

#### スウィング

```python
# 奇数ステップを遅らせる
swing_ms = 20.0

events = [
    Event(step=0, offset_ms=0.0),           # ストレート
    Event(step=1, offset_ms=swing_ms),      # 遅らせる
    Event(step=2, offset_ms=0.0),           # ストレート
    Event(step=3, offset_ms=swing_ms)       # 遅らせる
]
```

#### フラム

```python
# ゴーストノート + メインノート
events = [
    Event(step=16, offset_ms=-5.0, velocity=0.3),  # ゴースト（5ms前）
    Event(step=16, offset_ms=0.0, velocity=1.0)     # メイン
]
```

---

## Distribution側の責任

### 責任範囲

Distribution開発者は以下を担当:

1. ✅ **DSLパース・コンパイル**
2. ✅ **音高解決（スケール・コード → MIDIノート番号）**
3. ✅ **拍子・音楽理論の処理**
4. ✅ **256 stepフォーマットへの変換**
5. ✅ **offset_msの計算**
6. ✅ **創意工夫・独自実装**

**重要**: Oiduna Coreには既に解決済みの具体的なMIDIノート番号を送信する。スケール・コード進行等の音楽理論情報は送信しない。

### 基本ワークフロー

```
1. DSLパース
   ↓
2. 内部表現構築（Distribution固有のフォーマット）
   ↓
3. 音高解決
   - スケール情報 + 度数 → MIDIノート番号
   - コード進行 + 機能 → MIDIノート番号
   ↓
4. 拍子・音楽理論の処理
   ↓
5. Oiduna IRフォーマットへ変換
   - step: 0-255にマップ
   - note: 解決済みのMIDIノート番号
   - offset_ms: 計算
   ↓
6. HTTP POST → Oiduna Core
```

### Distribution側ベースクラス（推奨）

```python
class OidunaDistribution:
    """Distribution基底クラス（推奨実装）"""

    # Oidunaフォーマット定数
    OIDUNA_TOTAL_STEPS = 256
    STANDARD_BPM = 120.0

    def __init__(self, beats_per_bar: int, note_value: int = 4):
        """
        Args:
            beats_per_bar: 1小節の拍数（分子）
            note_value: 何の音符を1拍とするか（分母）
        """
        self.beats_per_bar = beats_per_bar
        self.note_value = note_value

        # 時間計算
        self.step_duration_ms = 60000.0 / self.STANDARD_BPM / 4  # 125ms
        self.total_duration_ms = self.OIDUNA_TOTAL_STEPS * self.step_duration_ms  # 32000ms

        # 1拍・1小節の時間
        self.beat_duration_ms = 60000.0 / self.STANDARD_BPM
        self.bar_duration_ms = self.beats_per_bar * self.beat_duration_ms

        # 小節数計算
        self.exact_num_bars = self.total_duration_ms / self.bar_duration_ms
        self.num_bars = int(self.exact_num_bars)

        # ステップ配分
        self.steps_per_beat = 16 // self.note_value
        self.steps_per_bar = self.beats_per_bar * self.steps_per_beat
        self.used_steps = self.num_bars * self.steps_per_bar
        self.unused_steps = self.OIDUNA_TOTAL_STEPS - self.used_steps

    def compile_to_oiduna(self, dsl_code: str) -> CompiledSession:
        """サブクラスで実装"""
        raise NotImplementedError
```

---

## 標準的な実装パターン

### パターンA: 4/4拍子（標準）

**最もシンプル、Oidunaフォーマットと完全一致**

```python
class StandardDistribution(OidunaDistribution):
    def __init__(self):
        super().__init__(beats_per_bar=4, note_value=4)

        # 自動計算結果:
        # num_bars = 16
        # steps_per_bar = 16
        # used_steps = 256
        # unused_steps = 0
```

**ステップマッピング**:
```
256 steps = 16 bars × 16 steps/bar
完全一致、変換不要
```

---

### パターンB: 3/4拍子（ワルツ）

**時間統一アプローチ**

```python
class WaltzDistribution(OidunaDistribution):
    def __init__(self):
        super().__init__(beats_per_bar=3, note_value=4)

        # 自動計算結果:
        # bar_duration_ms = 1500ms
        # exact_num_bars = 21.333...
        # num_bars = 21
        # steps_per_bar = 12
        # used_steps = 252
        # unused_steps = 4

    def compile_to_oiduna(self, dsl_code: str) -> CompiledSession:
        """ワルツ → Oiduna IR"""
        events = []

        # 21小節のワルツパターン
        for bar in range(self.num_bars):  # 0-20
            for beat in range(self.beats_per_bar):  # 0-2
                beat_step = bar * self.steps_per_bar + beat * self.steps_per_beat
                velocity = 1.0 if beat == 0 else 0.7  # 強拍・弱拍
                events.append(Event(step=beat_step, velocity=velocity))

        # unused_steps（252-255）は何もしない（無音）

        return CompiledSession(
            environment=Environment(bpm=self.STANDARD_BPM, loop_steps=256),
            sequences={"waltz": EventSequence.from_events("waltz", events)}
        )
```

**結果**:
```
steps 0-251:   21小節のワルツ（31.5秒）
steps 252-255: 無音（4 steps = 0.5秒）
総時間: 32秒（4/4拍子と統一）
```

---

### パターンC: 5/4拍子

```python
class FiveFourDistribution(OidunaDistribution):
    def __init__(self):
        super().__init__(beats_per_bar=5, note_value=4)

        # 自動計算結果:
        # num_bars = 12
        # steps_per_bar = 20
        # used_steps = 240
        # unused_steps = 16
```

**結果**:
```
steps 0-239:   12小節の5/4拍子（30秒）
steps 240-255: 無音（16 steps = 2秒）
総時間: 32秒
```

---

### 標準パターンまとめ

| 拍子 | 小節数 | 使用steps | 余りsteps | 余り時間 | 総時間 |
|------|--------|-----------|-----------|----------|--------|
| 4/4 | 16 | 256 | 0 | 0秒 | 32秒 |
| 3/4 | 21 | 252 | 4 | 0.5秒 | 32秒 |
| 5/4 | 12 | 240 | 16 | 2秒 | 32秒 |
| 6/8 | 21 | 252 | 4 | 0.5秒 | 32秒 |
| 7/8 | 18 | 252 | 4 | 0.5秒 | 32秒 |

**設計原則**: 総時間32秒で統一（DJ B2B対応）

---

## 変則的な実装パターン

### ハードウェアシーケンサー的テクニック

**背景**: 固定ステップのハードウェアシーケンサーで一般的に使われるテクニック

**Distribution開発者の自由**: これらの方法はDistribution設計者が選択・調整

---

### テクニック1: 変拍子ステップ + 余りステップ

**コンセプト**: 拍子の累乗でステップを管理

**例: 3拍子を3の累乗で管理**

```python
class PowerOfThreeDistribution:
    def __init__(self):
        # 3の累乗でステップ管理
        self.steps_per_beat = 9   # 3^2
        self.steps_per_bar = 27   # 3^3

        # 256 stepsでの配分
        self.num_bars = 256 // 27  # 9小節
        self.used_steps = 243      # 9 × 27
        self.unused_steps = 13     # 余り
```

**視覚化**:
```
Bar 0:  27 steps (steps 0-26)
Bar 1:  27 steps (steps 27-53)
...
Bar 8:  27 steps (steps 216-242)
Unused: 13 steps (steps 243-255)
```

**用途**: 3の累乗で美しい構造を作る

---

### テクニック2: 切り取りパターン

**コンセプト**: 余らせるのではなく、意図的に切り取る

**例: 5stepパターンを繰り返し**

```python
class FiveStepRepeatDistribution:
    def __init__(self):
        self.pattern_length = 5
        self.num_repeats = 256 // 5  # 51回
        self.used_steps = 51 * 5     # 255 steps
        self.cut_steps = 1           # 1 step切り取り
```

**視覚化**:
```
Pattern (5 steps): |1 2 3 4 5|
Repeat 51 times:   |1 2 3 4 5|1 2 3 4 5|...|1 2 3 4 5|
Total: 255 steps (1 step切り取り)
```

**結果**: 256ループごとに1 stepずつ位相がずれる（フェージング効果）

---

### テクニック3: ジャージークラブパターン

**コンセプト**: 不均等なビート構造 + 切り取り

**例: 4step × 2beat + 3step × 3beat - 1step**

```python
class JerseyClubDistribution:
    def __init__(self):
        # パターン構造
        # Section A: 4 steps × 2 beats = 8 steps
        # Section B: 3 steps × 3 beats = 9 steps
        # Total: 17 steps - 1 = 16 steps per bar

        self.section_a_steps = 8
        self.section_b_steps = 9
        self.bar_pattern = 16  # 17 - 1（切り取り）

        self.num_bars = 256 // 16  # 16小節
```

**視覚化**:
```
Bar pattern (16 steps):
  Section A: |1 2 3 4|1 2 3 4|    (4×2 = 8 steps)
  Section B: |1 2 3|1 2 3|1 2|     (3×3 = 9 steps, 最後1 step切り取り)

Repeat 16 times → 256 steps
```

**用途**: ジャージークラブ、フットワーク等のジャンル特有のグルーヴ

---

### テクニック4: 余りステップの音楽的活用

**コンセプト**: 余りステップを無音にせず、音楽的に使う

**例: 3/4拍子の余り4 stepsでフィルイン**

```python
class WaltzWithFillDistribution(OidunaDistribution):
    def __init__(self):
        super().__init__(beats_per_bar=3, note_value=4)
        # unused_steps = 4

    def compile_to_oiduna(self, dsl_code: str) -> CompiledSession:
        events = []

        # 21小節のメインパターン（steps 0-251）
        for bar in range(self.num_bars):
            for beat in range(self.beats_per_bar):
                beat_step = bar * self.steps_per_bar + beat * self.steps_per_beat
                events.append(Event(step=beat_step, velocity=1.0))

        # 余り4 steps（252-255）にフィルイン
        fill_pattern = [
            Event(step=252, velocity=1.0),
            Event(step=253, velocity=0.8),
            Event(step=254, velocity=0.9),
            Event(step=255, velocity=1.0)
        ]
        events.extend(fill_pattern)

        return CompiledSession(...)
```

**結果**:
```
steps 0-251:   21小節のワルツ
steps 252-255: フィルイン（ループ前のフレーズ）
```

**用途**: ループのつなぎ目を音楽的に処理

---

### テクニック5: 複合パターン

**コンセプト**: 複数の拍子を組み合わせ

**例: 3/4 + 5/4のシーケンス**

```python
class CompoundMeterDistribution:
    def __init__(self):
        # Section A: 3/4拍子、8小節、96 steps
        self.section_a_steps_per_bar = 12
        self.section_a_bars = 8
        self.section_a_total = 96

        # Section B: 5/4拍子、8小節、160 steps
        self.section_b_steps_per_bar = 20
        self.section_b_bars = 8
        self.section_b_total = 160

        # Total: 96 + 160 = 256 steps（完璧！）

    def compile_to_oiduna(self, dsl_code: str) -> CompiledSession:
        events = []

        # Section A: 3/4拍子（steps 0-95）
        for bar in range(8):
            for beat in range(3):
                beat_step = bar * 12 + beat * 4
                events.append(Event(step=beat_step, velocity=1.0))

        # Section B: 5/4拍子（steps 96-255）
        for bar in range(8):
            for beat in range(5):
                beat_step = 96 + bar * 20 + beat * 4
                events.append(Event(step=beat_step, velocity=1.0))

        return CompiledSession(...)
```

**視覚化**:
```
Section A (3/4): steps 0-95   (8 bars)
Section B (5/4): steps 96-255 (8 bars)
Total: 256 steps（余りなし）
```

---

### テクニック6: プライムナンバーパターン

**コンセプト**: 素数長のパターンで複雑なポリリズム

**例: 7 stepパターン × 36回 + 4 steps**

```python
class PrimePatternDistribution:
    def __init__(self):
        self.pattern_length = 7  # 素数
        self.num_repeats = 36
        self.used_steps = 252    # 7 × 36
        self.unused_steps = 4
```

**結果**: 7 stepごとに繰り返すため、256 stepループ内で位相が複雑に変化

---

### 変則パターンまとめ

| テクニック | 特徴 | 用途 |
|-----------|------|------|
| 累乗ステップ | 数学的に美しい | 実験的な音楽 |
| 切り取り | フェージング効果 | ミニマル、テクノ |
| ジャージークラブ | 不均等ビート | ジャンル特有グルーヴ |
| 余り活用 | つなぎ目処理 | 音楽的な完結性 |
| 複合拍子 | 拍子変化 | プログレッシブ |
| 素数パターン | 複雑なポリリズム | 実験的 |

**重要**: これらはすべてDistribution側の選択。Oidunaは256 stepループを提供するのみ。

---

## REST API仕様

### エンドポイント

#### セッション制御

```
POST   /playback/session         # セッション全体ロード
PATCH  /playback/environment      # 環境設定変更
PATCH  /playback/tracks/{id}/params  # トラックパラメータ変更
POST   /playback/start            # 再生開始
POST   /playback/stop             # 再生停止
GET    /playback/status           # ステータス取得
```

#### リアルタイム発音

```
POST   /playback/trigger/osc      # SuperDirt音即座発音
POST   /playback/trigger/midi     # MIDIノート即座発音
```

#### 変更管理

```
DELETE /playback/changes/{id}     # 保留中変更の取り消し
GET    /playback/changes/pending  # 保留中変更一覧
POST   /playback/changes/cancel-all  # 全取り消し
```

#### Client Metadata共有

```
POST   /session/clients/{client_id}/metadata   # メタデータ登録・更新
GET    /session/clients                        # 全クライアント情報取得
GET    /session/clients/{client_id}            # 特定クライアント情報取得
DELETE /session/clients/{client_id}            # クライアント削除（切断時）
```

**client_id仕様**:
- クライアント側で任意の文字列を設定（必須、nullable=false）
- 同一Distribution内で複数クライアントを識別
- 例: `"user_alice_mars"`, `"dj_bob_tidal"`, `"live_set_1"`

### タイミング制御

**すべてのセッション制御APIで利用可能**:

```json
{
  "data": {...},
  "timing": {
    "type": "boundary" | "absolute",

    // type=boundary の場合
    "unit": "beat" | "bar" | "seq",

    // type=absolute の場合
    "step": 0-255
  }
}
```

**デフォルト**: `{"type": "boundary", "unit": "bar"}`

---

## Client Metadata共有

### 設計思想

**目的**: Distribution間・クライアント間の情報共有を実現

**Oiduna Coreの役割**:
- ✅ メタデータの保持・配信（情報ハブ）
- ✅ SSEによるリアルタイム通知
- ❌ メタデータの解釈・処理（音楽理論を理解しない）

**Distribution/Clientの役割**:
- ✅ メタデータの意味理解・活用
- ✅ 他クライアントとの協調
- ✅ 音楽理論の処理

### アーキテクチャ

```
┌──────────────┐     metadata     ┌──────────────┐
│ Client A     ├──────POST────────>│              │
│ (MARS, Cmaj) │                   │  Oiduna Core │
└──────────────┘                   │  (metadata   │
                                   │   hub)       │
┌──────────────┐     metadata     │              │
│ Client B     ├──────GET─────────>│              │
│(Tidal, 参照) │                   │              │
└──────────────┘                   └──────────────┘
                                          │
                                     SSE  │ client_metadata_updated
                                          ▼
                                   すべてのクライアント
```

### データモデル

```python
@dataclass
class ClientMetadata:
    """クライアントメタデータ（Oiduna Core内部）"""
    client_id: str                    # クライアント識別子（必須）
    metadata: dict[str, Any]          # 任意のJSON構造
    updated_at: float                 # 更新タイムスタンプ
```

**重要**: Oidunaはメタデータを**保持するが理解しない**

### API詳細

#### メタデータ登録・更新

```http
POST /session/clients/{client_id}/metadata
Content-Type: application/json

{
  "scale": "C_major",
  "key": "C",
  "chords": ["Cmaj7", "Dm7", "G7", "Cmaj7"],
  "chord_position": 0,
  "bpm_suggestion": 120,
  "message": "Starting with II-V-I in C",
  "custom_data": {...}
}
```

**注意**:
- `client_id`はURLパスパラメータで指定（必須）
- 同一`client_id`で複数回POSTすると更新される
- メタデータは完全に置き換えられる（部分更新ではない）

**レスポンス**:
```json
{
  "client_id": "user_alice_mars",
  "updated_at": 1234567890.123
}
```

#### 全クライアント情報取得

```http
GET /session/clients
```

**レスポンス**:
```json
{
  "user_alice_mars": {
    "metadata": {
      "scale": "C_major",
      "chords": ["Cmaj7", "Dm7", "G7", "Cmaj7"],
      "chord_position": 0
    },
    "updated_at": 1234567890.123
  },
  "dj_bob_tidal": {
    "metadata": {
      "scale": "C_major",
      "message": "Following Alice's progression"
    },
    "updated_at": 1234567890.456
  }
}
```

#### 特定クライアント情報取得

```http
GET /session/clients/{client_id}
```

**レスポンス**:
```json
{
  "metadata": {
    "scale": "C_major",
    "chord_position": 2
  },
  "updated_at": 1234567890.123
}
```

#### クライアント削除

```http
DELETE /session/clients/{client_id}
```

### SSE統合

```javascript
// 新規イベント追加

event: client_metadata_updated
data: {
  "client_id": "user_alice_mars",
  "metadata": {
    "chord_position": 2,
    "message": "Moving to G7"
  },
  "updated_at": 1234567890.123
}

event: client_connected
data: {
  "client_id": "dj_bob_tidal"
}

event: client_disconnected
data: {
  "client_id": "user_alice_mars"
}
```

### 標準メタデータフォーマット（提案）

**目的**: 異なるDistribution間でも互換性を持つメタデータ標準

**ステータス**: v1.1で提案、将来的に正式化予定

#### 推奨フィールド

```typescript
interface StandardMetadata {
  // ========== 音楽理論情報 ==========
  scale?: string;              // "C_major", "A_minor", "D_dorian"
  key?: string;                // "C", "F#", "Bb"
  mode?: string;               // "major", "minor", "dorian", "phrygian"

  // コード進行
  chords?: string[];           // ["Cmaj7", "Dm7", "G7", "Cmaj7"]
  chord_position?: number;     // 現在のコード位置 (0-indexed)
  chord_format?: string;       // "symbol" | "roman" | "custom"

  // ========== テンポ・リズム ==========
  bpm?: number;                // 120.0
  bpm_suggestion?: number;     // 他クライアントへの提案BPM
  time_signature?: string;     // "4/4", "3/4", "5/4"

  // ========== セクション情報 ==========
  section?: string;            // "intro", "verse", "chorus", "bridge", "outro"
  section_bar?: number;        // セクション内の小節位置
  intensity?: number;          // 0.0-1.0（エネルギーレベル）

  // ========== メッセージ・通知 ==========
  message?: string;            // 自由形式メッセージ
  next_change?: {              // 次の変更予告
    type: "key" | "section" | "bpm" | "custom";
    value: any;
    bars_until: number;
  };

  // ========== クライアント情報 ==========
  distribution_type?: string;  // "mars", "tidal", "sonic_pi", "custom"
  client_name?: string;        // 表示名

  // ========== カスタムデータ ==========
  custom?: Record<string, any>;  // Distribution固有の拡張
}
```

#### 使用例

**例1: 基本的な情報共有**
```json
{
  "scale": "C_major",
  "key": "C",
  "chords": ["Cmaj7", "Dm7", "G7", "Cmaj7"],
  "chord_position": 0,
  "bpm": 120,
  "distribution_type": "mars",
  "client_name": "Alice"
}
```

**例2: キー変更の予告**
```json
{
  "scale": "C_major",
  "key": "C",
  "message": "Key change coming",
  "next_change": {
    "type": "key",
    "value": "F_major",
    "bars_until": 4
  }
}
```

**例3: セクション情報**
```json
{
  "section": "buildup",
  "section_bar": 6,
  "intensity": 0.75,
  "message": "Building to drop",
  "next_change": {
    "type": "section",
    "value": "drop",
    "bars_until": 2
  }
}
```

### B2Bユースケース

#### ケース1: コード進行の同期

```python
# Client A (リーダー)
oiduna_client.update_metadata({
    "client_id": "dj_alice",
    "scale": "C_major",
    "chords": ["Cmaj7", "Dm7", "G7", "Cmaj7"],
    "chord_position": 0
})

# Client B (フォロワー)
all_clients = oiduna_client.get_clients()
leader_metadata = all_clients["dj_alice"]["metadata"]
leader_chords = leader_metadata["chords"]
# → ["Cmaj7", "Dm7", "G7", "Cmaj7"]を参照してコード進行を合わせる
```

#### ケース2: リアルタイムコード進行追従

```python
# Client A: SSEでコード進行をブロードキャスト
@every_bar
def update_chord_position():
    oiduna_client.update_metadata({
        "chord_position": current_position,
        "message": f"Now on {current_chord}"
    })

# Client B: SSE受信してリアルタイム追従
@sse_handler
def on_metadata_update(event):
    if event.data.get("chord_position") is not None:
        sync_to_chord(event.data["chord_position"])
```

#### ケース3: キー変更の協調

```python
# Client A: キー変更予告
oiduna_client.update_metadata({
    "message": "Key change to F in 4 bars",
    "next_change": {
        "type": "key",
        "value": "F_major",
        "bars_until": 4
    }
})

# Client B: 予告を受けて準備
@sse_handler
def on_metadata_update(event):
    if "next_change" in event.data:
        change = event.data["next_change"]
        if change["type"] == "key":
            prepare_key_change(
                new_key=change["value"],
                bars_until=change["bars_until"]
            )
```

#### ケース4: 異なるDistribution間の互換性

```python
# MARS Distribution
mars_client.update_metadata({
    "scale": "C_major",
    "chords": ["Cmaj7", "Dm7", "G7"],  # シンボル形式
    "distribution_type": "mars"
})

# TidalCycles Distribution
tidal_client = get_oiduna_clients()
mars_metadata = tidal_client["mars_user"]["metadata"]

# コード進行を取得して自分の形式に変換
chords = mars_metadata["chords"]  # ["Cmaj7", "Dm7", "G7"]
tidal_chords = convert_to_tidal_format(chords)  # Distribution側で変換
```

### 実装ガイドライン

#### Client ID命名規則（推奨）

```
{username}_{distribution}_{session}

例:
- "alice_mars_live1"
- "bob_tidal_set2"
- "charlie_sonicpi_jam"
```

**重要**:
- `client_id`はクライアント側で設定（必須、nullable=false）
- 同一Distributionで複数クライアントを識別可能
- セッション全体で一貫して使用

#### セッションとメタデータの関係

**重要な設計原則**:
- **セッションIR** (`POST /playback/session`): 音楽データ（イベント、トラック等）
- **クライアントメタデータ** (`POST /session/clients/{client_id}/metadata`): 情報共有データ（スケール、コード進行等）

**分離の理由**:
- IRには音楽理論情報を含めない（既に解決済みのnote番号のみ）
- メタデータは他クライアントとの情報共有のみに使用
- Oiduna Coreはメタデータを保持するが処理しない

**典型的なワークフロー**:
```python
# 1. client_id設定
client_id = "alice_mars_live1"

# 2. セッションIR送信（音楽データ）
oiduna.post_session(compiled_session)

# 3. メタデータ送信（情報共有用）
oiduna.update_client_metadata(
    client_id=client_id,
    metadata={
        "scale": "C_major",
        "chords": ["Cmaj7", "Dm7", "G7"],
        "message": "Playing jazz in C"
    }
)

# 4. 他クライアントのメタデータ参照
other_clients = oiduna.get_clients()
if "bob_tidal_set2" in other_clients:
    bob_scale = other_clients["bob_tidal_set2"]["metadata"]["scale"]
    # スケールを合わせる等
```

#### メタデータ更新頻度

- **高頻度更新が必要**: `chord_position`, `section_bar`, `intensity`
- **低頻度更新**: `scale`, `key`, `chords`, `time_signature`
- **イベント駆動**: `message`, `next_change`

#### エラーハンドリング

```python
try:
    oiduna_client.update_metadata(metadata)
except ClientIDRequired:
    # client_idが未設定
    pass
except MetadataUpdateFailed:
    # ネットワークエラー等
    pass
```

### 将来の拡張

**v1.2以降で検討**:
- メタデータスキーマバリデーション（JSON Schema）
- Distribution間メタデータ変換プロトコル
- メタデータ履歴機能
- クライアントグループ機能（チーム単位の共有）

---

## 実装例

### 例1: シンプルな4/4拍子Distribution

```python
from oiduna_core.models.ir import *

class SimpleDistribution:
    def create_basic_pattern(self) -> CompiledSession:
        """4/4拍子、16小節のシンプルなパターン"""
        events = []

        # 16小節、各拍にキック
        for bar in range(16):
            for beat in range(4):
                step = bar * 16 + beat * 4
                events.append(Event(step=step, velocity=1.0))

        return CompiledSession(
            environment=Environment(bpm=120.0, loop_steps=256),
            tracks={
                "kick": Track(
                    meta=TrackMeta(track_id="kick"),
                    params=TrackParams(s="bd", gain=1.0)
                )
            },
            sequences={
                "kick": EventSequence.from_events("kick", events)
            }
        )
```

---

### 例2: 3/4拍子ワルツ（時間統一）

```python
class WaltzDistribution:
    STANDARD_BPM = 120.0

    def create_waltz_pattern(self) -> CompiledSession:
        """3/4拍子、21小節、32秒ループ"""
        # 計算
        beats_per_bar = 3
        steps_per_bar = 12  # 3 beats × 4 steps/beat
        num_bars = 21
        used_steps = 252

        events = []

        # 21小節のワルツ
        for bar in range(num_bars):
            for beat in range(beats_per_bar):
                step = bar * steps_per_bar + beat * 4
                velocity = 1.0 if beat == 0 else 0.7  # 強拍・弱拍
                events.append(Event(step=step, velocity=velocity))

        # steps 252-255は無音（自動的に）

        return CompiledSession(
            environment=Environment(bpm=self.STANDARD_BPM, loop_steps=256),
            tracks={
                "waltz": Track(
                    meta=TrackMeta(track_id="waltz"),
                    params=TrackParams(s="hihat", gain=0.8)
                )
            },
            sequences={
                "waltz": EventSequence.from_events("waltz", events)
            }
        )
```

---

### 例3: 三連譜（offset_ms使用）

```python
class TripletDistribution:
    def create_triplet_pattern(self, bpm: float = 120.0) -> CompiledSession:
        """8分音符3連符パターン"""
        # 1拍の長さ
        beat_duration_ms = 60000.0 / bpm  # 500ms @ 120 BPM
        triplet_interval = beat_duration_ms / 3  # 166.67ms

        events = []

        # 16小節、各拍で3連符
        for bar in range(16):
            for beat in range(4):
                beat_step = bar * 16 + beat * 4

                # 3連符
                for i in range(3):
                    events.append(Event(
                        step=beat_step,
                        offset_ms=i * triplet_interval,
                        velocity=1.0 if i == 0 else 0.8
                    ))

        return CompiledSession(
            environment=Environment(bpm=bpm, loop_steps=256),
            tracks={
                "triplets": Track(
                    meta=TrackMeta(track_id="triplets"),
                    params=TrackParams(s="hihat", gain=0.9)
                )
            },
            sequences={
                "triplets": EventSequence.from_events("triplets", events)
            }
        )
```

---

### 例4: ジャージークラブパターン（変則）

```python
class JerseyClubDistribution:
    def create_jersey_club_pattern(self) -> CompiledSession:
        """4×2 + 3×3 - 1 パターン"""
        events = []

        # 16小節のジャージークラブパターン
        for bar in range(16):
            bar_start = bar * 16

            # Section A: 4 steps × 2 beats = 8 steps
            for i in range(2):
                for j in range(4):
                    step = bar_start + i * 4 + j
                    events.append(Event(step=step, velocity=1.0))

            # Section B: 3 steps × 3 beats = 9 steps
            # 最後の1 stepは切り取り → 8 steps
            for i in range(3):
                for j in range(3):
                    if (i * 3 + j) < 8:  # 8 stepsまで
                        step = bar_start + 8 + i * 3 + j
                        events.append(Event(step=step, velocity=0.9))

        return CompiledSession(
            environment=Environment(bpm=130.0, loop_steps=256),
            tracks={
                "jersey": Track(
                    meta=TrackMeta(track_id="jersey"),
                    params=TrackParams(s="clap", gain=1.0)
                )
            },
            sequences={
                "jersey": EventSequence.from_events("jersey", events)
            }
        )
```

---

### 例5: 複合拍子（3/4 + 5/4）

```python
class CompoundMeterDistribution:
    def create_compound_pattern(self) -> CompiledSession:
        """3/4拍子8小節 + 5/4拍子8小節 = 256 steps"""
        events = []

        # Section A: 3/4拍子、8小節（steps 0-95）
        for bar in range(8):
            for beat in range(3):
                step = bar * 12 + beat * 4
                events.append(Event(step=step, velocity=1.0))

        # Section B: 5/4拍子、8小節（steps 96-255）
        for bar in range(8):
            for beat in range(5):
                step = 96 + bar * 20 + beat * 4
                events.append(Event(step=step, velocity=0.9))

        return CompiledSession(
            environment=Environment(bpm=120.0, loop_steps=256),
            tracks={
                "compound": Track(
                    meta=TrackMeta(track_id="compound"),
                    params=TrackParams(s="snare", gain=0.8)
                )
            },
            sequences={
                "compound": EventSequence.from_events("compound", events)
            }
        )
```

---

## 実装チェックリスト

### Oiduna Core側 (v1.0)

- [ ] Event.offset_msフィールド追加
- [ ] Event.to_dict/from_dict拡張
- [ ] StepProcessor.process_step_v2でoffset_ms処理
- [ ] OscSender/MidiSenderでタイミング制御
- [ ] テスト追加

### Oiduna Core側 (v1.1 新機能)

**Client Metadata共有機能**:
- [ ] ClientMetadataデータモデル追加
- [ ] SessionState.clientsストア実装
- [ ] REST API実装
  - [ ] `POST /session/clients/{client_id}/metadata`
  - [ ] `GET /session/clients`
  - [ ] `GET /session/clients/{client_id}`
  - [ ] `DELETE /session/clients/{client_id}`
- [ ] SSEイベント実装
  - [ ] `client_metadata_updated`
  - [ ] `client_connected`
  - [ ] `client_disconnected`
- [ ] client_id必須バリデーション
- [ ] テスト追加（API、SSE）
- [ ] ドキュメント更新

### Oiduna Core側 (v1.1 リファクタリング)

- [ ] Environment.scaleフィールドの削除
- [ ] Environment.chordsフィールドの削除
- [ ] Chordデータクラスの削除（未使用の場合）
- [ ] スケール関連の未使用コード削除
- [ ] コード進行関連の未使用コード削除
- [ ] to_dict/from_dictの更新
- [ ] テストの更新
- [ ] マイグレーションガイドの作成（Distribution開発者向け）

### Distribution側（開発者の責任）

**基本機能**:
- [ ] 音高解決機構（スケール・コード → MIDIノート番号）
- [ ] 拍子管理機構
- [ ] 256 stepフォーマット変換ロジック
- [ ] offset_ms計算ヘルパー
- [ ] DSL構文拡張（オプション）

**Client Metadata統合**:
- [ ] client_id設定機能
- [ ] メタデータ送信機能（標準フォーマット対応）
- [ ] メタデータ受信機能（他クライアント情報取得）
- [ ] SSE受信ハンドラ実装
- [ ] B2Bユースケース実装（コード進行同期等）
- [ ] ドキュメント作成

---

## バージョン履歴

### v1.1 (予定)

**新機能**:
- [ ] Client Metadata共有機能
  - REST API (`/session/clients/{client_id}/metadata`)
  - SSE統合 (`client_metadata_updated`イベント)
  - 標準メタデータフォーマット提案
  - Distribution間・クライアント間情報共有

**リファクタリング**:
- [ ] `Environment.scale`フィールドの削除
- [ ] `Environment.chords`フィールドの削除
- [ ] 関連する未使用コードの削除

**理由**:
- Oiduna Coreは音楽理論の概念を持たないシンプルなプレイヤー
- Distribution側で既にMIDIノート番号に解決済みのIRを受け取る
- スケール・コード進行等の音楽理論処理はDistribution側の責任
- 旧システム(MARS)との設計思想の違いを明確化
- **ただし**、Distribution間情報共有のハブとして機能（メタデータを保持するが理解しない）

**影響範囲**:
- Oiduna Core内部のみ（Distribution側への影響なし）
- IRデータモデルの簡素化
- 未使用フィールドの削除による保守性向上
- Client Metadata機能追加によるB2B対応強化

### v1.0 (2026-01-31)

- 初版リリース
- offset_ms仕様追加
- 変拍子実装パターン文書化
- 標準的・変則的な実装パターンの明確化

---

## 参考資料

### 関連ドキュメント

- `README.md` - Oiduna Coreプロジェクト概要
- `docs/architecture/GIL_MITIGATION.md` - GIL対策
- `oiduna_core/models/ir/` - IRデータモデル実装

### 外部参考

- TidalCycles: nudge パラメータ
- Ableton Live: groove機能
- ハードウェアシーケンサー: Roland TR-808, Elektron Octatrack

---

**END OF SPECIFICATION**
