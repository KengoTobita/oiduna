# External Interface: クライアント層 (Clients)

**パッケージ**: `oiduna_cli`, `oiduna_client`

**最終更新**: 2026-03-01

---

## 概要

External Interface層は、Oidunaへのアクセスインターフェースを提供します。HTTP APIクライアントとして機能し、ビジネスロジックや状態管理は一切含みません。これは開発・テスト用のオプションツールであり、MARSなどの外部システムはLayer 1 (API層)に直接接続します。

### 責任

- ✅ HTTP APIクライアント実装
- ✅ コマンドラインインターフェース（CLI）
- ✅ Pythonライブラリインターフェース
- ✅ エラーハンドリング（HTTP例外）
- ❌ ビジネスロジック（すべてサーバー側）
- ❌ 状態管理（サーバー側のみ）

### 依存関係

```
oiduna_cli → HTTP通信のみ（他パッケージに依存しない）
oiduna_client → HTTP通信のみ（他パッケージに依存しない）
```

**設計原則**: External Interface層は完全に独立。他のOidunaパッケージに依存しない。

---

## oiduna_cli: コマンドラインインターフェース

### ディレクトリ構造

```
oiduna_cli/
├── __init__.py
├── main.py               # CLIエントリーポイント
├── commands/
│   ├── __init__.py
│   ├── client.py         # client create/delete
│   ├── track.py          # track create/update/delete
│   ├── pattern.py        # pattern create/event add
│   ├── playback.py       # play/stop/bpm
│   └── status.py         # status/stream
└── config.py             # 設定ファイル管理
```

---

## main.py: CLIエントリーポイント

```python
import click
from oiduna_cli.commands import (
    client,
    track,
    pattern,
    playback,
    status
)

@click.group()
@click.option('--server', default='http://localhost:57122', help='Oiduna server URL')
@click.pass_context
def cli(ctx, server):
    """Oiduna CLI - Real-time live coding sequencer"""
    ctx.ensure_object(dict)
    ctx.obj['SERVER'] = server

# サブコマンド登録
cli.add_command(client.client)
cli.add_command(track.track)
cli.add_command(pattern.pattern)
cli.add_command(playback.playback)
cli.add_command(status.status)

if __name__ == '__main__':
    cli()
```

---

## commands/client.py: クライアント管理

```python
import click
import requests
from typing import Optional

@click.group()
def client():
    """Client management commands"""
    pass

@client.command()
@click.argument('client_id')
@click.option('--name', default=None, help='Client name')
@click.option('--type', 'client_type', default='mars', help='Client type')
@click.pass_context
def create(ctx, client_id: str, name: Optional[str], client_type: str):
    """Create a new client and get token"""
    server = ctx.obj['SERVER']
    client_name = name or client_id

    response = requests.post(
        f"{server}/clients/{client_id}",
        json={
            "client_name": client_name,
            "client_type": client_type
        }
    )

    if response.status_code == 201:
        data = response.json()
        click.echo(f"Client created: {data['client_id']}")
        click.echo(f"Token: {data['token']}")
        click.echo(f"\nSave this token! Set environment variable:")
        click.echo(f"export OIDUNA_CLIENT_ID={client_id}")
        click.echo(f"export OIDUNA_CLIENT_TOKEN={data['token']}")
    else:
        click.echo(f"Error: {response.json()['detail']}", err=True)

@client.command()
@click.argument('client_id')
@click.pass_context
def info(ctx, client_id: str):
    """Get client information"""
    server = ctx.obj['SERVER']

    response = requests.get(f"{server}/clients/{client_id}")

    if response.status_code == 200:
        data = response.json()
        click.echo(f"Client ID: {data['client_id']}")
        click.echo(f"Name: {data['client_name']}")
        click.echo(f"Type: {data['client_type']}")
        click.echo(f"Created: {data['created_at']}")
    else:
        click.echo(f"Error: {response.json()['detail']}", err=True)
```

