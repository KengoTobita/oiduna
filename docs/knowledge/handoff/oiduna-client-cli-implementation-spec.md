# Oiduna Client + CLI Implementation Specification

**作成日:** 2026-02-22
**対象:** 別エージェントによる実装
**Phase:** 2.1 (Development Tools)

---

## 1. プロジェクト概要

### 1.1 目的

**問題:**
- MARS DSL の開発進捗が Oiduna のテスト・検証のボトルネックになる可能性
- Oiduna の各機能を手軽に検証する方法が必要
- 人間（開発者）が直接 Oiduna を操作するツールがない

**解決策:**
Oiduna HTTP API をラップする軽量な Python クライアントライブラリ + CLI ツールを提供

### 1.2 スコープ

**実装対象:**
1. `oiduna_client` - Python ライブラリ（HTTP API ラッパー）
2. `oiduna_cli` - CLI ツール（コマンドモード + インタラクティブ REPL）
3. サンプル IR ファイル（即座にテスト可能）
4. サンプル SynthDef ファイル（基本的な音色定義）

**非スコープ:**
- MARS DSL コンパイラ（別プロジェクト）
- Web UI（Phase 3 以降）
- パターン生成・変換ロジック（ディストリビューション側の責務）

### 1.3 重要な制約

**Claude Code からの使用を念頭に置く:**
- CLI は人間だけでなく、Claude Code（自動化エージェント）からも呼び出される
- 出力フォーマットは機械可読である必要がある（JSON 出力オプション）
- エラーハンドリングは明確な終了コードとメッセージを提供
- ドライラン・検証モードをサポート

---

## 2. アーキテクチャ概要

```
┌─────────────────────────────────────────────────┐
│  User / Claude Code                              │
└────────────┬────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────┐
│  oiduna_cli (CLI Tool)                          │
│  - Command Mode: oiduna play pattern.json       │
│  - Interactive REPL: oiduna repl                │
└────────────┬────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────┐
│  oiduna_client (Python Library)                 │
│  - PatternClient                                │
│  - SynthDefClient                               │
│  - SampleClient                                 │
│  - HealthClient                                 │
│  - OidunaClient (統合クライアント)              │
└────────────┬────────────────────────────────────┘
             │
             ▼ HTTP (localhost:8000)
┌─────────────────────────────────────────────────┐
│  Oiduna API (FastAPI)                           │
│  - /patterns/*                                  │
│  - /superdirt/*                                 │
│  - /health                                      │
└─────────────────────────────────────────────────┘
```

---

## 3. oiduna_client ライブラリ仕様

### 3.1 ファイル構造

```
packages/oiduna_client/
├── __init__.py
├── client.py          # OidunaClient（統合クライアント）
├── patterns.py        # PatternClient
├── synthdef.py        # SynthDefClient
├── samples.py         # SampleClient
├── health.py          # HealthClient
├── models.py          # Pydantic モデル（リクエスト・レスポンス）
├── exceptions.py      # カスタム例外
└── config.py          # 設定（ベースURL等）
```

### 3.2 依存関係

```toml
[project]
name = "oiduna_client"
version = "0.1.0"
dependencies = [
    "httpx>=0.27.0",      # 非同期HTTPクライアント
    "pydantic>=2.0.0",    # データ検証
    "rich>=13.0.0",       # CLI表示（Optional）
]
```

### 3.3 OidunaClient（統合クライアント）

**ファイル:** `client.py`

```python
from typing import Optional
import httpx
from .patterns import PatternClient
from .synthdef import SynthDefClient
from .samples import SampleClient
from .health import HealthClient


class OidunaClient:
    """Oiduna API 統合クライアント

    Example:
        >>> client = OidunaClient(base_url="http://localhost:8000")
        >>> await client.patterns.submit(pattern_data)
        >>> await client.health.check()
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float = 30.0,
        http_client: Optional[httpx.AsyncClient] = None
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

        # 共有HTTPクライアント
        self._http_client = http_client or httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout
        )

        # サブクライアント
        self.patterns = PatternClient(self._http_client)
        self.synthdef = SynthDefClient(self._http_client)
        self.samples = SampleClient(self._http_client)
        self.health = HealthClient(self._http_client)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        """HTTPクライアントをクローズ"""
        await self._http_client.aclose()
```

### 3.4 PatternClient

**ファイル:** `patterns.py`

**対応エンドポイント:**
- `POST /patterns/submit` - パターン送信・実行
- `POST /patterns/validate` - パターン検証のみ
- `GET /patterns/active` - アクティブパターン取得
- `POST /patterns/stop` - パターン停止

