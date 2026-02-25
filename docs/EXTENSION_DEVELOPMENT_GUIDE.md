# Oiduna Extension Development Guide

Oiduna拡張の作り方、完全ガイド。

---

## 概要

Oiduna拡張システムは、destination固有やdistribution固有のロジックをOidunaコアから分離し、外部パッケージとして提供する仕組みです。

**設計原則**:
- **汎用性**: Oidunaコアはdestination/distribution非依存
- **拡張性**: 外部パッケージとして独立開発・配布可能
- **自動発見**: entry_pointsで`pip install`するだけで認識
- **パフォーマンス**: 実行時フックは軽量（p99 < 100μs）

---

## クイックスタート

### Step 1: プロジェクト作成

```bash
# ディレクトリ作成
mkdir oiduna-extension-myext
cd oiduna-extension-myext

# パッケージディレクトリ
mkdir oiduna_extension_myext
touch oiduna_extension_myext/__init__.py
```

### Step 2: pyproject.toml

```toml
[project]
name = "oiduna-extension-myext"
version = "0.1.0"
description = "My Oiduna extension"
requires-python = ">=3.13"
dependencies = [
    "oiduna>=0.1.0",
]

# entry_points で自動発見される
[project.entry-points."oiduna.extensions"]
myext = "oiduna_extension_myext:MyExtension"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**重要**: `[project.entry-points."oiduna.extensions"]` の設定が必須！

### Step 3: 拡張クラスの実装

```python
# oiduna_extension_myext/__init__.py

from oiduna_api.extensions import BaseExtension

class MyExtension(BaseExtension):
    """My custom extension"""

    def transform(self, payload: dict) -> dict:
        """
        Session load時の変換（必須）

        Args:
            payload: Session dict
                - messages: list[dict] (destination_id, cycle, step, params)
                - bpm: float
                - pattern_length: float

        Returns:
            Transformed payload
        """
        # メッセージを変換
        for msg in payload.get("messages", []):
            if msg.get("destination_id") == "myext":
                # カスタム処理
                params = msg.get("params", {})
                params["custom_param"] = "value"

        return payload

    # 以下はオプション
    def before_send_messages(self, messages, current_bpm, current_step):
        """送信直前の最終調整（オプション、パフォーマンスクリティカル）"""
        return messages  # デフォルトは無変更

    def startup(self):
        """起動時処理（オプション）"""
        print("MyExtension ready")

    def shutdown(self):
        """終了時処理（オプション）"""
        print("MyExtension stopped")
```

### Step 4: インストールと確認

```bash
# インストール（開発モード）
cd oiduna-extension-myext
uv pip install -e .

# Oiduna起動
cd ../oiduna
uvicorn oiduna_api.main:app --reload

# ログで拡張がロードされたことを確認
# INFO: Extension registered: myext
```

---

## BaseExtension APIリファレンス

### 必須メソッド

#### `transform(payload: dict) -> dict`

**タイミング**: Session load時（`POST /playback/session`受信後、1回だけ）

**目的**: セッションペイロードの変換

**ユースケース**:
- パラメータ追加・削除・変更
- メッセージのフィルタリング
- destination_idの書き換え
- BPM/pattern_lengthの調整

**パフォーマンス**: 制約なし（HTTPリクエストパス上で実行）

**例**:
```python
def transform(self, payload: dict) -> dict:
    for msg in payload["messages"]:
        if msg["destination_id"] == "superdirt":
            # Orbit割り当て
            params = msg["params"]
            params["orbit"] = 0

            # パラメータ名変換
            if "delay_send" in params:
                params["delaySend"] = params.pop("delay_send")

    return payload
```

---

### オプションメソッド

#### `before_send_messages(messages, current_bpm, current_step) -> messages`

**タイミング**: **Runtime、毎ステップ**（OSC/MIDI送信直前）

**目的**: 送信直前のメッセージ最終調整

**ユースケース**:
- BPM依存パラメータの動的注入（例: cps）
- タイムスタンプの追加
- ステップ位置依存の調整

**パフォーマンス**: ⚠️ **超重要** - p99 < 100μs必須
- BPM 120のステップ間隔: 125ms = 125,000μs
- フックは0.08%以下の時間で完了する必要

**引数**:
- `messages`: `list[ScheduledMessage]` - このステップのメッセージ
- `current_bpm`: `float` - 現在のBPM
- `current_step`: `int` - 現在のステップ位置（0-255）

**例**:
```python
def before_send_messages(self, messages, current_bpm, current_step):
    # 軽量な処理のみ！
    cps = current_bpm / 60.0 / 4.0

    return [
        msg.replace(params={**msg.params, "cps": cps})
        if msg.destination_id == "superdirt"
        else msg
        for msg in messages
    ]