**使用例**:
```bash
# クライアント作成
oiduna client create alice --name "Alice"
# Output:
# Client created: alice
# Token: 12345678-1234-1234-1234-123456789abc
# Save this token! Set environment variable:
# export OIDUNA_CLIENT_ID=alice
# export OIDUNA_CLIENT_TOKEN=12345678-1234-1234-1234-123456789abc

# クライアント情報取得
oiduna client info alice
# Output:
# Client ID: alice
# Name: Alice
# Type: mars
# Created: 2026-03-01T12:00:00Z
```

---

## commands/track.py: トラック管理

```python
import click
import requests
import os

def get_auth_headers():
    """環境変数から認証ヘッダー取得"""
    client_id = os.getenv('OIDUNA_CLIENT_ID')
    token = os.getenv('OIDUNA_CLIENT_TOKEN')

    if not client_id or not token:
        click.echo("Error: Set OIDUNA_CLIENT_ID and OIDUNA_CLIENT_TOKEN", err=True)
        raise click.Abort()

    return {
        'X-Client-ID': client_id,
        'X-Client-Token': token
    }

@click.group()
def track():
    """Track management commands"""
    pass

@track.command()
@click.argument('track_id')
@click.option('--name', default=None, help='Track name')
@click.option('--destination', default='superdirt', help='Destination ID')
@click.option('--sound', default=None, help='Sound (for SuperDirt)')
@click.option('--gain', default=0.8, help='Gain (0.0-1.0)')
@click.pass_context
def create(ctx, track_id: str, name: Optional[str], destination: str, sound: Optional[str], gain: float):
    """Create a new track"""
    server = ctx.obj['SERVER']
    headers = get_auth_headers()
    track_name = name or track_id

    base_params = {"gain": gain}
    if sound:
        base_params["sound"] = sound

    response = requests.post(
        f"{server}/tracks/{track_id}",
        headers=headers,
        json={
            "track_name": track_name,
            "destination_id": destination,
            "base_params": base_params
        }
    )

    if response.status_code == 201:
        data = response.json()
        click.echo(f"Track created: {data['track_id']}")
        click.echo(f"Destination: {data['destination_id']}")
        click.echo(f"Base params: {data['base_params']}")
    else:
        click.echo(f"Error: {response.json()['detail']}", err=True)

@track.command()
@click.argument('track_id')
@click.pass_context
def info(ctx, track_id: str):
    """Get track information"""
    server = ctx.obj['SERVER']

    response = requests.get(f"{server}/tracks/{track_id}")

    if response.status_code == 200:
        data = response.json()
        click.echo(f"Track ID: {data['track_id']}")
        click.echo(f"Name: {data['track_name']}")
        click.echo(f"Destination: {data['destination_id']}")
        click.echo(f"Base params: {data['base_params']}")
        click.echo(f"Patterns: {len(data['patterns'])}")
    else:
        click.echo(f"Error: {response.json()['detail']}", err=True)

@track.command()
@click.argument('track_id')
@click.pass_context
def delete(ctx, track_id: str):
    """Delete a track"""
    server = ctx.obj['SERVER']
    headers = get_auth_headers()

    response = requests.delete(
        f"{server}/tracks/{track_id}",
        headers=headers
    )

    if response.status_code == 200:
        click.echo(f"Track deleted: {track_id}")
    else:
        click.echo(f"Error: {response.json()['detail']}", err=True)
```

**使用例**:
```bash
# 環境変数設定
export OIDUNA_CLIENT_ID=alice
export OIDUNA_CLIENT_TOKEN=12345678-1234-1234-1234-123456789abc

# トラック作成
oiduna track create kick --name "Kick Drum" --sound bd --gain 0.9
# Output:
# Track created: kick
# Destination: superdirt
# Base params: {'sound': 'bd', 'gain': 0.9}

# トラック情報取得
oiduna track info kick

# トラック削除
oiduna track delete kick
```

---

## commands/pattern.py: パターン管理