```python
from typing import Any, Dict, Optional
import httpx
from .models import PatternSubmitRequest, PatternSubmitResponse, PatternValidateResponse
from .exceptions import OidunaAPIError, ValidationError, TimeoutError


class PatternClient:
    """パターン操作クライアント"""

    def __init__(self, http_client: httpx.AsyncClient):
        self._http = http_client

    async def submit(
        self,
        pattern: Dict[str, Any],
        validate_only: bool = False
    ) -> PatternSubmitResponse:
        """パターンを送信・実行

        Args:
            pattern: Oiduna IR形式のパターンデータ
            validate_only: Trueの場合は検証のみ（実行しない）

        Returns:
            PatternSubmitResponse: 実行結果

        Raises:
            ValidationError: パターンが無効
            TimeoutError: タイムアウト
            OidunaAPIError: その他のAPIエラー
        """
        try:
            response = await self._http.post(
                "/patterns/submit",
                json={"pattern": pattern, "validate_only": validate_only}
            )
            response.raise_for_status()
            return PatternSubmitResponse(**response.json())
        except httpx.TimeoutException as e:
            raise TimeoutError(f"Request timed out: {e}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                raise ValidationError(e.response.json().get("detail", str(e)))
            raise OidunaAPIError(f"API error: {e}")

    async def validate(self, pattern: Dict[str, Any]) -> PatternValidateResponse:
        """パターンを検証（実行せず）

        Args:
            pattern: Oiduna IR形式のパターンデータ

        Returns:
            PatternValidateResponse: 検証結果
        """
        response = await self._http.post(
            "/patterns/validate",
            json={"pattern": pattern}
        )
        response.raise_for_status()
        return PatternValidateResponse(**response.json())

    async def get_active(self) -> Dict[str, Any]:
        """アクティブなパターンを取得

        Returns:
            Dict: アクティブパターンのリスト
        """
        response = await self._http.get("/patterns/active")
        response.raise_for_status()
        return response.json()

    async def stop(self, track_id: Optional[str] = None) -> Dict[str, Any]:
        """パターンを停止

        Args:
            track_id: 停止するトラックID（Noneの場合は全停止）

        Returns:
            Dict: 停止結果
        """
        payload = {"track_id": track_id} if track_id else {}
        response = await self._http.post("/patterns/stop", json=payload)
        response.raise_for_status()
        return response.json()
```

### 3.5 SynthDefClient

**ファイル:** `synthdef.py`

**対応エンドポイント:**
- `POST /superdirt/synthdef` - SynthDef ロード

```python
from typing import Optional
import httpx
from .models import SynthDefLoadRequest, SynthDefLoadResponse
from .exceptions import OidunaAPIError, TimeoutError


class SynthDefClient:
    """SynthDef操作クライアント"""

    def __init__(self, http_client: httpx.AsyncClient):
        self._http = http_client

    async def load(
        self,
        name: str,
        code: str,
        timeout: Optional[float] = None
    ) -> SynthDefLoadResponse:
        """SynthDefをロード

        Args:
            name: SynthDef名（SuperCollider識別子形式）
            code: SuperCollider コード
            timeout: タイムアウト（秒）

        Returns:
            SynthDefLoadResponse: ロード結果

        Raises:
            TimeoutError: SuperColliderからの確認がタイムアウト
            OidunaAPIError: その他のAPIエラー
        """
        request = SynthDefLoadRequest(name=name, code=code)

        try:
            response = await self._http.post(
                "/superdirt/synthdef",
                json=request.model_dump(),
                timeout=timeout
            )
            response.raise_for_status()
            return SynthDefLoadResponse(**response.json())
        except httpx.TimeoutException as e:
            raise TimeoutError(f"Request timed out: {e}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 504:
                raise TimeoutError("SuperCollider confirmation timeout")
            raise OidunaAPIError(f"API error: {e}")

    async def load_from_file(
        self,
        filepath: str,
        timeout: Optional[float] = None
    ) -> SynthDefLoadResponse:
        """ファイルからSynthDefをロード

        Args:
            filepath: .scd ファイルパス
            timeout: タイムアウト（秒）

        Returns:
            SynthDefLoadResponse: ロード結果
        """
        with open(filepath, 'r') as f:
            code = f.read()

        # ファイル名からSynthDef名を推測（例: acid.scd -> acid）
        import os
        name = os.path.splitext(os.path.basename(filepath))[0]

        return await self.load(name=name, code=code, timeout=timeout)
```

### 3.6 SampleClient

**ファイル:** `samples.py`

**対応エンドポイント:**
- `POST /superdirt/sample/load` - サンプルロード
- `GET /superdirt/buffers` - バッファリスト取得

```python
from typing import List, Optional
import httpx
from .models import SampleLoadRequest, SampleLoadResponse, BufferListResponse
from .exceptions import OidunaAPIError, TimeoutError


class SampleClient:
    """サンプル操作クライアント"""

    def __init__(self, http_client: httpx.AsyncClient):
        self._http = http_client

    async def load(
        self,
        category: str,
        path: str,
        timeout: Optional[float] = None
    ) -> SampleLoadResponse:
        """サンプルディレクトリをロード

        Args:
            category: サンプルカテゴリ名（例: "custom", "kicks"）
            path: サンプルディレクトリの絶対パス
            timeout: タイムアウト（秒）

        Returns:
            SampleLoadResponse: ロード結果
        """
        request = SampleLoadRequest(category=category, path=path)

        try:
            response = await self._http.post(
                "/superdirt/sample/load",
                json=request.model_dump(),
                timeout=timeout
            )
            response.raise_for_status()
            return SampleLoadResponse(**response.json())
        except httpx.TimeoutException as e:
            raise TimeoutError(f"Request timed out: {e}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 504:
                raise TimeoutError("SuperCollider confirmation timeout")
            raise OidunaAPIError(f"API error: {e}")

    async def list_buffers(self) -> BufferListResponse:
        """ロード済みバッファ一覧を取得

        Returns:
            BufferListResponse: バッファリスト
        """
        response = await self._http.get("/superdirt/buffers")
        response.raise_for_status()
        return BufferListResponse(**response.json())
```

### 3.7 HealthClient

**ファイル:** `health.py`

**対応エンドポイント:**
- `GET /health` - ヘルスチェック

