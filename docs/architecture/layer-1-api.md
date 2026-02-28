# Layer 1: API層 (HTTP Interface)

**パッケージ**: `oiduna_api`

**最終更新**: 2026-03-01

---

## 概要

API層は、HTTP REST APIエンドポイントを提供します。FastAPIによる薄いHTTPラッパーとして機能し、ビジネスロジックはすべてLayer 2（Application層）に委譲します。MARSなどの外部システムはこの層に直接接続します。

### 責任

- ✅ HTTPエンドポイント提供
- ✅ リクエスト検証（Pydantic）
- ✅ レスポンスシリアライズ
- ✅ SSEストリーミング
- ✅ FastAPI依存性注入
- ❌ ビジネスロジック（Layer 2に任せる）
- ❌ データ永続化（Layer 5に任せる）

### 依存関係

```
oiduna_api → session, loop, auth, models, destination
```

**設計原則**: API層は薄いラッパーのみ。ビジネスロジックは含まない。

---

## ディレクトリ構造

```
oiduna_api/
├── __init__.py
├── main.py                # FastAPIアプリケーション
├── dependencies.py        # 依存性注入
└── routes/
    ├── __init__.py
    ├── clients.py         # /clients/*
    ├── tracks.py          # /tracks/*
    ├── patterns.py        # /tracks/{track_id}/patterns/*
    ├── session.py         # /session/*
    ├── playback.py        # /playback/*
    └── stream.py          # /stream (SSE)
```

---

## main.py: FastAPIアプリケーション

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from oiduna_api.routes import (
    clients,
    tracks,
    patterns,
    session,
    playback,
    stream
)

