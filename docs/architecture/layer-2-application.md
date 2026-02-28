# Layer 2: アプリケーション層 (Business Logic)

**パッケージ**: `oiduna_session`, `oiduna_auth`

**最終更新**: 2026-03-01

---

## 概要

アプリケーション層は、ビジネスロジックと認証・認可を担当します。SessionContainer Patternによる明確な責任分離と、Silent Failure防止機能が特徴です。

### 責任

- ✅ セッション状態の管理（SessionContainer）
- ✅ Manager分離（Client, Track, Pattern, Destination）
- ✅ Silent Failure防止（作成時バリデーション）
- ✅ Session → ScheduledMessageBatch変換（SessionCompiler）
- ✅ 認証・認可ロジック
- ❌ HTTP通信（Layer 1に任せる）
- ❌ 実際の実行（Layer 3に任せる）

### 依存関係

```
oiduna_session → models, destination, scheduler
oiduna_auth → なし（完全に独立）
```

**設計原則**: アプリケーション層は下位層のみに依存し、API層やクライアント層には依存しない

---

## oiduna_session: セッション管理

### ディレクトリ構造

```
oiduna_session/
├── __init__.py
├── container.py          # SessionContainer（Facade）
├── compiler.py           # SessionCompiler
└── managers/
    ├── __init__.py
    ├── client_manager.py      # ClientManager
    ├── track_manager.py       # TrackManager
    ├── pattern_manager.py     # PatternManager
    └── destination_manager.py # DestinationManager
```

---

## SessionContainer: Facade Pattern

全マネージャーを統合する単一のインターフェース。

```python
class SessionContainer:
    """セッション全体を管理するFacade"""

    def __init__(self):
        self.session = Session()

        # 各Managerの初期化（依存関係に注意）
        self.destinations = DestinationManager(self.session)
        self.clients = ClientManager(self.session)
        self.tracks = TrackManager(self.session, self.destinations)
        self.patterns = PatternManager(self.session)

    def get_state(self) -> dict:
        """セッション全体の状態を取得"""
        return {
            "clients": {id: asdict(c) for id, c in self.session.clients.items()},
            "tracks": {id: asdict(t) for id, t in self.session.tracks.items()},
            "destinations": {id: asdict(d) for id, d in self.session.destinations.items()},
            "environment": asdict(self.session.environment)
        }
```

**使用例**:
```python
# コンテナ作成
container = SessionContainer()

# デスティネーション追加
dest = OscDestinationConfig(
    id="superdirt",
    type="osc",
    host="127.0.0.1",
    port=57120,
    address="/dirt/play"
)
container.destinations.add(dest)

# クライアント作成
client = container.clients.create("alice", "Alice", "mars")

# トラック作成
track = container.tracks.create(
    track_id="kick",
    track_name="Kick Drum",
    destination_id="superdirt",
    client_id="alice",
    base_params={"sound": "bd", "gain": 0.8}
)

# パターン作成
pattern = container.patterns.create(
    track_id="kick",
    pattern_id="main",
    pattern_name="Main Pattern"
)

# イベント追加
container.patterns.add_event(
    track_id="kick",
    pattern_id="main",
    step=0,
    cycle=0.0,
    params={}
)
```

---

## ClientManager: クライアント管理

クライアント登録と認証トークン管理。