```python
import httpx
from .models import HealthResponse
from .exceptions import OidunaAPIError


class HealthClient:
    """ヘルスチェッククライアント"""

    def __init__(self, http_client: httpx.AsyncClient):
        self._http = http_client

    async def check(self) -> HealthResponse:
        """Oidunaのヘルスチェック

        Returns:
            HealthResponse: ヘルス状態
        """
        response = await self._http.get("/health")
        response.raise_for_status()
        return HealthResponse(**response.json())

    async def wait_ready(
        self,
        timeout: float = 30.0,
        interval: float = 1.0
    ) -> bool:
        """Oidunaが準備完了するまで待機

        Args:
            timeout: 最大待機時間（秒）
            interval: チェック間隔（秒）

        Returns:
            bool: 準備完了したらTrue

        Raises:
            TimeoutError: タイムアウト
        """
        import asyncio
        from time import time

        start = time()
        while time() - start < timeout:
            try:
                health = await self.check()
                if health.status == "healthy":
                    return True
            except Exception:
                pass
            await asyncio.sleep(interval)

        raise TimeoutError(f"Oiduna not ready after {timeout}s")
```

### 3.8 models.py（Pydantic モデル）

```python
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# リクエストモデル
class PatternSubmitRequest(BaseModel):
    pattern: Dict[str, Any]
    validate_only: bool = False


class SynthDefLoadRequest(BaseModel):
    name: str = Field(..., pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    code: str


class SampleLoadRequest(BaseModel):
    category: str
    path: str


# レスポンスモデル
class PatternSubmitResponse(BaseModel):
    status: str
    track_id: Optional[str] = None
    message: Optional[str] = None


class PatternValidateResponse(BaseModel):
    valid: bool
    errors: Optional[List[str]] = None


class SynthDefLoadResponse(BaseModel):
    request_id: str  # Phase 2で追加予定
    status: str
    name: str
    loaded: bool
    message: Optional[str] = None


class SampleLoadResponse(BaseModel):
    request_id: str  # Phase 2で追加予定
    status: str
    category: str
    loaded: bool
    sample_count: Optional[int] = None
    message: Optional[str] = None


class BufferListResponse(BaseModel):
    status: str
    buffers: List[str]
    count: int


class HealthResponse(BaseModel):
    status: str  # "healthy" | "degraded" | "unhealthy"
    components: Dict[str, str]  # {"superdirt": "connected", ...}
    version: str
```

### 3.9 exceptions.py（カスタム例外）

```python
class OidunaClientError(Exception):
    """Oiduna クライアント基底例外"""
    pass


class OidunaAPIError(OidunaClientError):
    """API エラー"""
    pass


class ValidationError(OidunaClientError):
    """バリデーションエラー"""
    pass


class TimeoutError(OidunaClientError):
    """タイムアウトエラー"""
    pass


class ConnectionError(OidunaClientError):
    """接続エラー"""
    pass
```

---

## 4. oiduna_cli 仕様

### 4.1 ファイル構造

```
packages/oiduna_cli/
├── __init__.py
├── main.py            # CLIエントリポイント
├── commands/
│   ├── __init__.py
│   ├── play.py        # play コマンド
│   ├── synthdef.py    # synthdef コマンド
│   ├── sample.py      # sample コマンド
│   ├── status.py      # status コマンド
│   └── repl.py        # REPL コマンド
├── repl/
│   ├── __init__.py
│   ├── shell.py       # インタラクティブシェル
│   └── completer.py   # 補完機能
└── utils/
    ├── __init__.py
    ├── output.py      # 出力フォーマット（JSON/human-readable）
    └── config.py      # CLI設定
```

### 4.2 依存関係

```toml
[project]
name = "oiduna_cli"
version = "0.1.0"
dependencies = [
    "oiduna_client>=0.1.0",
    "click>=8.0.0",        # CLI フレームワーク
    "rich>=13.0.0",        # リッチな出力
    "prompt-toolkit>=3.0.0",  # REPL機能
]
```

### 4.3 CLI 全体構成

```bash
# コマンドモード
oiduna play <pattern-file>               # パターン実行
oiduna validate <pattern-file>           # パターン検証
oiduna synthdef load <synthdef-file>     # SynthDefロード
oiduna sample load <category> <path>     # サンプルロード
oiduna sample list                       # バッファリスト
oiduna status                            # ステータス確認
oiduna stop [track-id]                   # 停止

# インタラクティブREPL
oiduna repl                              # REPLモード起動

# グローバルオプション
--url TEXT          # Oiduna API URL（デフォルト: http://localhost:8000）
--timeout FLOAT     # タイムアウト（秒）
--json              # JSON出力モード（Claude Code用）
--verbose           # 詳細ログ
```

### 4.4 main.py（エントリポイント）

```python
import click
import asyncio
from typing import Optional
from rich.console import Console
from oiduna_client import OidunaClient
from .commands import play, synthdef, sample, status, repl
from .utils.output import OutputFormatter


console = Console()


@click.group()
@click.option('--url', default='http://localhost:8000', help='Oiduna API URL')
@click.option('--timeout', default=30.0, help='Request timeout (seconds)')
@click.option('--json', is_flag=True, help='Output as JSON (for automation)')
@click.option('--verbose', is_flag=True, help='Verbose output')
@click.pass_context
def cli(ctx, url: str, timeout: float, json: bool, verbose: bool):
    """Oiduna CLI - SuperDirt + supernova ライブコーディング環境"""
    ctx.ensure_object(dict)
    ctx.obj['url'] = url
    ctx.obj['timeout'] = timeout
    ctx.obj['formatter'] = OutputFormatter(json_mode=json, verbose=verbose)
    ctx.obj['console'] = console


cli.add_command(play.play)
cli.add_command(play.validate)
cli.add_command(play.stop)
cli.add_command(synthdef.synthdef)
cli.add_command(sample.sample)
cli.add_command(status.status)
cli.add_command(repl.repl)


def main():
    """メインエントリポイント"""
    cli(obj={})


if __name__ == '__main__':
    main()
```

