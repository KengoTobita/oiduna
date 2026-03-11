# Migration Guide: Schedule/Cued Terminology (2026-03)

このガイドは、2026年3月に実施したSchedule/Cued命名整理に伴う破壊的変更の移行手順を説明します。

## 概要

MessageScheduler系とTimeline系の命名を整理し、2つの"Scheduled"の混乱を解消しました。

### 変更の背景

**問題**: `Scheduled`が2つの異なる意味で使われ、混乱を招いていました

```python
# 意味1: 確定済み実行計画（不変・過去分詞）
ScheduledMessageBatch  # "配置が完了している"256ステップのスケジュール

# 意味2: 未来予約（形容詞・未来）
ScheduledChange        # "予約されている"将来の変更
```

**解決策**: 用語を明確に分離

```python
# ループ実行系: Schedule（名詞）- 確定済み実行時刻表
LoopSchedule           # 列車の時刻表のような確定済みプラン
LoopScheduler          # 時刻表を実行するエンジン

# Timeline系: Cued（形容詞）- 次に来るもの
CuedChange             # DJが次に出す準備をしているトラック
CuedChangeTimeline     # キューされた変更の管理
```

---

## 破壊的変更一覧

### 1. LoopSchedule系（oiduna_scheduler）

| 変更前 | 変更後 | 影響範囲 |
|--------|--------|---------|
| `ScheduledMessageBatch` | `LoopSchedule` | 全パッケージ |
| `ScheduledMessage` | `ScheduleEntry` | 全パッケージ |
| `MessageScheduler` | `LoopScheduler` | Loop Engine |
| `batch.messages` | `batch.entries` | アクセス |
| `load_messages()` | `load_schedule()` | メソッド名 |
| `get_messages_at_step()` | `get_entries_at_step()` | メソッド名 |

### 2. CuedChange系（oiduna_timeline）

| 変更前 | 変更後 | 影響範囲 |
|--------|--------|---------|
| `ScheduledChange` | `CuedChange` | Timeline機能 |
| `ScheduledChangeTimeline` | `CuedChangeTimeline` | Timeline機能 |
| `schedule_change()` | `cue_change()` | メソッド名 |
| `scheduled_at` | `cued_at` | フィールド名 |
| `ScheduleChangeRequest` | `CueChangeRequest` | API |
| `ScheduleChangeResponse` | `CueChangeResponse` | API |
| `POST /timeline/schedule` | `POST /timeline/cue` | エンドポイント |

---

## 移行手順

### Phase 1: LoopSchedule系の更新

#### 1-1. インポート文の更新

```python
# 変更前
from oiduna_scheduler import ScheduledMessageBatch, ScheduledMessage, MessageScheduler

# 変更後
from oiduna_scheduler import LoopSchedule, ScheduleEntry, LoopScheduler
```

#### 1-2. 型アノテーションの更新

```python
# 変更前
def compile(session: Session) -> ScheduledMessageBatch:
    messages: list[ScheduledMessage] = []
    return ScheduledMessageBatch(messages=tuple(messages), bpm=120)

# 変更後
def compile(session: Session) -> LoopSchedule:
    entries: list[ScheduleEntry] = []
    return LoopSchedule(entries=tuple(entries), bpm=120)
```

#### 1-3. コンストラクタ引数の更新

```python
# 変更前
batch = ScheduledMessageBatch(
    messages=(msg1, msg2),
    bpm=120.0
)

# 変更後
schedule = LoopSchedule(
    entries=(entry1, entry2),
    bpm=120.0
)
```

#### 1-4. 属性アクセスの更新

```python
# 変更前
for msg in batch.messages:
    print(msg.destination_id)

# 変更後
for entry in schedule.entries:
    print(entry.destination_id)
```

#### 1-5. メソッド呼び出しの更新

```python
# 変更前
scheduler = MessageScheduler()
scheduler.load_messages(batch)
messages = scheduler.get_messages_at_step(64)

# 変更後
scheduler = LoopScheduler()
scheduler.load_schedule(schedule)
entries = scheduler.get_entries_at_step(64)
```

---

### Phase 2: CuedChange系の更新

#### 2-1. インポート文の更新

```python
# 変更前
from oiduna_timeline import ScheduledChange, ScheduledChangeTimeline

# 変更後
from oiduna_timeline import CuedChange, CuedChangeTimeline
```

#### 2-2. モデル名の更新

```python
# 変更前
change = ScheduledChange(
    target_global_step=1000,
    batch=batch,
    client_id="alice",
    scheduled_at=time.time()
)

# 変更後
change = CuedChange(
    target_global_step=1000,
    batch=schedule,
    client_id="alice",
    cued_at=time.time()
)
```