```python
import click
import requests

@click.group()
def pattern():
    """Pattern management commands"""
    pass

@pattern.command()
@click.argument('track_id')
@click.argument('pattern_id')
@click.option('--name', default=None, help='Pattern name')
@click.pass_context
def create(ctx, track_id: str, pattern_id: str, name: Optional[str]):
    """Create a new pattern"""
    server = ctx.obj['SERVER']
    headers = get_auth_headers()
    pattern_name = name or pattern_id

    response = requests.post(
        f"{server}/tracks/{track_id}/patterns/{pattern_id}",
        headers=headers,
        json={"pattern_name": pattern_name}
    )

    if response.status_code == 201:
        click.echo(f"Pattern created: {pattern_id} in track {track_id}")
    else:
        click.echo(f"Error: {response.json()['detail']}", err=True)

@pattern.command()
@click.argument('track_id')
@click.argument('pattern_id')
@click.option('--step', required=True, type=int, help='Step (0-255)')
@click.option('--cycle', default=0.0, help='Cycle position')
@click.option('--params', default='{}', help='JSON params')
@click.pass_context
def add_event(ctx, track_id: str, pattern_id: str, step: int, cycle: float, params: str):
    """Add event to pattern"""
    import json

    server = ctx.obj['SERVER']
    headers = get_auth_headers()

    try:
        params_dict = json.loads(params)
    except json.JSONDecodeError:
        click.echo("Error: Invalid JSON in --params", err=True)
        return

    response = requests.post(
        f"{server}/tracks/{track_id}/patterns/{pattern_id}/events",
        headers=headers,
        json={
            "step": step,
            "cycle": cycle,
            "params": params_dict
        }
    )

    if response.status_code == 201:
        click.echo(f"Event added at step {step}")
    else:
        click.echo(f"Error: {response.json()['detail']}", err=True)
```

**使用例**:
```bash
# パターン作成
oiduna pattern create kick main --name "Main Pattern"

# イベント追加
oiduna pattern add-event kick main --step 0 --cycle 0.0
oiduna pattern add-event kick main --step 64 --cycle 1.0 --params '{"gain": 0.7}'
```

---

## commands/playback.py: 再生制御

```python
import click
import requests

@click.group()
def playback():
    """Playback control commands"""
    pass

@playback.command()
@click.pass_context
def start(ctx):
    """Start playback"""
    server = ctx.obj['SERVER']

    response = requests.post(f"{server}/playback/start")

    if response.status_code == 200:
        click.echo("Playback started")
    else:
        click.echo(f"Error: {response.json()['detail']}", err=True)

@playback.command()
@click.pass_context
def stop(ctx):
    """Stop playback"""
    server = ctx.obj['SERVER']

    response = requests.post(f"{server}/playback/stop")

    if response.status_code == 200:
        click.echo("Playback stopped")
    else:
        click.echo(f"Error: {response.json()['detail']}", err=True)

@playback.command()
@click.argument('bpm', type=float)
@click.pass_context
def set_bpm(ctx, bpm: float):
    """Set BPM"""
    server = ctx.obj['SERVER']

    response = requests.post(
        f"{server}/playback/bpm",
        params={"bpm": bpm}
    )

    if response.status_code == 200:
        click.echo(f"BPM set to {bpm}")
    else:
        click.echo(f"Error: {response.json()['detail']}", err=True)
```

**使用例**:
```bash
# 再生開始
oiduna playback start

# BPM変更
oiduna playback set-bpm 140

# 停止
oiduna playback stop
```

---

## commands/status.py: 状態確認

```python
import click
import requests
from sseclient import SSEClient  # pip install sseclient-py

@click.group()
def status():
    """Status commands"""
    pass

@status.command()
@click.pass_context
def session(ctx):
    """Get session status"""
    server = ctx.obj['SERVER']

    response = requests.get(f"{server}/session/")

    if response.status_code == 200:
        data = response.json()
        click.echo(f"Clients: {len(data['clients'])}")
        click.echo(f"Tracks: {len(data['tracks'])}")
        click.echo(f"Destinations: {len(data['destinations'])}")
        click.echo(f"BPM: {data['environment']['bpm']}")
    else:
        click.echo(f"Error: {response.json()['detail']}", err=True)

@status.command()
@click.pass_context
def stream(ctx):
    """Stream real-time status (SSE)"""
    server = ctx.obj['SERVER']

    click.echo("Streaming status... (Ctrl+C to stop)")

    messages = SSEClient(f"{server}/stream")

    for msg in messages:
        import json
        data = json.loads(msg.data)
        click.echo(f"Step: {data['current_step']:3d} | BPM: {data['bpm']:6.2f} | Playing: {data['playing']}")
```