### 4.5 play コマンド

**ファイル:** `commands/play.py`

```python
import click
import asyncio
import json
from pathlib import Path
from oiduna_client import OidunaClient


@click.command()
@click.argument('pattern_file', type=click.Path(exists=True))
@click.pass_context
def play(ctx, pattern_file: str):
    """パターンファイルを実行

    Example:
        oiduna play pattern.json
        oiduna --json play pattern.json  # JSON出力（Claude Code用）
    """
    formatter = ctx.obj['formatter']

    try:
        # ファイル読み込み
        with open(pattern_file, 'r') as f:
            pattern_data = json.load(f)

        # API呼び出し
        result = asyncio.run(_play_async(
            ctx.obj['url'],
            ctx.obj['timeout'],
            pattern_data
        ))

        # 出力
        formatter.success("Pattern submitted", result)

    except Exception as e:
        formatter.error("Failed to play pattern", str(e))
        raise click.Abort()


async def _play_async(url: str, timeout: float, pattern_data: dict):
    """非同期パターン実行"""
    async with OidunaClient(base_url=url, timeout=timeout) as client:
        return await client.patterns.submit(pattern_data)


@click.command()
@click.argument('pattern_file', type=click.Path(exists=True))
@click.pass_context
def validate(ctx, pattern_file: str):
    """パターンファイルを検証（実行しない）

    Example:
        oiduna validate pattern.json
    """
    formatter = ctx.obj['formatter']

    try:
        with open(pattern_file, 'r') as f:
            pattern_data = json.load(f)

        result = asyncio.run(_validate_async(
            ctx.obj['url'],
            ctx.obj['timeout'],
            pattern_data
        ))

        if result.valid:
            formatter.success("Pattern is valid", result)
        else:
            formatter.error("Pattern validation failed", result.errors)
            raise click.Abort()

    except Exception as e:
        formatter.error("Validation error", str(e))
        raise click.Abort()


async def _validate_async(url: str, timeout: float, pattern_data: dict):
    """非同期パターン検証"""
    async with OidunaClient(base_url=url, timeout=timeout) as client:
        return await client.patterns.validate(pattern_data)


@click.command()
@click.argument('track_id', required=False)
@click.pass_context
def stop(ctx, track_id: str = None):
    """パターンを停止

    Example:
        oiduna stop           # 全トラック停止
        oiduna stop track-1   # 特定トラック停止
    """
    formatter = ctx.obj['formatter']

    try:
        result = asyncio.run(_stop_async(
            ctx.obj['url'],
            ctx.obj['timeout'],
            track_id
        ))

        formatter.success("Pattern stopped", result)

    except Exception as e:
        formatter.error("Failed to stop pattern", str(e))
        raise click.Abort()


async def _stop_async(url: str, timeout: float, track_id: str = None):
    """非同期パターン停止"""
    async with OidunaClient(base_url=url, timeout=timeout) as client:
        return await client.patterns.stop(track_id)
```

### 4.6 synthdef コマンド

**ファイル:** `commands/synthdef.py`

```python
import click
import asyncio
from pathlib import Path
from oiduna_client import OidunaClient


@click.group()
def synthdef():
    """SynthDef管理コマンド"""
    pass


@synthdef.command()
@click.argument('synthdef_file', type=click.Path(exists=True))
@click.option('--name', help='SynthDef name (default: from filename)')
@click.pass_context
def load(ctx, synthdef_file: str, name: str = None):
    """SynthDefファイルをロード

    Example:
        oiduna synthdef load acid.scd
        oiduna synthdef load custom.scd --name mysynth
    """
    formatter = ctx.obj['formatter']

    try:
        # ファイル読み込み
        with open(synthdef_file, 'r') as f:
            code = f.read()

        # 名前が指定されていない場合、ファイル名から推測
        if not name:
            name = Path(synthdef_file).stem

        # API呼び出し
        result = asyncio.run(_load_synthdef_async(
            ctx.obj['url'],
            ctx.obj['timeout'],
            name,
            code
        ))

        formatter.success(f"SynthDef '{name}' loaded", result)

    except Exception as e:
        formatter.error("Failed to load SynthDef", str(e))
        raise click.Abort()


async def _load_synthdef_async(url: str, timeout: float, name: str, code: str):
    """非同期SynthDefロード"""
    async with OidunaClient(base_url=url, timeout=timeout) as client:
        return await client.synthdef.load(name=name, code=code)
```

### 4.7 sample コマンド

**ファイル:** `commands/sample.py`

```python
import click
import asyncio
from oiduna_client import OidunaClient


@click.group()
def sample():
    """サンプル管理コマンド"""
    pass


@sample.command()
@click.argument('category')
@click.argument('path', type=click.Path(exists=True))
@click.pass_context
def load(ctx, category: str, path: str):
    """サンプルディレクトリをロード

    Example:
        oiduna sample load custom /path/to/samples/custom
    """
    formatter = ctx.obj['formatter']

    try:
        result = asyncio.run(_load_sample_async(
            ctx.obj['url'],
            ctx.obj['timeout'],
            category,
            path
        ))

        formatter.success(f"Samples '{category}' loaded", result)

    except Exception as e:
        formatter.error("Failed to load samples", str(e))
        raise click.Abort()


async def _load_sample_async(url: str, timeout: float, category: str, path: str):
    """非同期サンプルロード"""
    async with OidunaClient(base_url=url, timeout=timeout) as client:
        return await client.samples.load(category=category, path=path)


@sample.command('list')
@click.pass_context
def list_buffers(ctx):
    """ロード済みバッファ一覧を表示

    Example:
        oiduna sample list
        oiduna --json sample list  # JSON出力
    """
    formatter = ctx.obj['formatter']

    try:
        result = asyncio.run(_list_buffers_async(
            ctx.obj['url'],
            ctx.obj['timeout']
        ))

        formatter.success("Loaded buffers", {
            "count": result.count,
            "buffers": result.buffers
        })

    except Exception as e:
        formatter.error("Failed to list buffers", str(e))
        raise click.Abort()


async def _list_buffers_async(url: str, timeout: float):
    """非同期バッファリスト取得"""
    async with OidunaClient(base_url=url, timeout=timeout) as client:
        return await client.samples.list_buffers()
```

