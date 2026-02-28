# Oiduna 拡張機能開発ガイド - レイヤーアーキテクチャとの対応

Oidunaの5+1レイヤーアーキテクチャにおける拡張ポイントと、FastAPI機能の対応関係を解説します。

---

## 目次

1. [アーキテクチャ概要](#アーキテクチャ概要)
2. [レイヤー別拡張ポイント](#レイヤー別拡張ポイント)
3. [FastAPI機能とレイヤーの対応](#fastapi機能とレイヤーの対応)
4. [具体的な実装例](#具体的な実装例)
5. [ベストプラクティス](#ベストプラクティス)
6. [参考資料](#参考資料)

---

## アーキテクチャ概要

### 5+1レイヤー構造

```
┌─────────────────────────────────────────┐
│  External Interface (Optional)          │  - CLI, Client
├─────────────────────────────────────────┤
│  Layer 1: API                           │  - oiduna_api (FastAPI)
├─────────────────────────────────────────┤
│  Layer 2: Application                   │  - oiduna_session, oiduna_auth
├─────────────────────────────────────────┤
│  Layer 3: Core                          │  - oiduna_loop, oiduna_core
├─────────────────────────────────────────┤
│  Layer 4: Domain                        │  - oiduna_scheduler
├─────────────────────────────────────────┤
│  Layer 5: Data (Foundation)             │  - oiduna_models
└─────────────────────────────────────────┘
```

### 依存関係の原則

- **下方向のみ**: 上位レイヤーは下位レイヤーに依存可能、逆は不可
- **レイヤースキップ禁止**: Layer 1 → Layer 3のような飛び越しは避ける
- **水平依存禁止**: 同一レイヤー内での相互依存は避ける

---

## レイヤー別拡張ポイント

### External Interface (Optional): CLI/Client

**目的**: エンドユーザー向けインターフェース

#### 拡張ポイント

| 拡張ポイント | 対応するFastAPI機能 | 実装場所 |
|------------|-------------------|---------|
| カスタムCLIコマンド | - (外部) | `oiduna_cli` |
| クライアントライブラリ | - (外部) | `oiduna_client` |

#### 実装例

**カスタムCLIコマンド**

```python
# oiduna_extension_myext/cli.py

import click
from oiduna_client import OidunaClient

@click.command()
@click.option("--host", default="localhost")
@click.option("--port", default=57122)
def myext_status(host: str, port: int):
    """MyExt拡張のステータスを表示"""
    client = OidunaClient(f"http://{host}:{port}")
    response = client.get("/myext/status")
    click.echo(f"Status: {response.json()}")

if __name__ == "__main__":
    myext_status()
```

**拡張クライアントメソッド**

```python
# oiduna_extension_myext/client_ext.py

from oiduna_client import OidunaClient

class MyExtClient(OidunaClient):
    """MyExt拡張用のクライアント拡張"""

    def send_myext_command(self, command: str):
        """カスタムコマンドを送信"""
        return self.post("/myext/command", json={"command": command})

    def get_myext_state(self):
        """拡張のステータスを取得"""
        return self.get("/myext/status")
```

#### ベストプラクティス

- ✅ Layer 1 (API)のエンドポイントを利用する
- ✅ oiduna_clientを継承して拡張機能を追加
- ❌ APIを介さずに内部実装に直接アクセスしない

---

### Layer 1: API (oiduna_api)

**目的**: HTTP/WebSocketエンドポイント、リクエスト/レスポンス処理

#### 拡張ポイント

| 拡張ポイント | 対応するFastAPI機能 | 実装場所 | 難易度 |
|------------|-------------------|---------|--------|
| カスタムエンドポイント | `APIRouter`, `@app.get/post` | `BaseExtension.get_router()` | ⭐ |
| リクエスト前処理 | `Middleware` | FastAPI Middleware | ⭐⭐ |
| レスポンス後処理 | `Middleware` | FastAPI Middleware | ⭐⭐ |
| WebSocketエンドポイント | `@app.websocket` | Custom Router | ⭐⭐⭐ |
| SSEストリーミング | `EventSourceResponse` | Custom Router | ⭐⭐⭐ |
| カスタム認証 | `Depends`, `Security` | Dependencies | ⭐⭐ |
| エラーハンドリング | `@app.exception_handler` | Exception Handlers | ⭐⭐ |
| 起動/終了処理 | `lifespan`, `@app.on_event` | `BaseExtension.startup/shutdown()` | ⭐ |

#### 実装例

**1. カスタムエンドポイント (最も基本的)**

```python
# oiduna_extension_myext/__init__.py

from fastapi import APIRouter
from oiduna_api.extensions import BaseExtension

class MyExtExtension(BaseExtension):
    """カスタムエンドポイントを追加する拡張"""

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self.custom_state = {}

    def get_router(self) -> APIRouter:
        """カスタムルーターを提供"""
        router = APIRouter(prefix="/myext", tags=["myext"])

        @router.get("/status")
        def get_status():
            """拡張のステータスを返す"""
            return {
                "extension": "myext",
                "version": "0.1.0",
                "state": self.custom_state
            }

        @router.post("/command")
        def send_command(command: str):
            """カスタムコマンドを処理"""
            self.custom_state["last_command"] = command
            return {"status": "ok", "command": command}

        return router

    def transform(self, payload: dict) -> dict:
        """必須メソッド: セッションペイロード変換"""
        return payload  # この拡張ではペイロード変換なし
```

**2. Middleware (リクエスト/レスポンス処理)**

```python
# oiduna_extension_myext/middleware.py

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time

class MyExtMiddleware(BaseHTTPMiddleware):
    """カスタムミドルウェア: リクエスト時間を計測"""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # リクエスト前処理
        request.state.myext_start = start_time

        # 次の処理へ
        response = await call_next(request)

        # レスポンス後処理
        process_time = time.time() - start_time
        response.headers["X-MyExt-Process-Time"] = str(process_time)

        return response

# main.pyで登録:
# app.add_middleware(MyExtMiddleware)
```

**3. Dependency Injection (認証・依存関係)**

```python
# oiduna_extension_myext/dependencies.py

from fastapi import Depends, HTTPException, Header
from typing import Annotated

class MyExtAuth:
    """カスタム認証ヘルパー"""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def verify(self, x_api_key: Annotated[str, Header()]):
        """API Keyを検証"""
        if x_api_key != self.api_key:
            raise HTTPException(status_code=401, detail="Invalid API Key")
        return True

# Routerで使用:
# @router.get("/protected")
# def protected_endpoint(auth: bool = Depends(myext_auth.verify)):
#     return {"message": "Authenticated"}
```

**4. WebSocketエンドポイント**

```python
# oiduna_extension_myext/websocket.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio

router = APIRouter()

@router.websocket("/myext/ws")
async def myext_websocket(websocket: WebSocket):
    """カスタムWebSocketエンドポイント"""
    await websocket.accept()

    try:
        while True:
            # クライアントからのメッセージを受信
            data = await websocket.receive_json()

            # 処理してレスポンス
            response = {
                "type": "myext_response",
                "data": f"Received: {data}"
            }
            await websocket.send_json(response)

    except WebSocketDisconnect:
        print("WebSocket disconnected")
```

**5. Exception Handler (エラー処理)**

```python
# oiduna_extension_myext/exceptions.py

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

class MyExtException(Exception):
    """カスタム例外"""
    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code

async def myext_exception_handler(request: Request, exc: MyExtException):
    """カスタム例外ハンドラー"""
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "extension": "myext"
            }
        }
    )

# main.pyで登録:
# app.add_exception_handler(MyExtException, myext_exception_handler)
```

**6. Lifespan Events (起動/終了処理)**

```python
# oiduna_extension_myext/__init__.py

from oiduna_api.extensions import BaseExtension
import logging

logger = logging.getLogger(__name__)

class MyExtExtension(BaseExtension):
    """起動/終了処理を持つ拡張"""

    def startup(self):
        """起動時処理"""
        logger.info("MyExt: Initializing resources...")
        # リソースの初期化
        self.connection = self._connect_to_service()
        logger.info("MyExt: Ready")

    def shutdown(self):
        """終了時処理"""
        logger.info("MyExt: Cleaning up...")
        # リソースのクリーンアップ
        if hasattr(self, 'connection'):
            self.connection.close()
        logger.info("MyExt: Stopped")

    def _connect_to_service(self):
        """外部サービスへの接続"""
        # 実装例
        return {"host": "localhost", "port": 9999}

    def transform(self, payload: dict) -> dict:
        return payload
```

#### ベストプラクティス

- ✅ **Router分離**: エンドポイントは`get_router()`で提供
- ✅ **Dependency Injection**: `Depends()`で依存関係を注入
- ✅ **Middleware最小化**: パフォーマンス重視、必要最小限の処理
- ✅ **Lifespan管理**: リソース初期化は`startup()`, クリーンアップは`shutdown()`
- ❌ **グローバル状態**: 可能な限り避ける、`app.state`や`request.state`を活用

---

### Layer 2: Application (oiduna_session, oiduna_auth)

**目的**: ビジネスロジック、セッション管理、認証

#### 拡張ポイント

| 拡張ポイント | 対応するFastAPI機能 | 実装場所 | 難易度 |
|------------|-------------------|---------|--------|
| セッション変換 | `Dependencies` | `BaseExtension.transform()` | ⭐ |
| カスタム認証戦略 | `Security`, `Depends` | Custom Dependency | ⭐⭐ |
| セッション検証 | `Dependencies` | Custom Validator | ⭐⭐ |
| バックグラウンドタスク | `BackgroundTasks` | Router Endpoint | ⭐⭐ |

#### 実装例

**1. セッションペイロード変換 (最重要)**

```python
# oiduna_extension_myext/__init__.py

from oiduna_api.extensions import BaseExtension

class MyExtExtension(BaseExtension):
    """セッションペイロードを変換する拡張"""

    def transform(self, payload: dict) -> dict:
        """
        POST /playback/session 時に呼ばれる

        Args:
            payload: {
                "messages": [
                    {
                        "destination_id": "myext",
                        "cycle": 0,
                        "step": 0,
                        "params": {"note": 60}
                    }
                ],
                "bpm": 120.0,
                "pattern_length": 1.0
            }

        Returns:
            変換後のpayload
        """
        messages = payload.get("messages", [])

        for msg in messages:
            # myext destination向けメッセージを処理
            if msg.get("destination_id") == "myext":
                params = msg.get("params", {})

                # カスタムパラメータを追加
                params["_myext_version"] = "0.1.0"

                # noteを変換 (例: transpose)
                if "note" in params:
                    params["note"] = params["note"] + self.config.get("transpose", 0)

                # cycleベースのバリエーション
                cycle = msg.get("cycle", 0)
                if cycle % 2 == 0:
                    params["variation"] = "A"
                else:
                    params["variation"] = "B"

        return payload
```

**2. カスタム認証戦略**

```python
# oiduna_extension_myext/auth.py

from fastapi import Depends, HTTPException, Header
from typing import Annotated

class MyExtAuthProvider:
    """カスタム認証プロバイダー"""

    def __init__(self, secret_key: str):
        self.secret_key = secret_key

    async def verify_token(
        self,
        x_myext_token: Annotated[str, Header()]
    ) -> dict:
        """カスタムトークンを検証"""
        # トークン検証ロジック
        if not self._is_valid_token(x_myext_token):
            raise HTTPException(
                status_code=401,
                detail="Invalid MyExt token"
            )

        return {"user_id": "myext_user", "permissions": ["read", "write"]}

    def _is_valid_token(self, token: str) -> bool:
        # 実装例: シンプルなトークン検証
        return token.startswith("myext_") and len(token) > 10

# Routerで使用:
# myext_auth = MyExtAuthProvider(secret_key="secret")
#
# @router.get("/protected")
# async def protected(auth: dict = Depends(myext_auth.verify_token)):
#     return {"user": auth["user_id"]}
```

**3. BackgroundTasks (非同期処理)**

```python
# oiduna_extension_myext/background.py

from fastapi import APIRouter, BackgroundTasks
import logging

router = APIRouter(prefix="/myext", tags=["myext"])
logger = logging.getLogger(__name__)

def process_heavy_task(data: dict):
    """重い処理をバックグラウンドで実行"""
    logger.info(f"Processing heavy task: {data}")
    # 実装例: データベース書き込み、外部API呼び出しなど
    import time
    time.sleep(5)  # 重い処理のシミュレーション
    logger.info(f"Task completed: {data}")

@router.post("/trigger")
async def trigger_task(
    background_tasks: BackgroundTasks,
    data: dict
):
    """
    バックグラウンドタスクをトリガー

    レスポンスは即座に返し、処理は非同期で実行される
    """
    background_tasks.add_task(process_heavy_task, data)
    return {
        "status": "accepted",
        "message": "Task queued for processing"
    }
```

**4. SessionContainer統合 (依存性注入)**

```python
# oiduna_extension_myext/session_integration.py

from fastapi import APIRouter, Depends
from oiduna_api.dependencies import get_container
from oiduna_session import SessionContainer

router = APIRouter(prefix="/myext", tags=["myext"])

@router.get("/session/tracks")
def list_myext_tracks(
    container: SessionContainer = Depends(get_container)
):
    """
    SessionContainerを利用してトラック情報を取得

    Layer 2のSessionContainerに依存する例
    """
    tracks = container.tracks.list()

    # myext関連のトラックのみフィルタ
    myext_tracks = [
        track for track in tracks
        if track.get("destination_id") == "myext"
    ]

    return {
        "total": len(tracks),
        "myext_tracks": len(myext_tracks),
        "tracks": myext_tracks
    }
```

#### ベストプラクティス

- ✅ **transform()の軽量化**: HTTP requestパス上で実行されるため高速に
- ✅ **Dependency Injection**: SessionContainer等は`Depends()`で取得
- ✅ **BackgroundTasks活用**: 重い処理はバックグラウンドで
- ✅ **エラーハンドリング**: 変換失敗時は適切に例外を送出
- ❌ **I/O処理**: transform()内でファイル読み書き・外部API呼び出しは避ける

---

### Layer 3: Core (oiduna_loop, oiduna_core)

**目的**: ループエンジン、タイミング制御、リアルタイム処理

#### 拡張ポイント

| 拡張ポイント | 対応するFastAPI機能 | 実装場所 | 難易度 |
|------------|-------------------|---------|--------|
| メッセージ送信フック | - (内部Hook) | `BaseExtension.before_send_messages()` | ⭐⭐⭐ |
| カスタム出力先 | - (内部Protocol) | `OutputProtocol`実装 | ⭐⭐⭐⭐ |
| タイミング調整 | - (内部Hook) | Runtime Hook | ⭐⭐⭐⭐ |

#### 実装例

**1. before_send_messages() (ランタイムフック)**

```python
# oiduna_extension_myext/__init__.py

from oiduna_api.extensions import BaseExtension
from typing import Any

class MyExtExtension(BaseExtension):
    """ランタイムでメッセージを変換する拡張"""

    def before_send_messages(
        self,
        messages: list[Any],  # list[ScheduledMessage]
        current_bpm: float,
        current_step: int
    ) -> list[Any]:
        """
        メッセージ送信直前のフック (パフォーマンスクリティカル!)

        警告:
        - このメソッドはタイミングループ内で実行される
        - 処理時間 < 100μs を目標に
        - I/O処理、ログ出力、重い計算は絶対禁止

        Args:
            messages: 現在のstepで送信されるメッセージリスト
            current_bpm: 現在のBPM (動的変更される可能性)
            current_step: 現在のステップ位置 (0-255)

        Returns:
            変換後のメッセージリスト
        """
        # 例1: テンポ依存パラメータの注入
        cps = current_bpm / 60.0 / 4.0  # cycles per second

        modified = []
        for msg in messages:
            if msg.destination_id == "myext":
                # メッセージをコピーして変更
                new_params = {**msg.params, "cps": cps}

                # ステップ依存の処理
                if current_step % 16 == 0:  # 小節の頭
                    new_params["accent"] = 1.0

                # msg.replace()でイミュータブルに更新
                modified.append(msg.replace(params=new_params))
            else:
                modified.append(msg)

        return modified
```

**注意: このフックは超高頻度で呼ばれる**

```python
# パフォーマンス測定例

import time

class MyExtExtension(BaseExtension):
    def __init__(self, config=None):
        super().__init__(config)
        self._total_calls = 0
        self._total_time = 0.0

    def before_send_messages(self, messages, current_bpm, current_step):
        start = time.perf_counter()

        # 軽量な処理のみ
        modified = [
            msg.replace(params={**msg.params, "step": current_step})
            if msg.destination_id == "myext"
            else msg
            for msg in messages
        ]

        elapsed = time.perf_counter() - start
        self._total_calls += 1
        self._total_time += elapsed

        # 統計は別スレッドで定期的にログ出力
        # (ここでlog出力するとパフォーマンス低下)

        return modified
```

**2. カスタムDestination実装 (高度)**

```python
# oiduna_extension_myext/destination.py

from oiduna_models import DestinationConfig
from oiduna_scheduler.senders import DestinationSender
from typing import Any

class MyExtDestinationConfig(DestinationConfig):
    """カスタムdestination設定"""
    type: str = "myext"
    host: str = "localhost"
    port: int = 9999

class MyExtDestinationSender(DestinationSender):
    """カスタムdestination送信クラス"""

    def __init__(self, config: MyExtDestinationConfig):
        self.config = config
        self._connection = None

    def connect(self):
        """接続を確立"""
        # 実装例
        self._connection = self._create_connection()

    def send(self, messages: list[Any]):
        """メッセージを送信"""
        for msg in messages:
            # カスタムプロトコルで送信
            self._send_via_custom_protocol(msg)

    def close(self):
        """接続を閉じる"""
        if self._connection:
            self._connection.close()

    def _create_connection(self):
        # 実装例: ソケット接続など
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return s

    def _send_via_custom_protocol(self, msg):
        # カスタムプロトコル実装
        pass
```

#### ベストプラクティス

- ✅ **before_send_messages()の最適化**: マイクロ秒単位での高速化が必須
- ✅ **イミュータブル更新**: `msg.replace()`でコピー作成
- ✅ **条件分岐最小化**: destination_idでの早期return
- ❌ **I/O処理**: ファイル、ネットワーク、ログ出力は禁止
- ❌ **重い計算**: 複雑な数値計算、文字列処理は避ける
- ❌ **メモリアロケーション**: 大きなオブジェクト生成は避ける

---

### Layer 4: Domain (oiduna_scheduler)

**目的**: メッセージスケジューリング、ルーティングロジック

#### 拡張ポイント

| 拡張ポイント | 対応するFastAPI機能 | 実装場所 | 難易度 |
|------------|-------------------|---------|--------|
| カスタムスケジューリング | - (内部Logic) | Custom Scheduler | ⭐⭐⭐⭐ |
| メッセージルーティング | - (内部Logic) | Custom Router | ⭐⭐⭐⭐ |

このレイヤーは拡張より、Oidunaコアへの貢献が望ましい。

#### 実装例

**カスタムスケジューリングロジック (高度)**

```python
# oiduna_extension_myext/scheduler.py

from oiduna_scheduler.scheduler_models import ScheduledMessage

class MyExtScheduler:
    """カスタムスケジューリングロジック"""

    def schedule_with_swing(
        self,
        messages: list[ScheduledMessage],
        swing_amount: float = 0.1
    ) -> list[ScheduledMessage]:
        """
        スウィング感を追加するスケジューラー

        偶数ステップを遅らせることでスウィングを実現
        """
        modified = []

        for msg in messages:
            if msg.step % 2 == 0:
                # 偶数ステップを遅延
                # 注: これは概念的な例、実際はタイミング制御が必要
                modified.append(msg)
            else:
                modified.append(msg)

        return modified
```

このレイヤーの拡張は非常に高度で、Oidunaの内部アーキテクチャへの深い理解が必要。

#### ベストプラクティス

- ✅ **コア貢献**: 汎用的な機能はOidunaコアへPRを推奨
- ✅ **プロトコル準拠**: `ScheduledMessage`等の既存モデルを尊重
- ❌ **独自実装**: よほどの理由がない限り、このレイヤーは拡張しない

---

### Layer 5: Data (oiduna_models - Foundation)

**目的**: データモデル定義、データストア

#### 拡張ポイント

| 拡張ポイント | 対応するFastAPI機能 | 実装場所 | 難易度 |
|------------|-------------------|---------|--------|
| カスタムモデル | `Pydantic BaseModel` | Custom Model | ⭐⭐ |
| Destination定義 | `DestinationConfig` | Custom Config | ⭐⭐ |

#### 実装例

**1. カスタムDestinationモデル**

```python
# oiduna_extension_myext/models.py

from pydantic import BaseModel, Field
from oiduna_models import DestinationConfig

class MyExtDestinationConfig(DestinationConfig):
    """MyExt用のdestination設定"""

    type: str = Field(default="myext", frozen=True)
    host: str = Field(default="localhost")
    port: int = Field(default=9999, gt=0, lt=65536)

    # カスタムフィールド
    protocol: str = Field(default="udp", pattern="^(tcp|udp)$")
    buffer_size: int = Field(default=1024, gt=0)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "myext1",
                "type": "myext",
                "host": "localhost",
                "port": 9999,
                "protocol": "udp",
                "buffer_size": 2048
            }
        }
```

**2. カスタムパラメータモデル**

```python
# oiduna_extension_myext/params.py

from pydantic import BaseModel, Field
from typing import Literal

class MyExtParams(BaseModel):
    """MyExt destination用のパラメータモデル"""

    # 必須パラメータ
    note: int = Field(..., ge=0, le=127, description="MIDI note number")

    # オプションパラメータ
    velocity: int = Field(default=100, ge=0, le=127)
    duration: float = Field(default=1.0, gt=0.0)

    # カスタムパラメータ
    waveform: Literal["sine", "square", "saw", "triangle"] = "sine"
    filter_cutoff: float = Field(default=1000.0, ge=20.0, le=20000.0)

    class Config:
        json_schema_extra = {
            "example": {
                "note": 60,
                "velocity": 100,
                "duration": 1.0,
                "waveform": "sine",
                "filter_cutoff": 1000.0
            }
        }
```

**3. destinations.yaml統合**

```yaml
# destinations.yaml

myext1:
  type: myext
  host: localhost
  port: 9999
  protocol: udp
  buffer_size: 2048

myext2:
  type: myext
  host: 192.168.1.100
  port: 10000
  protocol: tcp
  buffer_size: 4096
```

#### ベストプラクティス

- ✅ **Pydantic活用**: バリデーション、シリアライゼーションを自動化
- ✅ **型安全性**: `Field()`で制約を明示
- ✅ **ドキュメント**: `description`, `json_schema_extra`で説明を追加
- ❌ **任意dict**: `dict[str, Any]`の多用は避け、明示的なモデルを定義

---

## FastAPI機能とレイヤーの対応

### 機能別対応表

| FastAPI機能 | 主な使用レイヤー | 用途 | 実装場所 |
|-----------|------------|-----|---------|
| **APIRouter** | Layer 1 | エンドポイントグルーピング | `BaseExtension.get_router()` |
| **Middleware** | Layer 1 | リクエスト/レスポンス処理 | FastAPI app |
| **Dependencies** | Layer 1, 2 | 依存性注入 | Router, Endpoint |
| **Background Tasks** | Layer 2 | 非同期処理 | Endpoint |
| **Lifespan Events** | Layer 1, 3 | 起動/終了処理 | `BaseExtension.startup/shutdown()` |
| **WebSocket** | Layer 1 | リアルタイム通信 | Custom Router |
| **SSE** | Layer 1 | イベントストリーミング | Custom Router |
| **Exception Handlers** | Layer 1 | エラー処理 | FastAPI app |
| **Custom Response** | Layer 1 | レスポンス形式カスタマイズ | Endpoint |
| **Security** | Layer 1, 2 | 認証・認可 | Dependencies |

### 推奨される実装パターン

```python
# 完全な拡張実装例

from fastapi import APIRouter, Depends, BackgroundTasks, WebSocket
from oiduna_api.extensions import BaseExtension
from oiduna_api.dependencies import get_container
from oiduna_session import SessionContainer
from typing import Any

class ComprehensiveExtension(BaseExtension):
    """
    全機能を統合した拡張例

    - Layer 1: カスタムエンドポイント (Router)
    - Layer 2: セッション変換 (transform)
    - Layer 3: ランタイムフック (before_send_messages)
    """

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self.state = {"message_count": 0}

    # ========================================
    # Layer 1: API (エンドポイント)
    # ========================================

    def get_router(self) -> APIRouter:
        """カスタムエンドポイントを提供"""
        router = APIRouter(prefix="/comprehensive", tags=["comprehensive"])

        # 1. シンプルなGETエンドポイント
        @router.get("/status")
        def get_status():
            return {
                "extension": "comprehensive",
                "state": self.state
            }

        # 2. SessionContainer統合
        @router.get("/session/stats")
        def get_session_stats(
            container: SessionContainer = Depends(get_container)
        ):
            return {
                "tracks": len(container.tracks.list()),
                "patterns": len(container.patterns.list()),
                "clients": len(container.clients.list())
            }

        # 3. BackgroundTasks
        @router.post("/process")
        async def process_data(
            background_tasks: BackgroundTasks,
            data: dict
        ):
            background_tasks.add_task(self._process_in_background, data)
            return {"status": "accepted"}

        # 4. WebSocket
        @router.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            await websocket.send_json({"type": "connected"})

            try:
                while True:
                    data = await websocket.receive_json()
                    await websocket.send_json({
                        "type": "echo",
                        "data": data
                    })
            except:
                pass

        return router

    # ========================================
    # Layer 2: Application (セッション変換)
    # ========================================

    def transform(self, payload: dict) -> dict:
        """セッションロード時の変換 (HTTP requestパス)"""
        messages = payload.get("messages", [])

        for msg in messages:
            if msg.get("destination_id") == "comprehensive":
                params = msg.get("params", {})

                # パラメータ追加・変換
                params["_ext_version"] = "1.0.0"
                params["_processed"] = True

                # noteのtranspose
                if "note" in params:
                    transpose = self.config.get("transpose", 0)
                    params["note"] = params["note"] + transpose

        return payload

    # ========================================
    # Layer 3: Core (ランタイムフック)
    # ========================================

    def before_send_messages(
        self,
        messages: list[Any],
        current_bpm: float,
        current_step: int
    ) -> list[Any]:
        """
        メッセージ送信直前の変換 (タイミングループ内)

        警告: 超高速処理が必須 (< 100μs)
        """
        # cps計算
        cps = current_bpm / 60.0 / 4.0

        # 軽量な変換のみ
        modified = [
            msg.replace(params={**msg.params, "cps": cps, "step": current_step})
            if msg.destination_id == "comprehensive"
            else msg
            for msg in messages
        ]

        # 統計更新 (軽量)
        self.state["message_count"] += len(messages)

        return modified

    # ========================================
    # Lifespan (起動/終了)
    # ========================================

    def startup(self):
        """起動時処理"""
        print("Comprehensive Extension: Starting up")
        # リソース初期化
        self.state["started_at"] = "2024-01-01T00:00:00Z"

    def shutdown(self):
        """終了時処理"""
        print("Comprehensive Extension: Shutting down")
        # リソースクリーンアップ
        self.state.clear()

    # ========================================
    # Private Methods
    # ========================================

    def _process_in_background(self, data: dict):
        """バックグラウンド処理 (重い処理OK)"""
        import time
        time.sleep(2)  # 重い処理のシミュレーション
        print(f"Processed: {data}")
```

---

## 具体的な実装例

### 例1: SuperDirt拡張 (実用例)

```python
# oiduna_extension_superdirt/__init__.py

from oiduna_api.extensions import BaseExtension
from fastapi import APIRouter
from typing import Any

class SuperDirtExtension(BaseExtension):
    """
    SuperDirt用の拡張

    - cpsパラメータを自動注入
    - orbit管理エンドポイント
    - SuperDirt固有のパラメータ検証
    """

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self.orbit_count = config.get("orbit_count", 12) if config else 12

    def transform(self, payload: dict) -> dict:
        """SuperDirt固有のパラメータ検証"""
        messages = payload.get("messages", [])

        for msg in messages:
            if msg.get("destination_id") == "superdirt":
                params = msg.get("params", {})

                # orbitの検証
                orbit = params.get("orbit", 0)
                if orbit >= self.orbit_count:
                    raise ValueError(
                        f"orbit {orbit} exceeds limit {self.orbit_count}"
                    )

                # デフォルト値設定
                params.setdefault("gain", 1.0)
                params.setdefault("pan", 0.5)

        return payload

    def before_send_messages(
        self,
        messages: list[Any],
        current_bpm: float,
        current_step: int
    ) -> list[Any]:
        """cpsパラメータを自動注入"""
        cps = current_bpm / 60.0 / 4.0

        return [
            msg.replace(params={**msg.params, "cps": cps})
            if msg.destination_id == "superdirt"
            else msg
            for msg in messages
        ]

    def get_router(self) -> APIRouter:
        """SuperDirt管理エンドポイント"""
        router = APIRouter(prefix="/superdirt", tags=["superdirt"])

        @router.get("/orbits")
        def list_orbits():
            """利用可能なorbitをリスト"""
            return {
                "orbit_count": self.orbit_count,
                "orbits": list(range(self.orbit_count))
            }

        @router.post("/panic")
        def panic_all_orbits():
            """全orbitをミュート (panic)"""
            # LoopServiceにpanic commandを送信
            # (実装は省略)
            return {"status": "panic_sent"}

        return router
```

### 例2: MIDI拡張

```python
# oiduna_extension_midi/__init__.py

from oiduna_api.extensions import BaseExtension
from fastapi import APIRouter, HTTPException
from typing import Any

class MidiExtension(BaseExtension):
    """
    MIDI拡張

    - MIDIチャンネル検証
    - CCメッセージサポート
    - MIDI panic機能
    """

    def transform(self, payload: dict) -> dict:
        """MIDI固有の検証"""
        messages = payload.get("messages", [])

        for msg in messages:
            if msg.get("destination_id", "").startswith("midi"):
                params = msg.get("params", {})

                # MIDI範囲検証
                if "note" in params:
                    note = params["note"]
                    if not (0 <= note <= 127):
                        raise ValueError(f"MIDI note {note} out of range [0, 127]")

                if "velocity" in params:
                    vel = params["velocity"]
                    if not (0 <= vel <= 127):
                        raise ValueError(f"velocity {vel} out of range [0, 127]")

                # channelのデフォルト値
                params.setdefault("channel", 0)

        return payload

    def get_router(self) -> APIRouter:
        """MIDI管理エンドポイント"""
        router = APIRouter(prefix="/midi", tags=["midi"])

        @router.get("/ports")
        def list_midi_ports():
            """利用可能なMIDIポートをリスト"""
            # MidiSenderからポート情報を取得
            # (実装は省略)
            return {
                "ports": ["IAC Driver Bus 1", "MIDI Monitor"]
            }

        @router.post("/cc")
        def send_cc(channel: int, cc: int, value: int):
            """CCメッセージを送信"""
            if not (0 <= channel <= 15):
                raise HTTPException(400, "channel out of range")
            if not (0 <= cc <= 127):
                raise HTTPException(400, "cc out of range")
            if not (0 <= value <= 127):
                raise HTTPException(400, "value out of range")

            # 実装省略
            return {"status": "sent", "channel": channel, "cc": cc, "value": value}

        return router
```

### 例3: Analytics拡張 (統計収集)

```python
# oiduna_extension_analytics/__init__.py

from oiduna_api.extensions import BaseExtension
from fastapi import APIRouter
from collections import defaultdict
from typing import Any
import time

class AnalyticsExtension(BaseExtension):
    """
    統計収集拡張

    - メッセージ送信回数をカウント
    - destination別統計
    - パフォーマンス測定
    """

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self.stats = {
            "total_messages": 0,
            "by_destination": defaultdict(int),
            "by_step": defaultdict(int),
            "started_at": None
        }

    def startup(self):
        """統計初期化"""
        self.stats["started_at"] = time.time()
        print("Analytics: Started collecting stats")

    def before_send_messages(
        self,
        messages: list[Any],
        current_bpm: float,
        current_step: int
    ) -> list[Any]:
        """統計収集 (軽量処理のみ)"""
        # メッセージカウント
        self.stats["total_messages"] += len(messages)

        # destination別
        for msg in messages:
            self.stats["by_destination"][msg.destination_id] += 1

        # step別
        self.stats["by_step"][current_step] += 1

        # 変更なし
        return messages

    def get_router(self) -> APIRouter:
        """統計エンドポイント"""
        router = APIRouter(prefix="/analytics", tags=["analytics"])

        @router.get("/stats")
        def get_stats():
            """統計情報を取得"""
            uptime = time.time() - self.stats["started_at"]

            return {
                "uptime_seconds": uptime,
                "total_messages": self.stats["total_messages"],
                "messages_per_second": self.stats["total_messages"] / uptime,
                "by_destination": dict(self.stats["by_destination"]),
                "most_active_step": max(
                    self.stats["by_step"].items(),
                    key=lambda x: x[1],
                    default=(None, 0)
                )[0]
            }

        @router.post("/reset")
        def reset_stats():
            """統計をリセット"""
            self.stats["total_messages"] = 0
            self.stats["by_destination"].clear()
            self.stats["by_step"].clear()
            self.stats["started_at"] = time.time()
            return {"status": "reset"}

        return router
```

---

## ベストプラクティス

### 全般

1. **レイヤー原則を守る**
   - 下位レイヤーのみに依存
   - レイヤースキップは避ける
   - 同一レイヤー内の水平依存は避ける

2. **FastAPI機能を適切に選択**
   - Router: Layer 1のエンドポイント追加
   - Dependencies: Layer 1-2の依存性注入
   - Middleware: Layer 1のグローバル処理
   - Background Tasks: Layer 2の重い処理

3. **パフォーマンスを意識**
   - `transform()`: 軽量 (< 10ms)
   - `before_send_messages()`: 超軽量 (< 100μs)
   - 重い処理は`BackgroundTasks`へ

### Layer 1 (API)

- ✅ `get_router()`でエンドポイント提供
- ✅ `Depends()`で依存性注入
- ✅ Pydanticでリクエスト/レスポンス検証
- ❌ ビジネスロジックをエンドポイントに書かない

### Layer 2 (Application)

- ✅ `transform()`でセッション変換
- ✅ `SessionContainer`へは`Depends(get_container)`でアクセス
- ✅ バリデーションエラーは適切に`raise`
- ❌ I/O処理はtransform()内で行わない

### Layer 3 (Core)

- ✅ `before_send_messages()`は最小限の処理
- ✅ イミュータブル更新 (`msg.replace()`)
- ✅ 早期return (destination_idでフィルタ)
- ❌ ログ出力、ファイルI/O、ネットワーク通信は禁止

### Layer 4-5 (Domain/Data)

- ✅ Pydanticでモデル定義
- ✅ `DestinationConfig`を継承
- ✅ バリデーション制約を明示 (`Field()`)
- ❌ 安易に`dict[str, Any]`を使わない

---

## 参考資料

### 公式ドキュメント

- [ADR-0006: Extension Mechanism](./decisions/) (予定)
- [EXTENSION_DEVELOPMENT_GUIDE.md](../EXTENSION_DEVELOPMENT_GUIDE.md)
- [ARCHITECTURE.md](../ARCHITECTURE.md)

### アーキテクチャドキュメント

- [README.md](./README.md) - アーキテクチャ概要
- [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - クイックリファレンス
- [layer-1-api.md](./layer-1-api.md) - Layer 1詳細
- [layer-2-application.md](./layer-2-application.md) - Layer 2詳細
- [layer-3-core.md](./layer-3-core.md) - Layer 3詳細
- [layer-4-domain.md](./layer-4-domain.md) - Layer 4詳細
- [layer-5-data.md](./layer-5-data.md) - Layer 5詳細

### FastAPI公式

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

---

## まとめ

### 拡張タイプ別の実装推奨

| やりたいこと | 実装レイヤー | 主な機能 |
|-----------|----------|---------|
| カスタムHTTPエンドポイント | Layer 1 | `get_router()` |
| WebSocket/SSE | Layer 1 | `APIRouter`, `WebSocket` |
| セッションペイロード変換 | Layer 2 | `transform()` |
| 認証・認可 | Layer 1-2 | `Security`, `Depends` |
| ランタイムメッセージ変換 | Layer 3 | `before_send_messages()` |
| カスタムdestination | Layer 5 | `DestinationConfig` |
| 統計収集・分析 | Layer 1-3 | Router + Runtime Hook |
| バックグラウンド処理 | Layer 2 | `BackgroundTasks` |

### 開発フロー

1. **要件定義**: どのレイヤーで実装すべきか判断
2. **BaseExtension継承**: 必須メソッド `transform()` 実装
3. **オプション機能追加**: `get_router()`, `before_send_messages()` 等
4. **entry_points設定**: `pyproject.toml`
5. **テスト**: 単体テスト、統合テスト
6. **パフォーマンス測定**: 特に`before_send_messages()`
7. **ドキュメント**: README, サンプルコード

このガイドを参考に、適切なレイヤーで効率的な拡張を開発してください。

---

**最終更新**: 2026-03-01
**対応バージョン**: Oiduna 0.1.0
**関連ADR**: ADR-0006 (Extension Mechanism)