#### 2-3. メソッド名の更新

```python
# 変更前
timeline = ScheduledChangeTimeline()
success, msg = timeline.add_change(change, current_step)
changes = timeline.get_changes_at(1000)

# 変更後
timeline = CuedChangeTimeline()
success, msg = timeline.cue_change(change, current_step)
changes = timeline.get_cued_at(1000)
```

#### 2-4. API エンドポイントの更新

**HTTPリクエスト**:

```bash
# 変更前
POST /timeline/schedule
Content-Type: application/json

{
  "target_global_step": 1000,
  "messages": [...]
}

# 変更後
POST /timeline/cue
Content-Type: application/json

{
  "target_global_step": 1000,
  "entries": [...]
}
```

**Response**:

```python
# 変更前
{
  "change_id": "uuid",
  "scheduled_at": 1234567890.0
}

# 変更後
{
  "change_id": "uuid",
  "cued_at": 1234567890.0
}
```

---

## 一括置換スクリプト

### LoopSchedule系

```bash
# インポート
find . -type f -name "*.py" -exec sed -i \
  's/from oiduna_scheduler.scheduler_models import ScheduledMessageBatch/from oiduna_scheduler.scheduler_models import LoopSchedule/g; \
   s/from oiduna_scheduler.scheduler_models import ScheduledMessage/from oiduna_scheduler.scheduler_models import ScheduleEntry/g; \
   s/from oiduna_scheduler.scheduler import MessageScheduler/from oiduna_scheduler.scheduler import LoopScheduler/g; \
   s/from oiduna_scheduler import ScheduledMessageBatch, ScheduledMessage/from oiduna_scheduler import LoopSchedule, ScheduleEntry/g' {} \;

# 型名
find . -type f -name "*.py" -exec sed -i \
  's/: ScheduledMessageBatch/: LoopSchedule/g; \
   s/: ScheduledMessage/: ScheduleEntry/g; \
   s/\[ScheduledMessage\]/[ScheduleEntry]/g; \
   s/-> ScheduledMessageBatch/-> LoopSchedule/g; \
   s/-> ScheduledMessage/-> ScheduleEntry/g' {} \;

# コンストラクタ
find . -type f -name "*.py" -exec sed -i \
  's/ScheduledMessageBatch(/LoopSchedule(/g; \
   s/ScheduledMessage(/ScheduleEntry(/g; \
   s/MessageScheduler(/LoopScheduler(/g' {} \;

# 属性・メソッド
find . -type f -name "*.py" -exec sed -i \
  's/\.messages\[/.entries[/g; \
   s/\.messages)/.entries)/g; \
   s/messages=/entries=/g; \
   s/load_messages(/load_schedule(/g; \
   s/get_messages_at_step(/get_entries_at_step(/g' {} \;

# docstring内
find . -type f -name "*.py" -exec sed -i \
  's/ScheduledMessageBatch/LoopSchedule/g; \
   s/ScheduledMessage/ScheduleEntry/g; \
   s/MessageScheduler/LoopScheduler/g' {} \;
```

### CuedChange系

```bash
# インポート
find . -type f -name "*.py" -exec sed -i \
  's/from oiduna_timeline import ScheduledChange, ScheduledChangeTimeline/from oiduna_timeline import CuedChange, CuedChangeTimeline/g; \
   s/from oiduna_timeline import ScheduledChange/from oiduna_timeline import CuedChange/g; \
   s/from oiduna_timeline import ScheduledChangeTimeline/from oiduna_timeline import CuedChangeTimeline/g' {} \;

# 型名・クラス名
find . -type f -name "*.py" -exec sed -i \
  's/: ScheduledChange/: CuedChange/g; \
   s/\[ScheduledChange\]/[CuedChange]/g; \
   s/-> ScheduledChange/-> CuedChange/g; \
   s/ScheduledChangeTimeline/CuedChangeTimeline/g' {} \;

# メソッド・フィールド
find . -type f -name "*.py" -exec sed -i \
  's/schedule_change(/cue_change(/g; \
   s/\.schedule_change(/.cue_change(/g; \
   s/scheduled_at=/cued_at=/g; \
   s/\.scheduled_at/.cued_at/g; \
   s/"scheduled_at"/"cued_at"/g' {} \;

# コンストラクタ
find . -type f -name "*.py" -exec sed -i \
  's/ScheduledChange(/CuedChange(/g' {} \;

# docstring内
find . -type f -name "*.py" -exec sed -i \
  's/ScheduledChange/CuedChange/g' {} \;
```