### 4.8 status コマンド

**ファイル:** `commands/status.py`

```python
import click
import asyncio
from oiduna_client import OidunaClient


@click.command()
@click.pass_context
def status(ctx):
    """Oidunaのステータスを確認

    Example:
        oiduna status
        oiduna --json status  # JSON出力
    """
    formatter = ctx.obj['formatter']

    try:
        result = asyncio.run(_status_async(
            ctx.obj['url'],
            ctx.obj['timeout']
        ))

        formatter.success("Oiduna status", {
            "status": result.status,
            "components": result.components,
            "version": result.version
        })

    except Exception as e:
        formatter.error("Failed to get status", str(e))
        raise click.Abort()


async def _status_async(url: str, timeout: float):
    """非同期ステータス取得"""
    async with OidunaClient(base_url=url, timeout=timeout) as client:
        return await client.health.check()
```

### 4.9 REPL（インタラクティブモード）

**ファイル:** `commands/repl.py`

```python
import click
from ..repl.shell import OidunaREPL


@click.command()
@click.pass_context
def repl(ctx):
    """インタラクティブREPLモードを起動

    Example:
        oiduna repl

    REPLコマンド:
        > play pattern.json
        > synthdef load acid.scd
        > sample load custom /path/to/samples
        > status
        > stop
        > exit
    """
    console = ctx.obj['console']

    console.print("[bold cyan]Oiduna REPL[/bold cyan]")
    console.print(f"Connected to: {ctx.obj['url']}")
    console.print("Type 'help' for commands, 'exit' to quit\n")

    # REPLセッション開始
    repl_session = OidunaREPL(
        url=ctx.obj['url'],
        timeout=ctx.obj['timeout'],
        console=console
    )

    repl_session.run()
```

**ファイル:** `repl/shell.py`

```python
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from rich.console import Console
import asyncio
from pathlib import Path
from oiduna_client import OidunaClient


class OidunaREPL:
    """Oiduna インタラクティブREPL"""

    def __init__(self, url: str, timeout: float, console: Console):
        self.url = url
        self.timeout = timeout
        self.console = console

        # プロンプトセッション
        history_file = Path.home() / '.oiduna_history'
        self.session = PromptSession(
            history=FileHistory(str(history_file)),
            auto_suggest=AutoSuggestFromHistory()
        )

    def run(self):
        """REPLメインループ"""
        while True:
            try:
                # 入力受付
                text = self.session.prompt('oiduna> ')

                if not text.strip():
                    continue

                # コマンド解析・実行
                if text.strip() in ('exit', 'quit'):
                    self.console.print("[yellow]Goodbye![/yellow]")
                    break
                elif text.strip() == 'help':
                    self._show_help()
                else:
                    asyncio.run(self._execute_command(text))

            except KeyboardInterrupt:
                continue
            except EOFError:
                break

    async def _execute_command(self, command: str):
        """コマンドを実行"""
        parts = command.split()

        try:
            async with OidunaClient(base_url=self.url, timeout=self.timeout) as client:
                if parts[0] == 'play':
                    await self._cmd_play(client, parts[1:])
                elif parts[0] == 'synthdef' and parts[1] == 'load':
                    await self._cmd_synthdef_load(client, parts[2:])
                elif parts[0] == 'sample' and parts[1] == 'load':
                    await self._cmd_sample_load(client, parts[2:])
                elif parts[0] == 'sample' and parts[1] == 'list':
                    await self._cmd_sample_list(client)
                elif parts[0] == 'status':
                    await self._cmd_status(client)
                elif parts[0] == 'stop':
                    await self._cmd_stop(client, parts[1:])
                else:
                    self.console.print(f"[red]Unknown command: {parts[0]}[/red]")
                    self.console.print("Type 'help' for available commands")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")

    async def _cmd_play(self, client: OidunaClient, args: list):
        """playコマンド実行"""
        import json
        with open(args[0], 'r') as f:
            pattern = json.load(f)
        result = await client.patterns.submit(pattern)
        self.console.print(f"[green]✓ Pattern submitted: {result.track_id}[/green]")

    async def _cmd_synthdef_load(self, client: OidunaClient, args: list):
        """synthdef loadコマンド実行"""
        result = await client.synthdef.load_from_file(args[0])
        self.console.print(f"[green]✓ SynthDef '{result.name}' loaded[/green]")

    async def _cmd_sample_load(self, client: OidunaClient, args: list):
        """sample loadコマンド実行"""
        category, path = args[0], args[1]
        result = await client.samples.load(category, path)
        self.console.print(f"[green]✓ Samples '{category}' loaded ({result.sample_count} files)[/green]")

    async def _cmd_sample_list(self, client: OidunaClient):
        """sample listコマンド実行"""
        result = await client.samples.list_buffers()
        self.console.print(f"[cyan]Loaded buffers ({result.count}):[/cyan]")
        for buf in result.buffers:
            self.console.print(f"  - {buf}")

    async def _cmd_status(self, client: OidunaClient):
        """statusコマンド実行"""
        result = await client.health.check()
        self.console.print(f"[cyan]Status: {result.status}[/cyan]")
        for component, status in result.components.items():
            self.console.print(f"  {component}: {status}")

    async def _cmd_stop(self, client: OidunaClient, args: list):
        """stopコマンド実行"""
        track_id = args[0] if args else None
        await client.patterns.stop(track_id)
        self.console.print("[green]✓ Pattern stopped[/green]")

    def _show_help(self):
        """ヘルプ表示"""
        self.console.print("""
[bold cyan]Available Commands:[/bold cyan]

  play <pattern-file>           - Execute pattern
  synthdef load <file>          - Load SynthDef
  sample load <cat> <path>      - Load samples
  sample list                   - List loaded buffers
  status                        - Check Oiduna status
  stop [track-id]               - Stop pattern(s)
  help                          - Show this help
  exit / quit                   - Exit REPL
        """)
```