```python
class ClientManager:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        client_id: str,
        client_name: str,
        client_type: str
    ) -> ClientInfo:
        """クライアント作成"""
        if client_id in self.session.clients:
            raise ValueError(f"Client {client_id} already exists")

        # トークン生成（UUID）
        token = str(uuid.uuid4())

        client = ClientInfo(
            client_id=client_id,
            client_name=client_name,
            client_type=client_type,
            token=token,
            created_at=datetime.now(timezone.utc).isoformat()
        )

        self.session.clients[client_id] = client
        return client

    def get(self, client_id: str) -> ClientInfo:
        """クライアント取得"""
        if client_id not in self.session.clients:
            raise ValueError(f"Client {client_id} not found")
        return self.session.clients[client_id]

    def delete(self, client_id: str) -> None:
        """クライアント削除"""
        if client_id not in self.session.clients:
            raise ValueError(f"Client {client_id} not found")

        # 使用中チェック（Silent Failure防止）
        using_tracks = [
            t.track_id
            for t in self.session.tracks.values()
            if t.client_id == client_id
        ]

        if using_tracks:
            raise ValueError(
                f"Cannot delete client {client_id}: "
                f"in use by tracks {using_tracks}"
            )

        del self.session.clients[client_id]

    def verify_token(self, client_id: str, token: str) -> bool:
        """トークン検証"""
        try:
            client = self.get(client_id)
            return client.token == token
        except ValueError:
            return False
```

---

## TrackManager: トラック管理

トラックの作成・削除・更新。

```python
class TrackManager:
    def __init__(
        self,
        session: Session,
        destination_manager: DestinationManager
    ):
        self.session = session
        self.destination_manager = destination_manager

    def create(
        self,
        track_id: str,
        track_name: str,
        destination_id: str,
        client_id: str,
        base_params: Optional[dict[str, Any]] = None
    ) -> Track:
        """トラック作成（Silent Failure防止）"""
        if track_id in self.session.tracks:
            raise ValueError(f"Track {track_id} already exists")

        # デスティネーション存在確認（Silent Failure防止）
        try:
            self.destination_manager.get(destination_id)
        except ValueError:
            available = list(self.session.destinations.keys())
            raise ValueError(
                f"Destination {destination_id} does not exist. "
                f"Available destinations: {available}"
            )

        # クライアント存在確認
        if client_id not in self.session.clients:
            raise ValueError(f"Client {client_id} not found")

        track = Track(
            track_id=track_id,
            track_name=track_name,
            destination_id=destination_id,
            client_id=client_id,
            base_params=base_params or {}
        )

        self.session.tracks[track_id] = track
        return track

    def update_base_params(
        self,
        track_id: str,
        base_params: dict[str, Any]
    ) -> Track:
        """base_params更新"""
        track = self.get(track_id)

        # 新しいTrackを作成（Pydanticモデルはイミュータブル）
        updated_track = Track(
            track_id=track.track_id,
            track_name=track.track_name,
            destination_id=track.destination_id,
            client_id=track.client_id,
            base_params=base_params,
            patterns=track.patterns
        )

        self.session.tracks[track_id] = updated_track
        return updated_track

    def delete(self, track_id: str) -> None:
        """トラック削除"""
        if track_id not in self.session.tracks:
            raise ValueError(f"Track {track_id} not found")

        del self.session.tracks[track_id]

    def get(self, track_id: str) -> Track:
        """トラック取得"""
        if track_id not in self.session.tracks:
            raise ValueError(f"Track {track_id} not found")
        return self.session.tracks[track_id]
```

---

## PatternManager: パターン管理

パターンとイベントの作成・更新・削除。

