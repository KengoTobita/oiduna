# Migration Guide: Terminology Cleanup (2026-03)

このガイドは、2026年3月に実施した用語整理・型強化に伴う破壊的変更の移行手順を説明します。

## 概要

今回の変更は、コードベース全体の用語統一と型安全性の向上を目的としています。
ユーザーコードに影響する**2つの破壊的変更**があります。

### 変更サマリー

| カテゴリ | 変更内容 | 影響範囲 | 破壊的 |
|---------|---------|---------|-------|
| イベント用語 | `SessionEvent` → `SessionChange` | Session layer | ✅ Yes |
| Manager API | `list()` → `list_clients()` / `list_tracks()` / `list_patterns()` | Session layer | ✅ Yes |
| 型定義 | `timing.py`新規追加 | Models layer | ❌ No (新機能) |
| 型定義 | `params.py`新規追加 | Models layer | ❌ No (新機能) |
| ドキュメント | SSE Event用語の明確化 | API layer | ❌ No (clarification) |

---

## 1. SessionEvent → SessionChange

### 変更理由

- **用語の混乱を解消**: 3種類の"Event"が存在し、混乱を招いていました
  - `PatternEvent`: 音楽的タイミングイベント（ドメインモデル）
  - `SessionEvent`: CRUD変更通知（セッション層） ← **SessionChangeに変更**
  - `SSE Event`: HTTP Server-Sent Eventsプロトコル（API層）

- **意味の明確化**: CRUD操作による「変更通知」であることを明示

### 影響を受けるコード

#### Protocol名の変更

**変更前:**
```python
from oiduna_session.managers.base import SessionEventPublisher

class MyPublisher:
    def __init__(self):
        self.publisher: SessionEventPublisher = ...
```

**変更後:**
```python
from oiduna_session.managers.base import SessionChangePublisher

class MyPublisher:
    def __init__(self):
        self.publisher: SessionChangePublisher = ...
```

#### メソッド名の変更

**変更前:**
```python
# BaseManager内部
self._emit_event("track_created", {...})
```

**変更後:**
```python
# BaseManager内部
self._emit_change("track_created", {...})
```

#### テストコードの変更

**変更前:**
```python
class MockSessionEventPublisher:
    def __init__(self):
        self.events = []

    def publish(self, event: dict) -> None:
        self.events.append(event)
```

**変更後:**
```python
class MockSessionChangePublisher:
    def __init__(self):
        self.changes = []

    def publish(self, change: dict) -> None:
        self.changes.append(change)
```

### 移行手順

1. **検索・置換**を実行:
   ```bash
   # Protocol名
   find . -type f -name "*.py" -exec sed -i 's/SessionEventPublisher/SessionChangePublisher/g' {} +

   # 変数名・メソッド名
   find . -type f -name "*.py" -exec sed -i 's/_emit_event/_emit_change/g' {} +
   find . -type f -name "*.py" -exec sed -i 's/\.events/.changes/g' {} +
   ```

2. **インポート文**を更新:
   ```python
   # 変更前
   from oiduna_session.managers.base import SessionEventPublisher

   # 変更後
   from oiduna_session.managers.base import SessionChangePublisher
   ```

3. **テスト実行**で動作確認:
   ```bash
   uv run pytest packages/oiduna_session/tests/
   ```

---

## 2. Manager API: list() → list_clients() / list_tracks() / list_patterns()

### 変更理由

- **組み込み型との競合を回避**: `list`という名前が組み込み型`list[T]`と競合し、型チェックでエラーが発生
- **可読性の向上**: メソッド名から何をリストするのか明確に

### 影響を受けるコード

#### ClientManager

**変更前:**
```python
clients = container.clients.list()
```

**変更後:**
```python
clients = container.clients.list_clients()
```

#### TrackManager

**変更前:**
```python
tracks = container.tracks.list()
```

**変更後:**
```python
tracks = container.tracks.list_tracks()
```

#### PatternManager

**変更前:**
```python
patterns = container.patterns.list(track_id="abcd", include_archived=False)
```

**変更後:**
```python
patterns = container.patterns.list_patterns(track_id="abcd", include_archived=False)
```

### 移行手順

1. **検索・置換**を実行:
   ```bash
   # ClientManager
   find . -type f -name "*.py" -exec sed -i 's/\.clients\.list()/\.clients\.list_clients()/g' {} +

   # TrackManager
   find . -type f -name "*.py" -exec sed -i 's/\.tracks\.list()/\.tracks\.list_tracks()/g' {} +

   # PatternManager (注意: 引数がある場合もあるので慎重に)
   find . -type f -name "*.py" -exec sed -i 's/\.patterns\.list(/\.patterns\.list_patterns(/g' {} +
   ```

2. **API エンドポイント**も影響を受ける場合は更新:
   - `packages/oiduna_api/routes/tracks.py`
   - `packages/oiduna_api/routes/patterns.py`
   - `packages/oiduna_api/routes/auth.py`
   - `packages/oiduna_api/routes/session.py`
   - `packages/oiduna_api/dependencies.py`

3. **テスト実行**で動作確認:
   ```bash
   uv run pytest packages/oiduna_session/tests/
   uv run pytest packages/oiduna_api/tests/
   ```

---

## 3. 新機能: timing.py (型安全なタイミング単位)

### 概要

タイミング関連の型定義とユーティリティ関数を提供する新モジュール。

### 提供される型