### 4.10 utils/output.py（出力フォーマット）

```python
import json
from typing import Any, Dict
from rich.console import Console


class OutputFormatter:
    """出力フォーマッター（JSON / human-readable）"""

    def __init__(self, json_mode: bool = False, verbose: bool = False):
        self.json_mode = json_mode
        self.verbose = verbose
        self.console = Console()

    def success(self, message: str, data: Any = None):
        """成功メッセージを出力"""
        if self.json_mode:
            output = {"status": "success", "message": message}
            if data:
                output["data"] = self._serialize(data)
            print(json.dumps(output, indent=2))
        else:
            self.console.print(f"[green]✓ {message}[/green]")
            if data and self.verbose:
                self.console.print_json(data=self._serialize(data))

    def error(self, message: str, details: Any = None):
        """エラーメッセージを出力"""
        if self.json_mode:
            output = {"status": "error", "message": message}
            if details:
                output["details"] = details
            print(json.dumps(output, indent=2))
        else:
            self.console.print(f"[red]✗ {message}[/red]")
            if details:
                self.console.print(f"  Details: {details}")

    def _serialize(self, obj: Any) -> Dict:
        """Pydanticモデルをdict化"""
        if hasattr(obj, 'model_dump'):
            return obj.model_dump()
        return obj
```

---

## 5. サンプルファイル仕様

### 5.1 サンプルIRパターンファイル

**ファイル構造:**

```
samples/
├── patterns/
│   ├── basic_kick.json           # 基本的なキック
│   ├── basic_hihat.json          # 基本的なハイハット
│   ├── simple_beat.json          # シンプルなビート
│   └── complex_pattern.json      # 複雑なパターン
└── synthdefs/
    ├── acid.scd                  # 303風シンセ
    ├── pad.scd                   # パッドシンセ
    └── kick.scd                  # キックドラム
```

**basic_kick.json:**

```json
{
  "version": "1.0",
  "type": "pattern",
  "metadata": {
    "name": "Basic Kick",
    "description": "Simple 4-on-the-floor kick pattern",
    "author": "Oiduna",
    "bpm": 120
  },
  "tracks": [
    {
      "track_id": "kick",
      "instrument": "superkick",
      "pattern": {
        "type": "euclidean",
        "steps": 16,
        "hits": 4,
        "rotation": 0
      },
      "params": {
        "gain": 0.8,
        "freq": 60
      }
    }
  ],
  "global": {
    "cps": 2.0
  }
}
```

**simple_beat.json:**

```json
{
  "version": "1.0",
  "type": "pattern",
  "metadata": {
    "name": "Simple Beat",
    "description": "Kick + snare + hihat pattern",
    "bpm": 120
  },
  "tracks": [
    {
      "track_id": "kick",
      "instrument": "superkick",
      "pattern": {
        "type": "euclidean",
        "steps": 16,
        "hits": 4
      }
    },
    {
      "track_id": "snare",
      "instrument": "supersnare",
      "pattern": {
        "type": "euclidean",
        "steps": 16,
        "hits": 2,
        "rotation": 4
      }
    },
    {
      "track_id": "hihat",
      "instrument": "superhat",
      "pattern": {
        "type": "euclidean",
        "steps": 16,
        "hits": 8
      },
      "params": {
        "gain": 0.5
      }
    }
  ],
  "global": {
    "cps": 2.0
  }
}
```

### 5.2 サンプルSynthDefファイル

**acid.scd:**

```supercollider
SynthDef(\acid, {
    |out=0, freq=440, gate=1, amp=0.5, cutoff=1000, res=0.5|
    var sig, env, filter;

    // Sawtooth wave
    sig = Saw.ar(freq);

    // Filter envelope
    env = EnvGen.ar(
        Env.adsr(0.01, 0.3, 0.5, 0.1),
        gate,
        doneAction: Done.freeSelf
    );

    // Resonant low-pass filter
    filter = MoogFF.ar(sig, cutoff * env, res);

    // Output
    Out.ar(out, filter * amp * env);
}).add;
```

**pad.scd:**

```supercollider
SynthDef(\pad, {
    |out=0, freq=440, gate=1, amp=0.3, attack=1.0, release=2.0|
    var sig, env;

    // Multiple detuned saws for richness
    sig = Mix.ar([
        Saw.ar(freq * 0.99),
        Saw.ar(freq),
        Saw.ar(freq * 1.01)
    ]) / 3;

    // Slow envelope
    env = EnvGen.ar(
        Env.asr(attack, 1.0, release),
        gate,
        doneAction: Done.freeSelf
    );

    // Low-pass filter
    sig = LPF.ar(sig, 2000);

    // Output
    Out.ar(out, sig * amp * env ! 2);
}).add;
```

**kick.scd:**