```python
class PatternManager:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        track_id: str,
        pattern_id: str,
        pattern_name: str
    ) -> Pattern:
        """パターン作成"""
        if track_id not in self.session.tracks:
            raise ValueError(f"Track {track_id} not found")

        track = self.session.tracks[track_id]

        if pattern_id in track.patterns:
            raise ValueError(
                f"Pattern {pattern_id} already exists in track {track_id}"
            )

        pattern = Pattern(
            pattern_id=pattern_id,
            pattern_name=pattern_name,
            active=True,
            events=[]
        )

        # 新しいTrackを作成（パターンを追加）
        updated_patterns = {**track.patterns, pattern_id: pattern}
        updated_track = Track(
            track_id=track.track_id,
            track_name=track.track_name,
            destination_id=track.destination_id,
            client_id=track.client_id,
            base_params=track.base_params,
            patterns=updated_patterns
        )

        self.session.tracks[track_id] = updated_track
        return pattern

    def add_event(
        self,
        track_id: str,
        pattern_id: str,
        step: int,
        cycle: float,
        params: Optional[dict[str, Any]] = None
    ) -> Event:
        """イベント追加"""
        track = self.session.tracks[track_id]
        pattern = track.patterns[pattern_id]

        event = Event(
            step=step,
            cycle=cycle,
            params=params or {}
        )

        # 新しいイベントリストを作成
        updated_events = list(pattern.events) + [event]

        # 新しいPatternを作成
        updated_pattern = Pattern(
            pattern_id=pattern.pattern_id,
            pattern_name=pattern.pattern_name,
            active=pattern.active,
            events=updated_events
        )

        # 新しいTrackを作成
        updated_patterns = {**track.patterns, pattern_id: updated_pattern}
        updated_track = Track(
            track_id=track.track_id,
            track_name=track.track_name,
            destination_id=track.destination_id,
            client_id=track.client_id,
            base_params=track.base_params,
            patterns=updated_patterns
        )

        self.session.tracks[track_id] = updated_track
        return event

    def set_active(
        self,
        track_id: str,
        pattern_id: str,
        active: bool
    ) -> Pattern:
        """パターンのアクティブ状態変更"""
        track = self.session.tracks[track_id]
        pattern = track.patterns[pattern_id]

        updated_pattern = Pattern(
            pattern_id=pattern.pattern_id,
            pattern_name=pattern.pattern_name,
            active=active,
            events=pattern.events
        )

        updated_patterns = {**track.patterns, pattern_id: updated_pattern}
        updated_track = Track(
            track_id=track.track_id,
            track_name=track.track_name,
            destination_id=track.destination_id,
            client_id=track.client_id,
            base_params=track.base_params,
            patterns=updated_patterns
        )

        self.session.tracks[track_id] = updated_track
        return updated_pattern
```

---

## DestinationManager: デスティネーション管理

送信先の追加・削除（使用中チェック付き）。

```python
class DestinationManager:
    def __init__(self, session: Session):
        self.session = session

    def add(self, destination: DestinationConfig) -> None:
        """デスティネーション追加"""
        if destination.id in self.session.destinations:
            raise ValueError(f"Destination {destination.id} already exists")

        self.session.destinations[destination.id] = destination

    def get(self, destination_id: str) -> DestinationConfig:
        """デスティネーション取得"""
        if destination_id not in self.session.destinations:
            raise ValueError(f"Destination {destination_id} not found")
        return self.session.destinations[destination_id]

    def remove(self, destination_id: str) -> None:
        """デスティネーション削除（Silent Failure防止）"""
        if destination_id not in self.session.destinations:
            raise ValueError(f"Destination {destination_id} not found")

        # 使用中チェック
        using_tracks = [
            f"{t.track_id} ({t.track_name})"
            for t in self.session.tracks.values()
            if t.destination_id == destination_id
        ]

        if using_tracks:
            available = [
                d.id for d in self.session.destinations.values()
                if d.id != destination_id
            ]
            raise ValueError(
                f"Cannot delete destination '{destination_id}': "
                f"in use by tracks: {', '.join(using_tracks)}. "
                f"Delete these tracks first or assign them to a different destination. "
                f"Available destinations: {available}"
            )

        del self.session.destinations[destination_id]
```

**Silent Failure防止の例**:
```python
# 旧システム（Silent Failure）
track.destination_id = "typo"  # 実行時まで気づかない

# 新システム（即座にエラー）
container.tracks.create(
    destination_id="typo"  # ValueError即座に発生
)
# ValueError: Destination typo does not exist.
# Available destinations: ['superdirt', 'volca']
```

---

## SessionCompiler: Session → ScheduledMessageBatch変換

セッション状態をスケジューラー用のフラット構造に変換。