```

**⚠️ 禁止事項**:
- ❌ I/O処理（ファイル読み書き、ネットワーク）
- ❌ 重い計算（複雑なアルゴリズム）
- ❌ ログ出力（logger.debug除く）
- ❌ time.sleep()
- ❌ データベースクエリ

**✅ 推奨**:
- リスト内包表記を使用（Pythonの最適化）
- 重い処理は`transform()`で実施
- キャッシュを活用（BPM変更時のみ再計算等）

---

#### `startup() -> None`

**タイミング**: FastAPI起動時（loop_engine起動前）

**目的**: 初期化処理

**ユースケース**:
- 設定の検証
- リソースの確保
- ログ出力

**例**:
```python
def startup(self):
    self.logger.info(f"MyExtension starting with config: {self.config}")
    # リソース初期化など
```

---

#### `shutdown() -> None`

**タイミング**: FastAPI終了時

**目的**: クリーンアップ

**ユースケース**:
- リソースの解放
- 接続のクローズ
- ログのフラッシュ

**例**:
```python
def shutdown(self):
    self.logger.info("MyExtension stopping")
    # クリーンアップ
```

---

#### `get_router() -> APIRouter | None`

**タイミング**: FastAPI起動時（拡張ルーター登録時）

**目的**: カスタムHTTPエンドポイントの提供

**ユースケース**:
- 拡張の状態確認エンドポイント
- 管理UIのAPI
- デバッグツール

**例**:
```python
def get_router(self) -> APIRouter:
    router = APIRouter(prefix="/myext", tags=["myext"])

    @router.get("/status")
    def get_status():
        return {"status": "ok", "version": "0.1.0"}

    @router.post("/reset")
    def reset_state():
        self._state = {}
        return {"status": "reset"}

    return router
```

**アクセス**: `http://localhost:8000/myext/status`

---

## パフォーマンスガイドライン

### before_send_messages() の最適化

#### ❌ 悪い例

```python
def before_send_messages(self, messages, current_bpm, current_step):
    # 毎回ログ出力（遅い！）
    logger.info(f"Processing {len(messages)} messages")

    # 非効率なループ
    result = []
    for msg in messages:
        new_msg = copy.deepcopy(msg)  # deepcopyは重い
        if msg.destination_id == "superdirt":
            new_params = msg.params.copy()
            new_params["cps"] = current_bpm / 60.0 / 4.0
            new_msg.params = new_params
        result.append(new_msg)

    return result
```

#### ✅ 良い例

```python
def before_send_messages(self, messages, current_bpm, current_step):
    # BPMキャッシュ（変更時のみ再計算）
    if self._cached_bpm != current_bpm:
        self._cached_bpm = current_bpm
        self._cached_cps = current_bpm / 60.0 / 4.0

    cps = self._cached_cps

    # リスト内包表記（高速）
    return [
        msg.replace(params={**msg.params, "cps": cps})
        if msg.destination_id == "superdirt"
        else msg
        for msg in messages
    ]
```

### transform() の最適化

`transform()`はHTTPリクエストパス上で実行されるため、パフォーマンス制約は緩い。ただし、以下に注意：

```python
def transform(self, payload: dict) -> dict:
    # ✅ OK: 事前計算
    lookup_table = self._build_lookup_table()

    # ✅ OK: ファイル読み込み（session load時のみ）
    custom_mapping = self._load_mapping_file()

    for msg in payload["messages"]:
        # 変換処理
        pass

    return payload
```

---

## テスト方法

### ユニットテスト

```python
# tests/test_myext.py

from oiduna_extension_myext import MyExtension

def test_transform():
    ext = MyExtension()

    payload = {
        "messages": [
            {"destination_id": "myext", "params": {}}
        ],
        "bpm": 120.0,
        "pattern_length": 4.0
    }

    result = ext.transform(payload)

    assert result["messages"][0]["params"]["custom_param"] == "value"

def test_before_send_messages():
    ext = MyExtension()

    # Mock ScheduledMessage
    from dataclasses import dataclass

    @dataclass
    class MockMsg:
        destination_id: str
        params: dict

        def replace(self, **kwargs):
            return MockMsg(self.destination_id, kwargs.get("params", self.params))

    messages = [MockMsg("myext", {"s": "bd"})]

    result = ext.before_send_messages(messages, 120.0, 0)

    assert len(result) == 1
```

### パフォーマンステスト