```supercollider
SynthDef(\kick, {
    |out=0, freq=60, amp=1.0, decay=0.3|
    var sig, env, freqEnv;

    // Frequency envelope (pitch drops quickly)
    freqEnv = EnvGen.ar(
        Env.perc(0.001, 0.1),
        levelScale: freq * 10,
        levelBias: freq
    );

    // Amplitude envelope
    env = EnvGen.ar(
        Env.perc(0.001, decay),
        doneAction: Done.freeSelf
    );

    // Sine wave with frequency envelope
    sig = SinOsc.ar(freqEnv);

    // Output
    Out.ar(out, sig * amp * env ! 2);
}).add;
```

---

## 6. Claude Code 統合要件

### 6.1 JSON 出力モード

**要件:**
- `--json` フラグで全出力を JSON 形式に統一
- 成功時: `{"status": "success", "message": "...", "data": {...}}`
- 失敗時: `{"status": "error", "message": "...", "details": "..."}`

**終了コード:**
- 0: 成功
- 1: 一般的なエラー
- 2: バリデーションエラー
- 3: タイムアウト
- 4: 接続エラー

### 6.2 使用例（Claude Code から）

```python
# Claude Code内でのOiduna操作例

import subprocess
import json

def oiduna_play_pattern(pattern_file: str) -> dict:
    """Oiduna経由でパターンを実行"""
    result = subprocess.run(
        ["oiduna", "--json", "play", pattern_file],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f"Oiduna error: {result.stderr}")

    return json.loads(result.stdout)


def oiduna_check_status() -> dict:
    """Oidunaのステータス確認"""
    result = subprocess.run(
        ["oiduna", "--json", "status"],
        capture_output=True,
        text=True
    )

    return json.loads(result.stdout)


# 使用例
try:
    status = oiduna_check_status()
    if status["data"]["status"] == "healthy":
        result = oiduna_play_pattern("pattern.json")
        print(f"Pattern started: {result['data']['track_id']}")
except Exception as e:
    print(f"Error: {e}")
```

### 6.3 ドライラン・検証モード

**要件:**
- `oiduna validate <pattern>` で実行せずに検証のみ
- エラー詳細を JSON で返す
- Claude Code がパターン生成後に検証可能

---

## 7. テスト要件

### 7.1 oiduna_client テスト

**ファイル:** `tests/test_oiduna_client.py`

**テストケース:**
1. `test_pattern_submit_success` - パターン送信成功
2. `test_pattern_submit_timeout` - タイムアウト処理
3. `test_synthdef_load_success` - SynthDefロード成功
4. `test_synthdef_load_invalid_name` - 無効な名前でバリデーションエラー
5. `test_sample_load_success` - サンプルロード成功
6. `test_buffer_list` - バッファリスト取得
7. `test_health_check` - ヘルスチェック
8. `test_health_wait_ready` - 準備待機

**モック:**
- `httpx.AsyncClient` をモック
- レスポンスを Mock オブジェクトで返す

### 7.2 oiduna_cli テスト

**ファイル:** `tests/test_oiduna_cli.py`

**テストケース:**
1. `test_cli_play_command` - play コマンド実行
2. `test_cli_json_output` - JSON 出力モード
3. `test_cli_exit_codes` - 終了コード確認
4. `test_repl_basic_commands` - REPL 基本コマンド

**テスト方法:**
- `click.testing.CliRunner` を使用
- 一時ファイルでパターン・SynthDef を作成

### 7.3 統合テスト（手動）

**前提条件:**
1. SuperCollider + SuperDirt が起動済み
2. Oiduna API が起動済み（localhost:8000）

**テスト手順:**
1. `oiduna status` でヘルス確認
2. `oiduna synthdef load samples/synthdefs/kick.scd` でSynthDefロード
3. `oiduna play samples/patterns/basic_kick.json` でパターン実行
4. `oiduna sample list` でバッファ確認
5. `oiduna stop` で停止

---

## 8. 実装チェックリスト

### Phase 2.1-A: oiduna_client ライブラリ（3-4日）

- [ ] **Day 1: 基盤構築**
  - [ ] プロジェクト構造作成（packages/oiduna_client/）
  - [ ] pyproject.toml 設定（依存関係）
  - [ ] models.py 作成（Pydantic モデル全定義）
  - [ ] exceptions.py 作成（カスタム例外）
  - [ ] config.py 作成（設定）

- [ ] **Day 2: クライアント実装**
  - [ ] client.py 作成（OidunaClient）
  - [ ] health.py 作成（HealthClient）
  - [ ] patterns.py 作成（PatternClient）
    - [ ] submit(), validate(), get_active(), stop() 実装

- [ ] **Day 3: SuperDirt クライアント実装**
  - [ ] synthdef.py 作成（SynthDefClient）
    - [ ] load(), load_from_file() 実装
  - [ ] samples.py 作成（SampleClient）
    - [ ] load(), list_buffers() 実装

- [ ] **Day 4: テスト**
  - [ ] tests/test_oiduna_client.py 作成
  - [ ] 各クライアントのユニットテスト作成（モック使用）
  - [ ] 手動統合テスト（実際の Oiduna API と接続）

### Phase 2.1-B: oiduna_cli ツール（3-4日）

- [ ] **Day 5: CLI 基盤**
  - [ ] プロジェクト構造作成（packages/oiduna_cli/）
  - [ ] pyproject.toml 設定
  - [ ] main.py 作成（エントリポイント、グローバルオプション）
  - [ ] utils/output.py 作成（OutputFormatter）

- [ ] **Day 6: コマンド実装（前半）**
  - [ ] commands/play.py 作成（play, validate, stop）
  - [ ] commands/status.py 作成（status）