```python
class SessionCompiler:
    @staticmethod
    def compile(session: Session) -> ScheduledMessageBatch:
        """SessionをScheduledMessageBatchに変換"""
        messages = []

        for track in session.tracks.values():
            for pattern in track.patterns.values():
                if not pattern.active:
                    continue

                for event in pattern.events:
                    # base_paramsとevent.paramsをマージ
                    merged_params = {
                        **track.base_params,
                        **event.params,
                        "track_id": track.track_id  # トラック情報を埋め込み
                    }

                    msg = ScheduledMessage(
                        destination_id=track.destination_id,
                        step=event.step,
                        cycle=event.cycle,
                        params=merged_params
                    )
                    messages.append(msg)

        return ScheduledMessageBatch(
            messages=tuple(messages),
            bpm=session.environment.bpm,
            pattern_length=4.0  # デフォルト16ビート
        )
```

**変換例**:
```python
# 入力: Session階層構造
Session(
    tracks={
        "kick": Track(
            destination_id="superdirt",
            base_params={"sound": "bd", "gain": 0.8},
            patterns={
                "main": Pattern(
                    active=True,
                    events=[
                        Event(step=0, cycle=0.0, params={}),
                        Event(step=64, cycle=1.0, params={"gain": 0.9})
                    ]
                )
            }
        )
    },
    environment=Environment(bpm=120.0)
)

# 出力: フラット構造
ScheduledMessageBatch(
    messages=(
        ScheduledMessage(
            destination_id="superdirt",
            step=0,
            cycle=0.0,
            params={"sound": "bd", "gain": 0.8, "track_id": "kick"}
        ),
        ScheduledMessage(
            destination_id="superdirt",
            step=64,
            cycle=1.0,
            params={"sound": "bd", "gain": 0.9, "track_id": "kick"}  # マージ
        )
    ),
    bpm=120.0,
    pattern_length=4.0
)
```

---

## oiduna_auth: 認証・認可

### ディレクトリ構造

```
oiduna_auth/
├── __init__.py
└── dependencies.py       # FastAPI依存性注入
```

### クライアントトークン認証

```python
from fastapi import HTTPException, Header

async def verify_client_token(
    x_client_id: str = Header(...),
    x_client_token: str = Header(...),
    container: SessionContainer = Depends(get_container)
) -> str:
    """クライアントトークン検証"""
    if not container.clients.verify_token(x_client_id, x_client_token):
        raise HTTPException(status_code=403, detail="Invalid token")

    return x_client_id
```

**使用例（API層）**:
```python
@router.post("/tracks/{track_id}")
async def create_track(
    track_id: str,
    data: dict,
    client_id: str = Depends(verify_client_token),
    container: SessionContainer = Depends(get_container)
):
    """トラック作成（認証必須）"""
    track = container.tracks.create(
        track_id=track_id,
        client_id=client_id,  # 認証されたクライアント
        **data
    )
    return {"track": asdict(track)}
```

### Admin認証

```python
import os
from fastapi import HTTPException, Header

async def verify_admin(
    x_admin_password: str = Header(...)
) -> None:
    """Admin認証"""
    expected = os.getenv("OIDUNA_ADMIN_PASSWORD", "admin")

    if x_admin_password != expected:
        raise HTTPException(status_code=403, detail="Forbidden")
```

**使用例**:
```python
@router.delete("/clients/{client_id}")
async def delete_client(
    client_id: str,
    _: None = Depends(verify_admin),  # Admin権限必須
    container: SessionContainer = Depends(get_container)
):
    """クライアント削除（Admin専用）"""
    container.clients.delete(client_id)
    return {"message": "deleted"}
```

---

## Rust移植の考慮事項

### 優先度: 中 🔶

ビジネスロジックはPython実装でも十分だが、将来的な移植候補。

### Rust実装の方針