app = FastAPI(
    title="Oiduna API",
    description="Real-time live coding sequencer",
    version="0.1.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーター登録
app.include_router(clients.router, prefix="/clients", tags=["Clients"])
app.include_router(tracks.router, prefix="/tracks", tags=["Tracks"])
app.include_router(patterns.router, prefix="/tracks", tags=["Patterns"])
app.include_router(session.router, prefix="/session", tags=["Session"])
app.include_router(playback.router, prefix="/playback", tags=["Playback"])
app.include_router(stream.router, tags=["Stream"])

@app.get("/")
async def root():
    """ヘルスチェック"""
    return {"status": "ok", "message": "Oiduna API is running"}
```

---

## dependencies.py: 依存性注入

SessionContainerとLoopEngineをシングルトンとして管理。

```python
from functools import lru_cache
from oiduna_session import SessionContainer
from oiduna_loop import LoopEngine, LoopEngineFactory
from oiduna_destination import OscDestinationConfig

# シングルトンインスタンス
_container: Optional[SessionContainer] = None
_loop_engine: Optional[LoopEngine] = None

@lru_cache()
def get_container() -> SessionContainer:
    """SessionContainerのシングルトン取得"""
    global _container
    if _container is None:
        _container = SessionContainer()

        # デフォルトデスティネーション追加
        superdirt = OscDestinationConfig(
            id="superdirt",
            type="osc",
            host="127.0.0.1",
            port=57120,
            address="/dirt/play"
        )
        _container.destinations.add(superdirt)

    return _container

@lru_cache()
def get_loop_engine() -> LoopEngine:
    """LoopEngineのシングルトン取得"""
    global _loop_engine
    if _loop_engine is None:
        container = get_container()
        _loop_engine = LoopEngineFactory.create_production(
            destinations=container.session.destinations
        )

    return _loop_engine
```

---

## routes/clients.py: クライアント管理エンドポイント

```python
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from oiduna_session import SessionContainer
from oiduna_api.dependencies import get_container
from oiduna_auth.dependencies import verify_admin

router = APIRouter()

class ClientCreateRequest(BaseModel):
    """クライアント作成リクエスト"""
    client_name: str
    client_type: str = "mars"

class ClientCreateResponse(BaseModel):
    """クライアント作成レスポンス"""
    client_id: str
    client_name: str
    token: str

@router.post("/{client_id}", response_model=ClientCreateResponse)
async def create_client(
    client_id: str,
    request: ClientCreateRequest,
    container: SessionContainer = Depends(get_container)
):
    """クライアント作成（トークン発行）"""
    try:
        client = container.clients.create(
            client_id=client_id,
            client_name=request.client_name,
            client_type=request.client_type
        )

        return ClientCreateResponse(
            client_id=client.client_id,
            client_name=client.client_name,
            token=client.token
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{client_id}")
async def get_client(
    client_id: str,
    container: SessionContainer = Depends(get_container)
):
    """クライアント取得（トークンは返さない）"""
    try:
        client = container.clients.get(client_id)
        return {
            "client_id": client.client_id,
            "client_name": client.client_name,
            "client_type": client.client_type,
            "created_at": client.created_at
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{client_id}")
async def delete_client(
    client_id: str,
    _: None = Depends(verify_admin),  # Admin権限必須
    container: SessionContainer = Depends(get_container)
):
    """クライアント削除（Admin専用）"""
    try:
        container.clients.delete(client_id)
        return {"message": f"Client {client_id} deleted"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

---

## routes/tracks.py: トラック管理エンドポイント

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from oiduna_session import SessionContainer
from oiduna_api.dependencies import get_container
from oiduna_auth.dependencies import verify_client_token

router = APIRouter()

class TrackCreateRequest(BaseModel):
    """トラック作成リクエスト"""
    track_name: str
    destination_id: str
    base_params: dict[str, Any] = {}

@router.post("/{track_id}")
async def create_track(
    track_id: str,
    request: TrackCreateRequest,
    client_id: str = Depends(verify_client_token),  # 認証必須
    container: SessionContainer = Depends(get_container)
):
    """トラック作成"""
    try:
        track = container.tracks.create(
            track_id=track_id,
            track_name=request.track_name,
            destination_id=request.destination_id,
            client_id=client_id,
            base_params=request.base_params
        )

        return {
            "track_id": track.track_id,
            "track_name": track.track_name,
            "destination_id": track.destination_id,
            "base_params": track.base_params
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{track_id}")
async def get_track(
    track_id: str,
    container: SessionContainer = Depends(get_container)
):
    """トラック取得"""
    try:
        track = container.tracks.get(track_id)
        return {
            "track_id": track.track_id,
            "track_name": track.track_name,
            "destination_id": track.destination_id,
            "client_id": track.client_id,
            "base_params": track.base_params,
            "patterns": {
                pid: {
                    "pattern_id": p.pattern_id,
                    "pattern_name": p.pattern_name,
                    "active": p.active,
                    "event_count": len(p.events)
                }
                for pid, p in track.patterns.items()
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.patch("/{track_id}/base_params")
async def update_base_params(
    track_id: str,
    request: dict[str, Any],
    client_id: str = Depends(verify_client_token),
    container: SessionContainer = Depends(get_container)
):
    """base_params更新"""
    try:
        # トラックの所有者確認
        track = container.tracks.get(track_id)
        if track.client_id != client_id:
            raise HTTPException(status_code=403, detail="Not your track")

        updated = container.tracks.update_base_params(
            track_id=track_id,
            base_params=request
        )

        return {"base_params": updated.base_params}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{track_id}")
async def delete_track(
    track_id: str,
    client_id: str = Depends(verify_client_token),
    container: SessionContainer = Depends(get_container)
):
    """トラック削除"""
    try:
        track = container.tracks.get(track_id)
        if track.client_id != client_id:
            raise HTTPException(status_code=403, detail="Not your track")

        container.tracks.delete(track_id)
        return {"message": f"Track {track_id} deleted"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

---

## routes/patterns.py: パターン管理エンドポイント

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from oiduna_session import SessionContainer
from oiduna_api.dependencies import get_container
from oiduna_auth.dependencies import verify_client_token

router = APIRouter()

class PatternCreateRequest(BaseModel):
    """パターン作成リクエスト"""
    pattern_name: str

class EventAddRequest(BaseModel):
    """イベント追加リクエスト"""
    step: int
    cycle: float
    params: dict[str, Any] = {}

@router.post("/{track_id}/patterns/{pattern_id}")
async def create_pattern(
    track_id: str,
    pattern_id: str,
    request: PatternCreateRequest,
    client_id: str = Depends(verify_client_token),
    container: SessionContainer = Depends(get_container)
):
    """パターン作成"""
    try:
        # トラック所有者確認
        track = container.tracks.get(track_id)
        if track.client_id != client_id:
            raise HTTPException(status_code=403, detail="Not your track")

        pattern = container.patterns.create(
            track_id=track_id,
            pattern_id=pattern_id,
            pattern_name=request.pattern_name
        )

        return {
            "pattern_id": pattern.pattern_id,
            "pattern_name": pattern.pattern_name,
            "active": pattern.active
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{track_id}/patterns/{pattern_id}/events")
async def add_event(
    track_id: str,
    pattern_id: str,
    request: EventAddRequest,
    client_id: str = Depends(verify_client_token),
    container: SessionContainer = Depends(get_container)
):
    """イベント追加"""
    try:
        track = container.tracks.get(track_id)
        if track.client_id != client_id:
            raise HTTPException(status_code=403, detail="Not your track")

        event = container.patterns.add_event(
            track_id=track_id,
            pattern_id=pattern_id,
            step=request.step,
            cycle=request.cycle,
            params=request.params
        )

        return {
            "step": event.step,
            "cycle": event.cycle,
            "params": event.params
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/{track_id}/patterns/{pattern_id}/active")
async def set_pattern_active(
    track_id: str,
    pattern_id: str,
    active: bool,
    client_id: str = Depends(verify_client_token),
    container: SessionContainer = Depends(get_container)
):
    """パターンのアクティブ状態変更"""
    try:
        track = container.tracks.get(track_id)
        if track.client_id != client_id:
            raise HTTPException(status_code=403, detail="Not your track")

        pattern = container.patterns.set_active(
            track_id=track_id,
            pattern_id=pattern_id,
            active=active
        )

        return {"active": pattern.active}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

---

## routes/session.py: セッション状態取得

```python
from fastapi import APIRouter, Depends
from oiduna_session import SessionContainer
from oiduna_api.dependencies import get_container

router = APIRouter()

@router.get("/")
async def get_session(
    container: SessionContainer = Depends(get_container)
):
    """セッション全体の状態取得"""
    return container.get_state()

@router.get("/clients")
async def list_clients(
    container: SessionContainer = Depends(get_container)
):
    """クライアント一覧"""
    return {
        "clients": [
            {
                "client_id": c.client_id,
                "client_name": c.client_name,
                "client_type": c.client_type
            }
            for c in container.session.clients.values()
        ]
    }

@router.get("/tracks")
async def list_tracks(
    container: SessionContainer = Depends(get_container)
):
    """トラック一覧"""
    return {
        "tracks": [
            {
                "track_id": t.track_id,
                "track_name": t.track_name,
                "destination_id": t.destination_id,
                "client_id": t.client_id,
                "pattern_count": len(t.patterns)
            }
            for t in container.session.tracks.values()
        ]
    }

@router.get("/destinations")
async def list_destinations(
    container: SessionContainer = Depends(get_container)
):
    """デスティネーション一覧"""
    return {
        "destinations": [
            {
                "id": d.id,
                "type": d.type,
                "host": getattr(d, "host", None),
                "port": getattr(d, "port", None),
            }
            for d in container.session.destinations.values()
        ]
    }
```

---

## routes/playback.py: 再生制御

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from oiduna_session import SessionContainer, SessionCompiler
from oiduna_scheduler import MessageScheduler
from oiduna_loop import LoopEngine
from oiduna_api.dependencies import get_container, get_loop_engine

router = APIRouter()

class PlaybackSessionRequest(BaseModel):
    """セッション再生リクエスト（MARS用）"""
    messages: list[dict]
    bpm: float
    pattern_length: float

@router.post("/start")
async def start_playback(
    container: SessionContainer = Depends(get_container),
    engine: LoopEngine = Depends(get_loop_engine)
):
    """再生開始（現在のセッションをコンパイル）"""
    try:
        # SessionをScheduledMessageBatchに変換
        batch = SessionCompiler.compile(container.session)

        # Schedulerを作成してLoopEngineと同期
        scheduler = MessageScheduler(batch)
        await engine.sync(scheduler)

        # ループ開始
        await engine.start()

        return {"status": "playing"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/session")
async def play_session(
    request: PlaybackSessionRequest,
    engine: LoopEngine = Depends(get_loop_engine)
):
    """セッション再生（MARS直接送信用）"""
    from oiduna_scheduler import ScheduledMessageBatch, ScheduledMessage

    try:
        # JSON → ScheduledMessageBatch変換
        messages = tuple(
            ScheduledMessage(**msg)
            for msg in request.messages
        )

        batch = ScheduledMessageBatch(
            messages=messages,
            bpm=request.bpm,
            pattern_length=request.pattern_length
        )

        # Schedulerと同期
        scheduler = MessageScheduler(batch)
        await engine.sync(scheduler)

        return {"status": "synced"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/stop")
async def stop_playback(
    engine: LoopEngine = Depends(get_loop_engine)
):
    """再生停止"""
    await engine.stop()
    return {"status": "stopped"}

@router.post("/bpm")
async def set_bpm(
    bpm: float,
    container: SessionContainer = Depends(get_container),
    engine: LoopEngine = Depends(get_loop_engine)
):
    """BPM変更"""
    try:
        container.session.environment.bpm = bpm
        engine.clock.set_bpm(bpm)
        return {"bpm": bpm}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

---

## routes/stream.py: SSEストリーム

Server-Sent Events (SSE)でリアルタイム状態配信。

```python
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from oiduna_loop import LoopEngine
from oiduna_api.dependencies import get_loop_engine
import asyncio
import json

router = APIRouter()

@router.get("/stream")
async def stream(
    engine: LoopEngine = Depends(get_loop_engine)
):
    """SSEストリーム（リアルタイム状態配信）"""

    async def event_generator():
        while True:
            # LoopEngineの状態を取得
            state = {
                "playing": engine.state.playing,
                "current_step": engine.state.current_step,
                "bpm": engine.state.bpm,
                "loop_count": engine.state.loop_count
            }

            # SSE形式で送信
            yield f"data: {json.dumps(state)}\n\n"

            # 100msごとに更新
            await asyncio.sleep(0.1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

**クライアント側（JavaScript）**:
```javascript
const eventSource = new EventSource('http://localhost:57122/stream');

eventSource.onmessage = (event) => {
    const state = JSON.parse(event.data);
    console.log(`Step: ${state.current_step}, BPM: ${state.bpm}`);
};
```

---

## エラーハンドリング

### HTTPException変換

```python
# Layer 3のValueErrorをHTTP 400に変換
try:
    container.tracks.create(...)
except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
```

### カスタムエラーレスポンス

```python
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)}
    )
```

---

## Rust移植の考慮事項

### 優先度: 低 🔷

Python FastAPIが成熟しており、HTTP処理は移植優先度が低い。

### Rust実装の方針（将来的）

```rust
use axum::{
    Router,
    routing::{get, post},
    extract::{State, Path},
    Json,
};
use serde::{Deserialize, Serialize};

#[derive(Deserialize)]
struct TrackCreateRequest {
    track_name: String,
    destination_id: String,
    base_params: HashMap<String, serde_json::Value>,
}

async fn create_track(
    Path(track_id): Path<String>,
    State(container): State<Arc<SessionContainer>>,
    Json(request): Json<TrackCreateRequest>,
) -> Result<Json<Track>, StatusCode> {
    container.tracks.create(
        track_id,
        request.track_name,
        request.destination_id,
    ).map(Json)
      .map_err(|_| StatusCode::BAD_REQUEST)
}

let app = Router::new()
    .route("/tracks/:track_id", post(create_track))
    .with_state(container);
```

---

## テスト例

```python
from fastapi.testclient import TestClient
from oiduna_api.main import app

client = TestClient(app)

def test_create_client():
    """クライアント作成のテスト"""
    response = client.post(
        "/clients/alice",
        json={"client_name": "Alice", "client_type": "mars"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["client_id"] == "alice"
    assert "token" in data

def test_create_track_with_auth():
    """認証付きトラック作成"""
    # クライアント作成
    response = client.post(
        "/clients/alice",
        json={"client_name": "Alice"}
    )
    token = response.json()["token"]

    # トラック作成（認証ヘッダー付き）
    response = client.post(
        "/tracks/kick",
        headers={
            "X-Client-ID": "alice",
            "X-Client-Token": token
        },
        json={
            "track_name": "Kick",
            "destination_id": "superdirt"
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["track_id"] == "kick"

def test_create_track_without_auth_fails():
    """認証なしでトラック作成は失敗"""
    response = client.post(
        "/tracks/kick",
        json={"track_name": "Kick", "destination_id": "superdirt"}
    )

    assert response.status_code == 403
```

---

## OpenAPI自動生成

FastAPIは自動的にOpenAPIスキーマを生成します。

```bash
# サーバー起動
uv run uvicorn oiduna_api.main:app --reload

# ブラウザで確認
open http://localhost:57122/docs
```

### Swagger UI機能

- 全エンドポイント一覧
- リクエスト/レスポンススキーマ
- インタラクティブなAPI実行
- 認証ヘッダー設定

---

## まとめ

### API層の重要性

1. **薄いHTTPラッパー**: ビジネスロジックは含まない
2. **FastAPI依存性注入**: シングルトン管理
3. **自動バリデーション**: Pydanticモデル
4. **OpenAPI自動生成**: ドキュメント不要

### 設計判断

- **エンドポイント設計**: RESTful
- **認証**: ヘッダーベース（X-Client-ID + X-Client-Token）
- **エラーハンドリング**: ValueError → HTTP 400
- **SSE**: リアルタイム状態配信

### 次のステップ

API層を理解したら：
1. [External Interface: クライアント層](./external-interface.md)でクライアント実装を学ぶ
2. [Layer 2: アプリケーション層](./layer-2-application.md)でビジネスロジックを理解
3. [データフロー例](./data-flow-examples.md)で全体の流れを確認

---

**関連ドキュメント**:
- `packages/oiduna_api/README.md`
- FastAPI公式: https://fastapi.tiangolo.com/
- OpenAPI: http://localhost:57122/docs