```python
from oiduna_models import (
    StepNumber,     # 0-255 (256-step loop)
    BeatNumber,     # 0-15 (16 beats per loop)
    BarNumber,      # 0-3 (4 bars per loop)
    CycleFloat,     # 0.0-4.0 (Tidal Cycles互換)
    BPM,            # 20-999
    Milliseconds,   # タイムスタンプ用
)
```

### 変換ユーティリティ

```python
from oiduna_models import (
    step_to_cycle,          # StepNumber → CycleFloat
    cycle_to_step,          # CycleFloat → StepNumber
    step_to_beat,           # StepNumber → BeatNumber
    step_to_bar,            # StepNumber → BarNumber
    bpm_to_step_duration_ms,    # BPM → 1ステップのミリ秒
    bpm_to_loop_duration_ms,    # BPM → 1ループのミリ秒
)
```

### 使用例

```python
from oiduna_models import StepNumber, BPM, step_to_cycle, bpm_to_step_duration_ms

# 型安全なステップ定義
current_step: StepNumber = StepNumber(128)
cycle_pos: CycleFloat = step_to_cycle(current_step)  # 2.0

# BPMからタイミング計算
tempo: BPM = BPM(120)
step_ms: Milliseconds = bpm_to_step_duration_ms(tempo)  # 125ms
```

### 移行の必要性

この変更は**新機能**であり、既存コードの変更は不要です。
型安全性を向上させたい場合に、任意で導入してください。

---

## 4. 新機能: params.py (DestinationParams型定義)

### 概要

Destination固有のパラメータ型定義を提供する新モジュール。

### 提供される型

```python
from oiduna_models import (
    SuperDirtParams,    # SuperDirt/TidalCycles パラメータ
    SimpleMidiParams,   # MIDI パラメータ（フラット構造）
    DestinationParams,  # Union型（SuperDirt | SimpleMidi | dict）
)
```

### SuperDirtParams 使用例

```python
from oiduna_models import SuperDirtParams

kick: SuperDirtParams = {
    "s": "bd",
    "n": 0,
    "gain": 0.9,
    "pan": 0.5,
    "room": 0.1,
    "orbit": 0,
}
```

### SimpleMidiParams 使用例

```python
from oiduna_models import SimpleMidiParams

# Note On
note_params: SimpleMidiParams = {
    "note": 60,
    "velocity": 100,
    "duration_ms": 250,
    "channel": 0,
}

# Control Change
cc_params: SimpleMidiParams = {
    "cc": 74,
    "value": 127,
    "channel": 0,
}
```

### 既存のMidiParamsとの違い

| 型 | 場所 | 用途 | 構造 |
|----|------|------|------|
| `MidiParams` | `midi_helpers.py` | プロトコル検証 | `cc: dict[int, int]` (ネスト) |
| `SimpleMidiParams` | `params.py` | 型ヒント・補完 | `cc: int, value: int` (フラット) |

### 移行の必要性

この変更は**新機能**であり、既存コードの変更は不要です。
エディタの型補完を活用したい場合に、任意で導入してください。

---

## 5. SSE Event用語の明確化

### 変更内容

`packages/oiduna_api/routes/stream.py`のdocstringを拡充し、3種類の"Event"の違いを明確化しました。

### 用語の整理

| 用語 | レイヤー | 意味 |
|------|---------|------|
| **PatternEvent** | Domain (Models) | 音楽的タイミングイベント（step, params） |
| **SessionChange** | Session | CRUD変更通知（track_created等） |
| **SSE Event** | API | HTTP Server-Sent Eventsプロトコル |

### 影響

ドキュメントの明確化のみで、コード変更は不要です。

---

## テスト実行

全ての移行が完了したら、テストを実行して動作確認してください。

```bash
# 全パッケージのテスト
uv run pytest packages/ tests/ -v

# 型チェック
uv run mypy packages/oiduna_models packages/oiduna_session packages/oiduna_api

# カバレッジ確認
uv run pytest packages/ --cov=packages --cov-report=term-missing
```

---

## トラブルシューティング

### Q: SessionEventPublisher が見つからない

**A:** `SessionChangePublisher`に名前が変更されました。

```python
# ❌ 旧
from oiduna_session.managers.base import SessionEventPublisher

# ✅ 新
from oiduna_session.managers.base import SessionChangePublisher
```

### Q: clients.list() が AttributeError

**A:** メソッド名が`list_clients()`に変更されました。

```python
# ❌ 旧
clients = container.clients.list()

# ✅ 新
clients = container.clients.list_clients()
```

### Q: MidiParams が2つあって混乱

**A:** 用途に応じて使い分けてください。

- **`midi_helpers.MidiParams`**: MIDI検証用（`validate_midi_params()`で使用）
- **`params.SimpleMidiParams`**: 型ヒント用（エディタ補完向け）

---

## 関連ドキュメント

- [TERMINOLOGY.md](./TERMINOLOGY.md) - 用語集
- [CODING_CONVENTIONS.md](./CODING_CONVENTIONS.md) - コーディング規約
- [OIDUNA_CONCEPTS.md](./OIDUNA_CONCEPTS.md) - コンセプト解説
- [architecture/DIAGRAMS.md](./architecture/DIAGRAMS.md) - アーキテクチャ図

---

## 変更履歴

| 日付 | バージョン | 変更内容 |
|------|-----------|---------|
| 2026-03-11 | 1.0.0 | 初版作成（SessionEvent→SessionChange, list→list_*, timing.py, params.py） |

---

**作成者**: Claude Sonnet 4.5
**テストステータス**: 全テスト通過 (83/83 session tests, 21/21 params tests, 28/28 timing tests)
**型チェック**: mypy エラーなし（修正パッケージ）