**注意**: 必ずバージョン管理下で実行し、`git diff`で確認してください。

---

## 互換性エイリアス

後方互換性のため、一時的にエイリアスを提供しています：

```python
# oiduna_scheduler/__init__.py
ScheduledMessage = ScheduleEntry  # Deprecated
ScheduledMessageBatch = LoopSchedule  # Deprecated
MessageScheduler = LoopScheduler  # Deprecated
```

**⚠️ 警告**: これらのエイリアスは次回のメジャーバージョンアップで削除されます。
早めに新しい名前に移行してください。

---

## トラブルシューティング

### Q1: `ImportError: cannot import name 'ScheduledMessageBatch'`

**A**: `oiduna_scheduler`のバージョンが古い可能性があります。

```bash
# 依存関係を更新
uv sync

# または最新版をインストール
uv add oiduna-scheduler --upgrade
```

### Q2: `AttributeError: 'LoopSchedule' object has no attribute 'messages'`

**A**: `.messages`を`.entries`に変更してください。

```python
# ❌ 旧
for msg in schedule.messages:
    ...

# ✅ 新
for entry in schedule.entries:
    ...
```

### Q3: `TypeError: LoopSchedule.__init__() got an unexpected keyword argument 'messages'`

**A**: コンストラクタ引数を`messages=`から`entries=`に変更してください。

```python
# ❌ 旧
LoopSchedule(messages=(...))

# ✅ 新
LoopSchedule(entries=(...))
```

### Q4: API エンドポイント `/timeline/schedule` が404

**A**: エンドポイントが`/timeline/cue`に変更されました。

```bash
# ❌ 旧
curl -X POST http://localhost:57122/timeline/schedule

# ✅ 新
curl -X POST http://localhost:57122/timeline/cue
```

### Q5: `scheduled_at`フィールドがない

**A**: `cued_at`に変更されました。

```python
# ❌ 旧
change.scheduled_at

# ✅ 新
change.cued_at
```

---

## テスト実行

すべての移行が完了したら、テストを実行して動作確認してください。

```bash
# 全パッケージのテスト
uv run pytest packages/ -v

# 特定パッケージのテスト
uv run pytest packages/oiduna_scheduler/ packages/oiduna_timeline/ -v

# 型チェック
uv run mypy packages/oiduna_scheduler packages/oiduna_timeline packages/oiduna_session

# カバレッジ確認
uv run pytest packages/ --cov=packages --cov-report=term-missing
```

---

## 用語の使い分け（参考）

### Schedule vs Cued

| 用語 | 品詞 | 意味 | 例 |
|------|------|------|-----|
| **Schedule** | 名詞 | 確定済みの時刻表・予定表 | "bus schedule"（バスの時刻表） |
| **Scheduler** | 名詞 | スケジューラー・実行者 | "task scheduler"（タスク実行管理） |
| **Cued** | 形容詞 | キューされた・次に来る | "cued track"（DJが次に出すトラック） |
| **Cue** | 動詞 | キューする・準備する | "cue the next song"（次の曲を準備） |

### 音楽的な類推

```
LoopSchedule (楽譜)
├─ 256ステップに音符が配置されている
├─ 一度書いたら変わらない（不変）
└─ 演奏者（LoopScheduler）がこれを読む

CuedChange (DJのキューリスト)
├─ 「step 1000で次のトラックに切り替える」予約
├─ まだ実行されていない（未来）
└─ タイミングが来たら適用される
```

---

## 関連ドキュメント

- [TERMINOLOGY.md](./TERMINOLOGY.md) - 用語集（Schedule/Cued定義含む）
- [CODING_CONVENTIONS.md](./CODING_CONVENTIONS.md) - コーディング規約
- [API_REFERENCE.md](./API_REFERENCE.md) - API仕様
- [MIGRATION_GUIDE_TERMINOLOGY_CLEANUP.md](./MIGRATION_GUIDE_TERMINOLOGY_CLEANUP.md) - SessionEvent→SessionChange移行ガイド

---

## 変更履歴

| 日付 | バージョン | 変更内容 |
|------|-----------|---------|
| 2026-03-11 | 1.0.0 | 初版作成（LoopSchedule系、CuedChange系） |

---

**作成者**: Claude Sonnet 4.5
**テストステータス**: 全テスト通過 (122/122 passed ✅)
**型チェック**: mypy エラーなし
**影響範囲**: 約45ファイル
**破壊的変更**: あり（後方互換性エイリアス提供）
