# MIDI Parameters Reference

Oidunaは`params: dict[str, Any]`による柔軟なパラメータ設計を採用していますが、MIDI送信先向けには**MIDI規格チェック**のためのヘルパー機能を提供しています。

## 設計思想

- **送信先非依存**: paramsは`dict[str, Any]`のまま維持（柔軟性優先）
- **MIDI規格のみ**: 0-127範囲、14bit NRPN等の**プロトコル制約**のみチェック
- **音楽的意味は関与しない**: CC1が何を制御するかは送信先機器次第
- **オプション機能**: 使いたい人だけ使う（強制しない）

## 対応するMIDI機能

| 機能 | パラメータキー | 範囲 | 説明 |
|-----|-------------|------|------|
| ノート | `note` | 0-127 | MIDIノート番号（音高とは限らない） |
| ベロシティ | `velocity` | 0-127 | ベロシティ（音量とは限らない） |
| ノート長 | `duration_ms` | > 0 | ミリ秒単位のノート長 |
| チャンネル | `channel` | 0-15 | MIDIチャンネル |
| CC | `cc` | {0-127: 0-127} | Control Change（7bit） |
| NRPN | `nrpn` | {0-16383: 0-16383} | Non-Registered Parameter Number（14bit） |

## 使用方法

### 1. TypedDict（型ヒント専用）

IDE補完と型チェックのための型ヒント：

```python
from oiduna_models import Event, MidiParams

# IDE補完が効く！
params: MidiParams = {
    "note": 60,
    "velocity": 100,
    "duration_ms": 250,
    "channel": 0
}

event = Event(step=0, cycle=0.0, params=params)
```

### 2. バリデーション（オプション）

MIDI規格チェックが必要な場合：

```python
from oiduna_models import Event, validate_midi_params, MidiValidationError

params = {
    "note": 60,
    "velocity": 100
}

try:
    validate_midi_params(params)  # MIDI規格チェック
    event = Event(step=0, cycle=0.0, params=params)
except MidiValidationError as e:
    print(f"MIDI規格違反: {e}")
```

非例外版：

```python
from oiduna_models import is_valid_midi_params

if is_valid_midi_params(params):
    event = Event(step=0, cycle=0.0, params=params)
else:
    print("Invalid MIDI params")
```

## 実例

### 基本的なノート

```python
from oiduna_models import Event

event = Event(
    step=0,
    cycle=0.0,
    params={
        "note": 60,
        "velocity": 100,
        "duration_ms": 250
    }
)
```

### Control Change (CC)

```python
# CC辞書で複数のCCを送信
params = {
    "note": 60,
    "cc": {
        1: 64,    # CC1 (モジュレーション？送信先次第)
        7: 100,   # CC7 (ボリューム？送信先次第)
        10: 64    # CC10 (パン？送信先次第)
    }
}

event = Event(step=0, cycle=0.0, params=params)
```

**重要**: CCの音楽的な意味（CC1=モジュレーション等）は送信先機器に依存します。Oidunaは数値の範囲のみチェックします。

### NRPN (Non-Registered Parameter Number)

```python
# 14bit高解像度パラメータ
params = {
    "note": 60,
    "nrpn": {
        256: 8192,   # NRPN #256に値8192を設定
        100: 16383   # NRPN #100に値16383を設定（最大値）
    }
}

event = Event(step=0, cycle=0.0, params=params)
```

**NRPN範囲**:
- パラメータ番号: 0-16383 (14bit)
- 値: 0-16383 (14bit)

### MIDIミキサーへの送信例

```python
# 例: YAMAHAデジタルミキサーのフェーダー制御
# （CC番号は機器のマニュアル参照）

# Ch1フェーダー（仮にCC14とする）
params = {
    "channel": 0,
    "cc": {14: 100}  # 0-127
}

# NRPNで高解像度制御（仮にNRPN #1がフェーダーとする）
params = {
    "channel": 0,
    "nrpn": {1: 12288}  # 0-16383の高解像度
}
```

## バリデーションエラー例

```python
from oiduna_models import validate_midi_params, MidiValidationError

# ❌ ノート番号が範囲外
try:
    validate_midi_params({"note": 200})
except MidiValidationError as e:
    print(e)  # "MIDI note must be 0-127, got 200"

# ❌ チャンネルが範囲外
try:
    validate_midi_params({"channel": 16})
except MidiValidationError as e:
    print(e)  # "MIDI channel must be 0-15, got 16"

# ❌ CC番号が範囲外
try:
    validate_midi_params({"cc": {200: 64}})
except MidiValidationError as e:
    print(e)  # "MIDI CC number must be 0-127, got 200"

# ❌ NRPN値が範囲外
try:
    validate_midi_params({"nrpn": {256: 20000}})
except MidiValidationError as e:
    print(e)  # "MIDI NRPN value must be 0-16383 (14-bit), got 20000"
```

## 柔軟性の維持

### 未知のパラメータは無視される

```python
params = {
    "note": 60,
    "custom_param": "anything",  # 未知のパラメータ
    "my_filter": 0.8             # 送信先固有のパラメータ
}

validate_midi_params(params)  # エラーなし
# → MIDI規格パラメータ（note, velocity等）のみチェック
# → 未知のパラメータはスルー（柔軟性維持）
```

### dict[str, Any]のまま

```python
# TypedDictは型ヒント専用
# 実際のparamsは依然としてdict[str, Any]
event = Event(
    step=0,
    cycle=0.0,
    params={"note": 60, "anything": "goes"}  # 自由に追加可能
)
```

## テストでの使用例

```python
import pytest
from oiduna_models import Event, validate_midi_params, MidiValidationError

def test_midi_event_creation():
    """MIDI eventの作成とバリデーション."""
    params = {
        "note": 60,
        "velocity": 100,
        "duration_ms": 250
    }

    # MIDI規格チェック
    validate_midi_params(params)

    # Event作成
    event = Event(step=0, cycle=0.0, params=params)

    assert event.params["note"] == 60
    assert event.params["velocity"] == 100

def test_invalid_midi_note():
    """不正なMIDIノート番号のテスト."""
    params = {"note": 200}

    with pytest.raises(MidiValidationError):
        validate_midi_params(params)
```

## まとめ

| 機能 | 用途 | 必須？ |
|-----|------|-------|
| `MidiParams` | IDE補完、型チェック | オプション |
| `validate_midi_params()` | MIDI規格チェック | オプション |
| `is_valid_midi_params()` | 非例外版チェック | オプション |

**重要ポイント**:
- ✅ `params: dict[str, Any]`の柔軟性は維持
- ✅ MIDI規格（0-127等）のみチェック
- ✅ 音楽的な意味づけは送信先依存
- ✅ 使いたい人だけ使う（オプトイン）
- ✅ 未知のパラメータは無視（柔軟性）

---

**関連ドキュメント**:
- [データモデルリファレンス](./DATA_MODEL_REFERENCE.md) - paramsの基本概念
- [Layer 5: データ層](./architecture/layer-5-data.md) - Event, Track, Patternの詳細