```python
import time
import statistics

def test_performance():
    ext = MyExtension()

    messages = [...]  # 典型的なケース

    # Warm up
    for _ in range(100):
        ext.before_send_messages(messages, 120.0, 0)

    # Measure
    durations = []
    for _ in range(1000):
        start = time.perf_counter()
        result = ext.before_send_messages(messages, 120.0, 0)
        duration = time.perf_counter() - start
        durations.append(duration)

    p99 = sorted(durations)[int(len(durations) * 0.99)]

    print(f"p99: {p99*1e6:.2f}μs")
    assert p99 < 0.0001  # 100μs
```

### 統合テスト

```python
from fastapi.testclient import TestClient
from oiduna_api.main import app

def test_extension_integration():
    client = TestClient(app)

    # 拡張がロードされているか確認
    response = client.post("/playback/session", json={
        "messages": [...],
        "bpm": 120.0,
        "pattern_length": 4.0
    })

    assert response.status_code == 200
```

---

## デバッグTips

### ログ出力

```python
import logging

logger = logging.getLogger(__name__)

class MyExtension(BaseExtension):
    def transform(self, payload: dict) -> dict:
        logger.debug(f"Processing {len(payload['messages'])} messages")
        # ...

    def before_send_messages(self, messages, current_bpm, current_step):
        # ⚠️ before_send_messagesではログを最小限に
        # logger.debug()のみ許容
        if self._debug_mode:
            logger.debug(f"Step {current_step}: {len(messages)} messages")
        # ...
```

### 拡張が認識されない場合

```bash
# entry_pointsを確認
python -c "from importlib.metadata import entry_points; print(list(entry_points(group='oiduna.extensions')))"

# 期待される出力:
# [EntryPoint(name='myext', value='oiduna_extension_myext:MyExtension', group='oiduna.extensions')]
```

### パフォーマンス問題のデバッグ

```python
import cProfile
import pstats

# プロファイリング
profiler = cProfile.Profile()
profiler.enable()

ext.before_send_messages(messages, 120.0, 0)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)
```

---

## ベストプラクティス

### 1. destination_id でフィルタリング

```python
def transform(self, payload: dict) -> dict:
    for msg in payload["messages"]:
        # 自分のdestinationのみ処理
        if msg["destination_id"] != "myext":
            continue

        # 処理...

    return payload
```

### 2. 設定をコンストラクタで受け取る

```python
def __init__(self, config: dict | None = None):
    super().__init__(config)

    # 設定から値を取得
    self.default_value = self.config.get("default_value", 42)
    self.enabled_feature = self.config.get("enabled_feature", True)
```

### 3. 内部パラメータは削除

```python
def transform(self, payload: dict) -> dict:
    for msg in payload["messages"]:
        params = msg["params"]

        # 内部パラメータを使用
        internal_id = params.get("internal_id")
        # ... 処理 ...

        # 送信前に削除
        params.pop("internal_id", None)

    return payload
```

### 4. Immutableなデータ構造を尊重

```python
# ❌ 悪い例
def before_send_messages(self, messages, current_bpm, current_step):
    for msg in messages:
        msg.params["cps"] = cps  # ScheduledMessage is frozen!

# ✅ 良い例
def before_send_messages(self, messages, current_bpm, current_step):
    return [
        msg.replace(params={**msg.params, "cps": cps})
        for msg in messages
    ]
```

---

## 公開・配布

### PyPIへの公開

```bash
# ビルド
python -m build

# PyPIへアップロード
python -m twine upload dist/*
```

### インストール

```bash
# PyPIから
pip install oiduna-extension-myext

# Gitから
pip install git+https://github.com/user/oiduna-extension-myext.git
```

---

## 参考実装

### SuperDirt拡張

`oiduna-extension-superdirt`が完全な実装例です：

- Orbit割り当て
- パラメータ名変換
- CPS注入（before_send_messages）
- カスタムエンドポイント

[oiduna-extension-superdirt](../../../oiduna-extension-superdirt/)

---

## FAQ

### Q: 複数の拡張をインストールした場合の実行順序は？

A: entry_pointsの発見順（通常はアルファベット順）。順序に依存する設計は避けるべき。

### Q: 拡張から別の拡張にアクセスできる？

A: できません。拡張は独立して動作します。

### Q: 設定ファイル（extensions.yaml）は使える？

A: 現在は未サポート。将来的に追加予定。

### Q: before_send_messagesでメッセージを追加/削除できる？

A: できます。リストを返すので、長さを変えても問題ありません。

```python
def before_send_messages(self, messages, current_bpm, current_step):
    # メッセージを追加
    extra_msg = ScheduledMessage(...)
    return messages + [extra_msg]

    # または削除
    return [msg for msg in messages if msg.params.get("s") != "silence"]
```

---

**作成日**: 2026-02-25
**バージョン**: 1.0