- [ ] **Day 7: コマンド実装（後半）+ REPL**
  - [ ] commands/synthdef.py 作成（synthdef load）
  - [ ] commands/sample.py 作成（sample load, sample list）
  - [ ] repl/shell.py 作成（OidunaREPL）
  - [ ] commands/repl.py 作成（REPL エントリポイント）

- [ ] **Day 8: テスト + 統合**
  - [ ] tests/test_oiduna_cli.py 作成
  - [ ] CLI テスト（CliRunner）
  - [ ] 手動統合テスト（全コマンド確認）

### Phase 2.1-C: サンプルファイル（1日）

- [ ] **Day 9: サンプル作成**
  - [ ] samples/patterns/ ディレクトリ作成
    - [ ] basic_kick.json
    - [ ] basic_hihat.json
    - [ ] simple_beat.json
    - [ ] complex_pattern.json
  - [ ] samples/synthdefs/ ディレクトリ作成
    - [ ] acid.scd
    - [ ] pad.scd
    - [ ] kick.scd
  - [ ] README.md 作成（サンプル使用方法）

### Phase 2.1-D: ドキュメント（1日）

- [ ] **Day 10: ドキュメント整備**
  - [ ] README.md 更新（oiduna_client, oiduna_cli）
  - [ ] USAGE.md 作成（CLI 使用例）
  - [ ] EXAMPLES.md 作成（Claude Code 統合例）
  - [ ] ADR作成: `knowledge/adr/0005-oiduna-client-cli-design.md`

---

## 9. 完了条件

### 9.1 oiduna_client

- [ ] 全エンドポイントに対応するクライアントメソッドが実装されている
- [ ] Pydantic モデルで型安全な API が提供されている
- [ ] カスタム例外で明確なエラーハンドリングが可能
- [ ] ユニットテストが全て通過（カバレッジ 80%+）
- [ ] 実際の Oiduna API と接続して動作確認完了

### 9.2 oiduna_cli

- [ ] コマンドモードで全機能が利用可能（play, validate, stop, synthdef, sample, status）
- [ ] インタラクティブ REPL が動作
- [ ] `--json` フラグで JSON 出力が可能（Claude Code 対応）
- [ ] 終了コードが適切に設定されている（0/1/2/3/4）
- [ ] CLI テストが全て通過
- [ ] 手動統合テストで全コマンド動作確認完了

### 9.3 サンプルファイル

- [ ] 最低4つのパターンファイルが提供されている
- [ ] 最低3つのSynthDefファイルが提供されている
- [ ] 各サンプルが実際に動作することを確認済み
- [ ] README で使用方法が説明されている

### 9.4 ドキュメント

- [ ] oiduna_client の API リファレンスが完備
- [ ] oiduna_cli の全コマンド説明が完備
- [ ] Claude Code からの使用例が記載されている
- [ ] ADR でライブラリ・CLI の設計決定が記録されている

---

## 10. 注意事項・Tips

### 10.1 非同期処理

- `oiduna_client` は完全非同期（`async/await`）
- CLI 側で `asyncio.run()` でラップして同期的に使用
- REPL でも `asyncio.run()` で実行

### 10.2 エラーハンドリング

**優先度:**
1. カスタム例外（ValidationError, TimeoutError, etc.）を使用
2. `httpx.HTTPStatusError` を適切に変換
3. 明確なメッセージとコンテキストを提供

### 10.3 テスタビリティ

- `httpx.AsyncClient` を依存性注入で受け取る設計
- テストでモッククライアントを簡単に注入可能
- `CliRunner` で CLI テストを自動化

### 10.4 Claude Code からの使用

- JSON 出力モードを必ず実装
- 終了コードを正しく設定
- stderr にエラー詳細、stdout にJSON結果

### 10.5 Phase 2 への橋渡し

- request_id フィールドは Phase 2 で追加予定
- 現状は空文字列 or ダミー値で対応
- モデル定義には含めておく（Optional）

---

## 11. 参考資料

### 11.1 既存実装

- Oiduna API 実装: `/home/tobita/study/livecoding/oiduna/packages/oiduna_api/`
- Oiduna Phase 1 完了コード（参考）

### 11.2 設計ドキュメント

- `knowledge/research/oiduna-cli-design.md` - CLI 設計書
- `knowledge/adr/0004-phase-roadmap-v2.md` - Phase ロードマップ
- `knowledge/discussions/2026-02-22-distribution-design.md` - ディストリビューション設計

### 11.3 外部ドキュメント

- httpx: https://www.python-httpx.org/
- Click: https://click.palletsprojects.com/
- Pydantic: https://docs.pydantic.dev/
- prompt-toolkit: https://python-prompt-toolkit.readthedocs.io/

---

## 12. 質問・不明点がある場合

このドキュメントで不明な点があれば、以下を確認：

1. **API仕様の詳細:** Oiduna API の OpenAPI ドキュメント（http://localhost:8000/docs）
2. **設計意図:** `knowledge/` ディレクトリ内の関連ドキュメント
3. **実装例:** Oiduna API の既存実装コード

---

**実装担当エージェントへ:**

このドキュメントに従って oiduna_client + oiduna_cli を実装してください。

**重要ポイント:**
1. Claude Code からも使用されることを念頭に置く（JSON出力、終了コード）
2. テスタビリティを重視（DI、モック可能な設計）
3. Phase 2 への橋渡し（request_id フィールド等）
4. サンプルファイルで即座にテスト可能にする

実装完了後、統合テストを実施して動作確認を行ってください。

---

**作成者:** Claude Code (Main Agent)
**最終更新:** 2026-02-22
