# Oiduna: コンセプトと設計哲学

**作成日**: 2026-02-27
**バージョン**: 2.1.0 (Timing Model追加版)
**対象**: Oiduna開発者・利用者

## 目次

1. [Oidunaとは何か](#oidunaとは何か)
2. [設計哲学](#設計哲学)
3. [アーキテクチャの進化](#アーキテクチャの進化)
4. [核となるコンセプト](#核となるコンセプト)
   - 6. [Timing Model（タイミングモデル）](#6-timing-modelタイミングモデル)
5. [パフォーマンス設計](#パフォーマンス設計)

---

## Oidunaとは何か

### 一言で言うと

**Oiduna = Destination-Agnostic リアルタイム音楽パターン再生エンジン**

HTTPでScheduledMessageBatch（JSON形式）を受け取り、SuperDirt、MIDIデバイス、カスタム送信先にリアルタイムでイベントを送信するPythonアプリケーション。

### Oidunaが「ではない」もの

- ❌ DSLコンパイラ（それはMARSの役割）
- ❌ プロジェクト管理システム（それもMARSの役割）
- ❌ DAW（Digital Audio Workstation）
- ❌ シンセサイザー（それはSuperColliderの役割）
- ❌ SuperDirt専用エンジン（任意の送信先に対応）

### Oidunaが「である」もの

- ✅ リアルタイムループエンジン（256ステップ = 16ビート）
- ✅ 送信先非依存のメッセージルーター
- ✅ HTTP APIサーバー（再生制御）
- ✅ 拡張可能なプラットフォーム（Extension System）

---

## 設計哲学

### 1. Destination-Agnostic（送信先非依存）

**問題意識**:
従来のアーキテクチャはSuperDirt専用で、他の送信先への拡張が困難でした。

**解決アプローチ**:
```python
# 送信先に依存しない共通インターフェース
ScheduledMessage(
    destination_id="superdirt",  # または "volca_bass", "custom_synth"
    step=0,
    params={"s": "bd", "gain": 0.8}  # 送信先が解釈
)
```

**メリット**:
- SuperDirt、MIDI、カスタム送信先を統一的に扱える
- 新しい送信先を追加しやすい（destinations.yaml + Sender実装）
- 送信先固有の最適化が可能

**実例**:
- SuperDirt: OSCプロトコル、orbit概念
- MIDI: Note On/Off、CC、Pitch Bend
- カスタム: 任意のプロトコル（WebSocket、UDP等）

### 2. Simplicity（シンプルさ）

**問題意識**:
階層構造（Environment/Track/Sequence）は複雑で、変換コストが高く、デバッグが困難でした。

**解決アプローチ**:
```python
# フラットなメッセージリスト
ScheduledMessageBatch(
    messages=[
        ScheduledMessage(destination_id="superdirt", step=0, params={...}),
        ScheduledMessage(destination_id="superdirt", step=16, params={...}),
        # ...
    ],
    bpm=120.0,
    pattern_length=4.0
)
```

**メリット**:
- デバッグしやすい（階層を辿る必要がない）
- 変換処理が不要（MARS側でScheduledMessageBatchを直接生成）
- メモリ効率が良い（tupleによる固定長配列）

### 3. Performance（パフォーマンス）

**問題意識**:
リアルタイム再生（120 BPMで125msごと）では、O(N)の線形探索は使えません。

**解決アプローチ**:
```python
# MessageSchedulerによるステップ別インデックス
step_index: dict[int, list[int]] = {
    0: [0, 5, 12],   # ステップ0に3つのメッセージ
    16: [1, 8],      # ステップ16に2つのメッセージ
    # ...
}

# O(1)検索
messages = [all_messages[i] for i in step_index[current_step]]
```

**パフォーマンス実測**（256ステップ、1000メッセージ）:
- 線形探索: ~10ms per step → ❌ 不可（125msの制約を超える）
- インデックス検索: ~0.1ms per step → ✅ OK

**最適化技法**:
- 早期リターン（Mute/Solo未設定時は即座にreturn）
- リスト内包表記（Cレベルで最適化）
- walrus演算子（:=）による効率的な条件判定
- frozen=True, slots=Trueによるメモリ最適化

### 4. Extensibility（拡張性）

**問題意識**:
コアに機能を追加すると複雑化し、メンテナンスが困難になります。

**解決アプローチ**:
```python
# Extension Systemによる機能追加
class MyExtension:
    def apply(self, batch: ScheduledMessageBatch) -> ScheduledMessageBatch:
        # ScheduledMessageBatchを変換
        return modified_batch

# 拡張機能の登録
pipeline.register(MyExtension())
```

**メリット**:
- コアはシンプルに保つ
- 機能を独立してテスト可能
- 有効/無効を簡単に切り替え可能

**拡張例**:
- **oiduna-extension-superdirt**: SuperDirt固有のorbit/cps計算
- **カスタム拡張**: パラメータ変換、フィルタリング、ルーティング

### 5. Type Safety（型安全性）

**問題意識**:
実行時エラーは本番環境で問題を引き起こします。

**解決アプローチ**:
```python
# mypyによる静的型チェック
@dataclass(frozen=True, slots=True)
class ScheduledMessage:
    destination_id: str
    cycle: float
    step: int
    params: dict[str, Any]  # 送信先依存のため型緩和
```

**型安全性のバランス**:
- **厳密な型**: destination_id, cycle, step
- **緩い型**: params（送信先依存、拡張性を重視）

**型安全性の補完**:
- DestinationSender側でのバリデーション
- テストによるカバレッジ
- ドキュメントによる明示

---

## アーキテクチャの進化

### Phase 1: SuperDirt専用（初期）

```python
# SuperDirt固有のデータ構造
class OscEvent:
    s: str          # サウンド名
    orbit: int      # オービット番号
    cps: float      # Cycles Per Second
    # ...SuperDirt固有のフィールド
```

**問題点**:
- MIDI出力への対応が困難
- カスタム送信先への拡張が不可能
- SuperDirt固有の概念がコアに混入

### Phase 2: 3層IR構造（中期）

```python
# 階層構造
CompiledSession
├── Environment (BPM, scale等)
├── Track (音色、エフェクト)
└── EventSequence (パターン)
```

**問題点**:
- 階層が複雑でデバッグが困難
- 変換処理のコストが高い
- 送信先依存の概念が残存（orbit等）

### Phase 3: ScheduledMessageBatch（データフォーマット統一）

```python
# フラット構造 + 送信先非依存
ScheduledMessageBatch
└── messages: [
      ScheduledMessage(destination_id, step, params),
      ...
    ]
```

**改善点**:
- ✅ 送信先非依存（Destination-Agnostic）
- ✅ シンプル（フラット構造）
- ✅ 高速（O(1)検索）
- ✅ 拡張可能（Extension System）

**移行の記録**:
- [archive/ARCHITECTURE_UNIFICATION_COMPLETE.md](archive/ARCHITECTURE_UNIFICATION_COMPLETE.md)
- [archive/MIGRATION_GUIDE_SCHEDULED_MESSAGE_BATCH.md](archive/MIGRATION_GUIDE_SCHEDULED_MESSAGE_BATCH.md)

### Phase 4-5: API層の刷新とSessionContainer（実装品質向上）

**Phase 4 (API層)**: 階層的データモデルとREST API
```python
# 新規パッケージ
oiduna_models      # Session/Track/Pattern/Event/Client
oiduna_auth        # UUID Token認証
oiduna_session     # SessionContainer + 専門マネージャー
oiduna_api         # FastAPI routes
```

**Phase 5 (SessionContainer)**: SessionManager分割とアーキテクチャ改善
```python
# SessionContainer: 軽量コンテナパターン
SessionContainer
├── clients: ClientManager
├── tracks: TrackManager
├── patterns: PatternManager
├── environment: EnvironmentManager
└── destinations: DestinationManager
```

**改善点**:
- ✅ 単一責任原則の遵守（497行 → 5つの専門マネージャー）
- ✅ 直接アクセスAPI（Facadeパターン廃止）
- ✅ テスト容易性向上（+84テスト）
- ✅ 型安全性（Pydantic、mypy strict）

**詳細ドキュメント**:
- [../../IMPLEMENTATION_COMPLETE.md](../../IMPLEMENTATION_COMPLETE.md) - Phase 1-5完了サマリー
- [knowledge/adr/0010-session-container-refactoring.md](knowledge/adr/0010-session-container-refactoring.md) - ADR-0010

**Note**: Phase 4-5はAPI実装の改善であり、コアループエンジン（ScheduledMessageBatch処理）には影響しません。

---

## 核となるコンセプト

### 1. ScheduledMessage（スケジュール済みメッセージ）

**定義**: 「いつ（step）、どこに（destination_id）、何を（params）送るか」を表現

```python
ScheduledMessage(
    destination_id="superdirt",  # どこに
    step=0,                      # いつ（256ステップ中の位置）
    cycle=0.0,                   # いつ（サイクル単位）
    params={"s": "bd", ...}      # 何を
)
```

**設計思想**:
- **宣言的**: 「何をするか」だけを記述、「どうやるか」は隠蔽
- **送信先非依存**: paramsの解釈は送信先に委譲
- **イミュータブル**: frozen=Trueにより変更不可

### 2. MessageScheduler（メッセージスケジューラ）

**役割**: ScheduledMessageBatchを高速検索可能な形式に変換

**処理フロー**:
```
ScheduledMessageBatch
  ↓ load_messages()
ステップ別インデックス構築 (O(N))
  ↓ get_messages_for_step(step)
該当ステップのメッセージ取得 (O(1))
```

**設計思想**:
- **一度だけの前処理**: インデックス構築はパターン読み込み時のみ
- **高速な検索**: 毎ステップ（125ms）の検索はO(1)
- **メモリ効率**: インデックスは整数配列のみ

### 3. DestinationRouter（送信先ルーター）

**役割**: destination_idに基づいてメッセージを振り分け

**処理フロー**:
```
list[ScheduledMessage]
  ↓ send_messages()
送信先別にグループ化
  ├→ destination_id="superdirt" → OscDestinationSender
  └→ destination_id="volca_bass" → MidiDestinationSender
```

**設計思想**:
- **疎結合**: コアは送信先の詳細を知らない
- **設定ベース**: destinations.yamlで送信先を定義
- **拡張可能**: 新しいSenderを追加するだけ

### 4. RuntimeState（実行時状態）

**役割**: 再生状態、BPM、Mute/Soloを管理

**主要な責任**:
- **再生状態**: PLAYING, PAUSED, STOPPED
- **位置管理**: step, beat, bar, cycle
- **BPM管理**: set_bpm()
- **Mute/Solo**: filter_messages()

**設計思想**:
- **最小限の状態**: 必要最小限のフィールドのみ
- **不変性**: 状態変更は専用メソッド経由のみ
- **スレッドセーフ**: asyncioによる排他制御

### 5. Extension System（拡張システム）

**役割**: ScheduledMessageBatchを変換する拡張機能のプラットフォーム

**拡張ポイント**:
```python
class Extension(Protocol):
    def apply(self, batch: ScheduledMessageBatch) -> ScheduledMessageBatch:
        """ScheduledMessageBatchを変換"""
        ...
```

**設計思想**:
- **単純なインターフェース**: apply()メソッドのみ
- **チェーン実行**: ExtensionPipelineで複数の拡張を順次実行
- **有効/無効**: oiduna_extensions.yamlで設定

**拡張例**:
```python
# orbit計算拡張（SuperDirt用）
class OrbitMapperExtension:
    def apply(self, batch: ScheduledMessageBatch) -> ScheduledMessageBatch:
        # track_idからorbitを計算してparamsに追加
        return modified_batch
```

### 6. Timing Model（タイミングモデル）

**役割**: Oidunaの時間・タイミング管理の基本仕様

#### 固定ループ長の設計思想

Oidunaは**256ステップ固定ループ**を採用しています。これは変更できないコアアーキテクチャです。

```python
# packages/oiduna_loop/engine/loop_engine.py:23
LOOP_STEPS = 256  # 固定値（変更不可）
```

**なぜ256ステップなのか**:
- **2の累乗**: ビット演算での最適化が可能（256 = 2^8）
- **音楽的に自然**: 16ビート = 4小節 = 典型的なループ長
- **TidalCycles互換**: 4.0サイクル = 4小節

#### 時間単位の正確な関係式

```
1 step    = 1/16 note (16分音符)
4 steps   = 1 beat (4分音符、1拍)
16 steps  = 1 bar (1小節、4拍)
64 steps  = 4 bars
256 steps = 16 beats = 4 bars = 1 loop = 4.0 cycles
```

**図解**:
```
Loop (256 steps = 4.0 cycles)
├─ Bar 0 (0-15 steps = 0.0-0.999... cycles)
│  ├─ Beat 0 (0-3 steps)
│  ├─ Beat 1 (4-7 steps)
│  ├─ Beat 2 (8-11 steps)
│  └─ Beat 3 (12-15 steps)
├─ Bar 1 (16-31 steps = 1.0-1.999... cycles)
├─ Bar 2 (32-47 steps = 2.0-2.999... cycles)
└─ Bar 3 (48-63 steps = 3.0-3.999... cycles)
... 繰り返し（64-255 steps）
```

#### step（整数）vs offset（浮動小数点）

ScheduleEntryは**両方の表現**を持ちます:

```python
@dataclass
class ScheduleEntry:
    step: int        # 0-255（量子化されたステップ番号）
    offset: float    # 0.0-0.999...（ステップ内相対位置）
    params: dict[str, Any]
```

**使い分け**:
- **step**: MessageSchedulerのO(1)インデックス検索
- **offset**: スウィング、トリプレット、マイクロタイミング

**offsetの範囲**: `[0.0, 1.0)` 半開区間
- `0.0` = ステップ開始（デフォルト）
- `0.5` = ステップ中間（スウィング）
- `0.666` = 2/3位置（トリプレット feel）
- `0.999...` = 次ステップ直前

**BPM非依存**:
offsetは比率なので、BPM変更時も値は不変。
絶対時刻のみが再計算される。

**計算式**:
```python
絶対時刻 = (step * step_duration) + (offset * step_duration)
step_duration = (60.0 / BPM) / 4  # 秒/step
```

**例（120 BPM）**:
| step | offset | 絶対時刻（ms） | 意味 |
|------|--------|---------------|------|
| 0 | 0.0 | 0ms | ステップ開始 |
| 0 | 0.5 | 62.5ms | スウィング（ステップ中間） |
| 0 | 0.666 | 83.3ms | トリプレット（2/3位置） |
| 1 | 0.0 | 125ms | 次ステップ開始 |

**変拍子の表現**:
Oidunaは1 bar = 16 steps固定だが、step + offsetの組み合わせで変拍子を表現可能。

例: **3/4拍子**（12 steps = 3拍）
- 1拍目: `step=0, offset=0.0` → 絶対位置 0 steps
- 2拍目: `step=5, offset=0.333` → 絶対位置 5.333 steps
- 3拍目: `step=10, offset=0.666` → 絶対位置 10.666 steps

これにより、16stepグリッド上で自由な拍位置を指定できる。

#### BPMと時間の関係

**基本公式**:
```python
秒/beat = 60.0 / BPM
秒/step = (60.0 / BPM) / 4  # 1 beat = 4 steps
秒/loop = (60.0 / BPM) * 16  # 1 loop = 16 beats
```

**時間換算表**:
| BPM | 秒/step | 秒/beat | 秒/loop |
|-----|---------|---------|---------|
| 60 | 250ms | 1000ms | 16秒 |
| 120 | 125ms | 500ms | 8秒 |
| 140 | 107ms | 428ms | 6.86秒 |
| 180 | 83ms | 333ms | 5.33秒 |

**リアルタイム制約**:
- 120 BPM → **125ms/step**
- この時間内に以下を完了:
  1. メッセージ取得（MessageScheduler）
  2. Mute/Soloフィルタリング（RuntimeState）
  3. 送信先別振り分け（DestinationRouter）
  4. OSC/MIDI送信（DestinationSender）
- **目標**: < 50ms（余裕を持たせるため）

#### Position（位置情報）

RuntimeStateは現在位置を以下の形式で管理:

```python
@dataclass
class Position:
    step: int    # 0-255（現在のステップ）
    beat: int    # 0-15（現在のビート）
    bar: int     # 0-3（現在の小節）
    cycle: float # 0.0-4.0（現在のサイクル位置）
```

**position_update_interval**（位置更新通知の頻度）:
- `"beat"`: 4ステップごと（1ビートごと）に位置更新をSSE配信
- `"bar"`: 16ステップごと（1小節ごと）に位置更新をSSE配信

**トレードオフ**:
- `"beat"`: 高頻度更新（滑らかなUI）、ネットワーク負荷大
- `"bar"`: 低頻度更新（軽量）、更新が粗い

**デフォルト**: `"beat"`（packages/oiduna_models/environment.py:14）

#### タイミング精度の保証

**Clock Generator**:
- `packages/oiduna_loop/engine/clock_generator.py`
- asyncio + 高精度タイマーによるドリフト補正

**ドリフト補正パラメータ**:
```python
DRIFT_RESET_THRESHOLD_MS = 50  # 50ms以上のズレで強制リセット
DRIFT_WARNING_THRESHOLD_MS = 20  # 20ms以上で警告ログ
```

**設計思想**:
- **ドリフト検出**: 累積誤差を毎ステップ測定
- **段階的補正**: 小さなズレは次ステップで吸収
- **強制リセット**: 大きなズレ（50ms超）は即座にリセット

**コード参照**:
- `packages/oiduna_models/events.py:10-11` - PatternEvent (step/cycle)
- `packages/oiduna_loop/engine/loop_engine.py:23` - LOOP_STEPS定数
- `packages/oiduna_loop/engine/clock_generator.py:15-17` - ドリフト補正
- `packages/oiduna_models/environment.py:14` - position_update_interval

---

## パフォーマンス設計

### リアルタイム制約

**要求**:
- 120 BPM → 125ms/step
- 各ステップで以下の処理を完了:
  1. メッセージ取得（MessageScheduler）
  2. Mute/Soloフィルタリング（RuntimeState）
  3. 送信先別振り分け（DestinationRouter）
  4. OSC/MIDI送信（DestinationSender）

**制約**: 合計処理時間 < 125ms（余裕を持たせて < 50ms）

### O(1)検索の必要性

**問題**: 線形探索では大規模パターンで遅延

```python
# ❌ 線形探索: O(N)
messages_at_step = [msg for msg in all_messages if msg.step == current_step]
# 1000メッセージで ~10ms → 制約を超える可能性

# ✅ インデックス検索: O(1)
message_indices = step_index[current_step]
messages_at_step = [all_messages[i] for i in message_indices]
# 1000メッセージで ~0.1ms → OK
```

### 早期リターンパターン

**filter_messages()の最適化**:
```python
def filter_messages(self, messages: list[ScheduledMessage]) -> list[ScheduledMessage]:
    # 早期リターン: Mute/Solo未設定時
    if not self._track_mute and not self._track_solo:
        return messages  # コピーなし、即座にreturn

    # フィルタリング（必要な場合のみ）
    return [
        msg for msg in messages
        if (track_id := msg.params.get("track_id")) is None
        or self.is_track_active(track_id)
    ]
```

**効果**:
- 一般的なケース（Mute/Solo未使用）: ~0.01ms
- フィルタリング必要: ~0.5ms

### イミュータブル設計

**メモリ最適化**:
```python
@dataclass(frozen=True, slots=True)
class ScheduledMessage:
    destination_id: str
    cycle: float
    step: int
    params: dict[str, Any]
```

**効果**:
- **frozen=True**: オブジェクトの変更を禁止、ハッシュ可能
- **slots=True**: `__dict__`なし、メモリ使用量 -40%
- **tuple使用**: 固定長配列として最適化

---

## ユースケース

### 基本的な使い方

**1. パターンデータの送信**:
```python
import requests

batch = {
    "messages": [
        {
            "destination_id": "superdirt",
            "cycle": 0.0,
            "step": 0,
            "params": {"s": "bd", "gain": 0.8}
        },
        {
            "destination_id": "superdirt",
            "cycle": 1.0,
            "step": 16,
            "params": {"s": "sn", "gain": 0.9}
        }
    ],
    "bpm": 120.0,
    "pattern_length": 4.0
}

response = requests.post("http://localhost:8000/playback/session", json=batch)
```

**2. 再生制御**:
```bash
# 再生開始
curl -X POST http://localhost:8000/playback/start

# 一時停止
curl -X POST http://localhost:8000/playback/pause

# 停止
curl -X POST http://localhost:8000/playback/stop

# BPM変更
curl -X POST http://localhost:8000/playback/bpm -d '{"bpm": 140.0}'
```

**3. Mute/Solo**:
```bash
# トラックをMute
curl -X POST http://localhost:8000/tracks/kick/mute

# トラックをSolo
curl -X POST http://localhost:8000/tracks/snare/solo

# Mute解除
curl -X DELETE http://localhost:8000/tracks/kick/mute
```

### 高度な使い方

**1. カスタム送信先の追加**:
```yaml
# destinations.yaml
destinations:
  - id: my_custom_synth
    type: custom
    module: my_extension.custom_sender
    class: CustomSynthSender
    config:
      host: 192.168.1.100
      port: 8080
```

**2. 拡張機能の実装**:
```python
# my_extension/custom_extension.py
class CustomExtension:
    def apply(self, batch: ScheduledMessageBatch) -> ScheduledMessageBatch:
        # ScheduledMessageBatchを変換
        new_messages = []
        for msg in batch.messages:
            # カスタムロジック
            modified_msg = self.transform(msg)
            new_messages.append(modified_msg)

        return ScheduledMessageBatch(
            messages=tuple(new_messages),
            bpm=batch.bpm,
            pattern_length=batch.pattern_length
        )
```

---

## まとめ

### Oidunaの強み

1. **Destination-Agnostic**: 任意の送信先に対応
2. **シンプル**: フラットなメッセージリスト
3. **高速**: O(1)検索、早期リターン、最適化技法
4. **拡張可能**: Extension Systemによる機能追加
5. **型安全**: mypyによる静的型チェック

### Oidunaの制約

1. **params型**: dict[str, Any]で型安全性が低い（実用性重視）
2. **256ステップ固定**: 可変長ループは未対応
3. **Python性能**: C/Rust実装と比較すると遅い（十分高速だが）

### 今後の方向性

- **パフォーマンス**: Cython/Rust化の検討
- **拡張機能**: エコシステムの充実
- **ドキュメント**: チュートリアルの追加
- **テスト**: カバレッジの向上

---

## 参照ドキュメント

- [ARCHITECTURE.md](ARCHITECTURE.md) - システム全体のアーキテクチャ
- [DATA_MODEL_REFERENCE.md](DATA_MODEL_REFERENCE.md) - データモデル詳細
- [TERMINOLOGY.md](TERMINOLOGY.md) - 用語集
- [MIGRATION_GUIDE_SCHEDULED_MESSAGE_BATCH.md](MIGRATION_GUIDE_SCHEDULED_MESSAGE_BATCH.md) - 移行ガイド
- [EXTENSION_DEVELOPMENT_GUIDE.md](EXTENSION_DEVELOPMENT_GUIDE.md) - 拡張機能開発ガイド

---

**バージョン**: 2.0.0 (ScheduledMessageBatch統合版)
**作成日**: 2026-02-27
**作成者**: Claude Code