**使用例**:
```bash
# セッション状態取得
oiduna status session
# Output:
# Clients: 2
# Tracks: 3
# Destinations: 1
# BPM: 120.0

# リアルタイムストリーム
oiduna status stream
# Output:
# Streaming status... (Ctrl+C to stop)
# Step:   0 | BPM: 120.00 | Playing: True
# Step:   1 | BPM: 120.00 | Playing: True
# ...
```

---

## oiduna_client: Pythonライブラリ

### ディレクトリ構造

```
oiduna_client/
├── __init__.py
└── client.py             # OidunaClient実装
```

---

## client.py: OidunaClient実装

```python
import requests
from typing import Optional, Dict, Any

class OidunaClient:
    """Oiduna HTTP APIクライアント"""

    def __init__(self, server_url: str = "http://localhost:57122"):
        self.server_url = server_url
        self.client_id: Optional[str] = None
        self.token: Optional[str] = None

    def _headers(self) -> Dict[str, str]:
        """認証ヘッダー"""
        if not self.client_id or not self.token:
            raise ValueError("Not authenticated. Call create_client() first.")

        return {
            "X-Client-ID": self.client_id,
            "X-Client-Token": self.token
        }

    # Client methods
    def create_client(self, client_id: str, client_name: str, client_type: str = "mars") -> Dict:
        """クライアント作成（トークン取得）"""
        response = requests.post(
            f"{self.server_url}/clients/{client_id}",
            json={
                "client_name": client_name,
                "client_type": client_type
            }
        )
        response.raise_for_status()

        data = response.json()
        self.client_id = data["client_id"]
        self.token = data["token"]

        return data

    # Track methods
    def create_track(
        self,
        track_id: str,
        track_name: str,
        destination_id: str,
        base_params: Optional[Dict[str, Any]] = None
    ) -> Dict:
        """トラック作成"""
        response = requests.post(
            f"{self.server_url}/tracks/{track_id}",
            headers=self._headers(),
            json={
                "track_name": track_name,
                "destination_id": destination_id,
                "base_params": base_params or {}
            }
        )
        response.raise_for_status()
        return response.json()

    def get_track(self, track_id: str) -> Dict:
        """トラック取得"""
        response = requests.get(f"{self.server_url}/tracks/{track_id}")
        response.raise_for_status()
        return response.json()

    def delete_track(self, track_id: str) -> Dict:
        """トラック削除"""
        response = requests.delete(
            f"{self.server_url}/tracks/{track_id}",
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()

    # Pattern methods
    def create_pattern(
        self,
        track_id: str,
        pattern_id: str,
        pattern_name: str
    ) -> Dict:
        """パターン作成"""
        response = requests.post(
            f"{self.server_url}/tracks/{track_id}/patterns/{pattern_id}",
            headers=self._headers(),
            json={"pattern_name": pattern_name}
        )
        response.raise_for_status()
        return response.json()

    def add_event(
        self,
        track_id: str,
        pattern_id: str,
        step: int,
        cycle: float,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict:
        """イベント追加"""
        response = requests.post(
            f"{self.server_url}/tracks/{track_id}/patterns/{pattern_id}/events",
            headers=self._headers(),
            json={
                "step": step,
                "cycle": cycle,
                "params": params or {}
            }
        )
        response.raise_for_status()
        return response.json()

    # Playback methods
    def start(self) -> Dict:
        """再生開始"""
        response = requests.post(f"{self.server_url}/playback/start")
        response.raise_for_status()
        return response.json()

    def stop(self) -> Dict:
        """再生停止"""
        response = requests.post(f"{self.server_url}/playback/stop")
        response.raise_for_status()
        return response.json()

    def set_bpm(self, bpm: float) -> Dict:
        """BPM設定"""
        response = requests.post(
            f"{self.server_url}/playback/bpm",
            params={"bpm": bpm}
        )
        response.raise_for_status()
        return response.json()

    # Session methods
    def get_session(self) -> Dict:
        """セッション状態取得"""
        response = requests.get(f"{self.server_url}/session/")
        response.raise_for_status()
        return response.json()
```