```rust
use std::collections::HashMap;

pub struct SessionContainer {
    session: Session,
    destinations: DestinationManager,
    clients: ClientManager,
    tracks: TrackManager,
    patterns: PatternManager,
}

impl SessionContainer {
    pub fn new() -> Self {
        let session = Session::new();
        let destinations = DestinationManager::new(&session);
        let clients = ClientManager::new(&session);
        let tracks = TrackManager::new(&session, &destinations);
        let patterns = PatternManager::new(&session);

        Self {
            session,
            destinations,
            clients,
            tracks,
            patterns,
        }
    }

    pub fn get_state(&self) -> HashMap<String, serde_json::Value> {
        // JSONシリアライズで互換性維持
        serde_json::to_value(&self.session).unwrap()
    }
}

pub struct TrackManager<'a> {
    session: &'a mut Session,
    destination_manager: &'a DestinationManager<'a>,
}

impl<'a> TrackManager<'a> {
    pub fn create(
        &mut self,
        track_id: String,
        destination_id: String,
        client_id: String,
    ) -> Result<Track, String> {
        // 存在確認（Silent Failure防止）
        self.destination_manager.get(&destination_id)?;

        let track = Track {
            track_id,
            destination_id,
            client_id,
            ..Default::default()
        };

        self.session.tracks.insert(track.track_id.clone(), track);
        Ok(track)
    }
}
```

---

## テスト例

```python
def test_track_creation_with_nonexistent_destination_raises():
    """存在しないデスティネーションでトラック作成はエラー"""
    container = SessionContainer()

    # デスティネーションなし
    with pytest.raises(ValueError, match="does not exist"):
        container.tracks.create(
            track_id="kick",
            track_name="Kick",
            destination_id="nonexistent",
            client_id="alice"
        )

def test_destination_removal_with_tracks_raises():
    """使用中のデスティネーション削除はエラー"""
    container = SessionContainer()

    # セットアップ
    dest = OscDestinationConfig(id="superdirt", ...)
    container.destinations.add(dest)
    container.clients.create("alice", "Alice", "mars")
    container.tracks.create(
        track_id="kick",
        destination_id="superdirt",
        client_id="alice"
    )

    # 削除試行
    with pytest.raises(ValueError, match="in use by tracks"):
        container.destinations.remove("superdirt")

def test_session_compiler():
    """SessionCompilerのテスト"""
    container = SessionContainer()

    # セットアップ
    dest = OscDestinationConfig(id="superdirt", ...)
    container.destinations.add(dest)
    container.clients.create("alice", "Alice", "mars")
    track = container.tracks.create(
        track_id="kick",
        destination_id="superdirt",
        client_id="alice",
        base_params={"sound": "bd"}
    )
    container.patterns.create("kick", "main", "Main")
    container.patterns.add_event("kick", "main", step=0, cycle=0.0, params={})

    # コンパイル
    batch = SessionCompiler.compile(container.session)

    assert len(batch.messages) == 1
    assert batch.messages[0].destination_id == "superdirt"
    assert batch.messages[0].params["sound"] == "bd"
    assert batch.messages[0].params["track_id"] == "kick"
```

---

## まとめ

### アプリケーション層の重要性

1. **Silent Failure防止**: 作成時にエラー、実行時ではない
2. **Manager分離**: 各Managerが単一の責任を持つ
3. **明確なエラーメッセージ**: 利用可能な選択肢を表示
4. **Facade Pattern**: SessionContainerで統一インターフェース

### 設計判断

- **Pydanticイミュータブル**: 更新時は新オブジェクト作成
- **依存性注入**: ManagerにSessionを渡す
- **使用中チェック**: 削除前に依存関係を確認
- **SessionCompiler**: 階層構造→フラット構造の変換

### 次のステップ

アプリケーション層を理解したら：
1. [Layer 1: API層](./layer-1-api.md)でHTTPエンドポイントを学ぶ
2. [External Interface: クライアント層](./external-interface.md)でクライアントを理解
3. [Layer 3: コア層](./layer-3-core.md)でリアルタイム実行を学ぶ
4. [データフロー例](./data-flow-examples.md)で全体の流れを確認

---

**関連ドキュメント**:
- `packages/oiduna_session/README.md`
- `packages/oiduna_auth/README.md`
- ADR-0010: SessionContainer Pattern
- ADR-0008: Code Quality Refactoring Strategy