**使用例**:
```python
from oiduna_client import OidunaClient

# クライアント作成
client = OidunaClient("http://localhost:57122")

# 認証
client.create_client("alice", "Alice")

# トラック作成
client.create_track(
    "kick",
    "Kick Drum",
    "superdirt",
    {"sound": "bd", "gain": 0.8}
)

# パターン作成
client.create_pattern("kick", "main", "Main Pattern")

# イベント追加
client.add_event("kick", "main", step=0, cycle=0.0)
client.add_event("kick", "main", step=64, cycle=1.0, params={"gain": 0.9})

# 再生開始
client.start()

# BPM変更
client.set_bpm(140)

# 停止
client.stop()
```

---

## Rust移植の考慮事項

### 優先度: 中 🔶

CLIツールはRust移植で配布が容易になる。

### Rust実装の方針

```rust
use clap::{Parser, Subcommand};
use reqwest::blocking::Client;
use serde::{Deserialize, Serialize};

#[derive(Parser)]
#[command(name = "oiduna")]
#[command(about = "Oiduna CLI - Real-time live coding sequencer")]
struct Cli {
    #[arg(long, default_value = "http://localhost:57122")]
    server: String,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    Client {
        #[command(subcommand)]
        action: ClientAction,
    },
    Track {
        #[command(subcommand)]
        action: TrackAction,
    },
}

#[derive(Subcommand)]
enum ClientAction {
    Create {
        client_id: String,
        #[arg(long)]
        name: Option<String>,
    },
}

fn main() {
    let cli = Cli::parse();
    let client = Client::new();

    match cli.command {
        Commands::Client { action } => match action {
            ClientAction::Create { client_id, name } => {
                let response = client
                    .post(format!("{}/clients/{}", cli.server, client_id))
                    .json(&serde_json::json!({
                        "client_name": name.unwrap_or(client_id.clone())
                    }))
                    .send()
                    .unwrap();

                println!("Client created: {:?}", response.json::<serde_json::Value>());
            }
        },
        _ => {}
    }
}
```

**Rust版のメリット**:
- シングルバイナリ配布（Python不要）
- 高速起動
- クロスプラットフォームビルド

---

## テスト例

```python
def test_oiduna_client():
    """OidunaClientのテスト"""
    client = OidunaClient("http://localhost:57122")

    # クライアント作成
    response = client.create_client("test_client", "Test Client")
    assert response["client_id"] == "test_client"
    assert "token" in response

    # トラック作成
    track = client.create_track(
        "test_track",
        "Test Track",
        "superdirt",
        {"sound": "bd"}
    )
    assert track["track_id"] == "test_track"

    # トラック削除
    response = client.delete_track("test_track")
    assert "message" in response
```

---

## まとめ

### External Interface層の重要性

1. **完全な独立性**: 他のOidunaパッケージに依存しない
2. **HTTP APIクライアント**: サーバー側にビジネスロジック集約
3. **CLI/ライブラリ**: 用途に応じたインターフェース
4. **Rust移植**: CLIはRustで配布が容易
5. **オプション性**: MARS等の外部システムは直接Layer 1 (API層)へ接続

### 設計判断

- **HTTP通信のみ**: 状態管理はサーバー側
- **環境変数認証**: OIDUNA_CLIENT_ID, OIDUNA_CLIENT_TOKEN
- **エラーハンドリング**: HTTPステータスコード
- **SSE対応**: リアルタイムストリーム

### 次のステップ

External Interface層を理解したら：
1. [Layer 1: API層](./layer-1-api.md)でメインの入口を理解
2. [README](./README.md)で全体像を再確認
3. [QUICK_REFERENCE](./QUICK_REFERENCE.md)で要点をおさらい
4. 実際にCLIやライブラリを使ってみる

---

**関連ドキュメント**:
- `packages/oiduna_cli/README.md`
- `packages/oiduna_client/README.md`
- Click公式: https://click.palletsprojects.com/
- Requests公式: https://requests.readthedocs.io/
