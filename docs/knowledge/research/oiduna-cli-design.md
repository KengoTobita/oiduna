# oiduna-cli 設計提案

**作成日:** 2026-02-22
**目的:** Oiduna開発を加速する軽量クライアント

## 背景

### 問題

MARS_for_oidunaのようなフルスタックディストリビューションに依存すると：

1. **開発のボトルネック**
   - MARS DSL開発が進まないとOiduna機能確認できない
   - DSLのバグがOiduna開発を妨げる

2. **フィードバックループの遅延**
   - 新機能実装 → MARS DSL対応 → テスト
   - 段階が多く、時間がかかる

3. **機能確認の煩雑さ**
   - curlで毎回JSONを書くのは面倒
   - IRの手書きは間違いやすい

### 解決策

**DI的な軽量クライアント:**
- DSLコンパイラ不要
- Oiduna IRを直接投げられる
- 各APIを簡単にテスト
- Oiduna開発と並行して使える

---

## oiduna-cli の設計

### コンセプト

```
oiduna-cli = Oiduna本体の「リモコン」

- 人間が手軽に操作できるCLI
- Oiduna IRを直接扱える
- 全APIエンドポイントをカバー
- インタラクティブ/バッチ両対応
```

### 2つのモード

#### Mode 1: コマンドラインモード

```bash
# 1回きりのコマンド実行
oiduna apply scene.json
oiduna play
oiduna stop
oiduna load-synthdef kick kick.scd
oiduna list-buffers
```

**用途:**
- シェルスクリプトでの自動化
- CI/CDでのテスト
- クイックな動作確認

#### Mode 2: インタラクティブモード

```bash
$ oiduna-cli

Oiduna CLI v2.0.0
Connected to http://localhost:8000

oiduna> help
Available commands:
  connect <url>          - Connect to Oiduna server
  apply <file.json>      - Apply scene from JSON file
  play                   - Start playback
  stop                   - Stop playback
  bpm <value>            - Set BPM
  load-synthdef <name> <file.scd>  - Load SynthDef
  load-samples <category> <path>   - Load samples
  list-buffers           - List loaded buffers
  health                 - Check server health
  exit                   - Exit CLI

oiduna> apply examples/basic_kick.json
✓ Scene applied

oiduna> play
✓ Playing

oiduna> bpm 140
✓ BPM set to 140

oiduna> load-synthdef acid synthdefs/acid.scd
✓ SynthDef 'acid' loaded

oiduna> list-buffers
bd, sd, hh, cp, acid

oiduna> exit
```

**用途:**
- 開発中のインタラクティブテスト
- ライブコーディング風の操作
- デバッグセッション

---

## 実装案

### プロジェクト構造

```
oiduna/
└── packages/
    ├── oiduna_client/         # Pythonライブラリ
    │   ├── client.py          # HTTPクライアント
    │   ├── models.py          # リクエスト/レスポンス
    │   └── exceptions.py      # エラー定義
    └── oiduna_cli/            # CLIツール
        ├── __main__.py        # エントリーポイント
        ├── commands.py        # コマンド定義
        ├── interactive.py     # インタラクティブシェル
        └── utils.py           # ヘルパー関数
```

### oiduna_client（基盤ライブラリ）

```python
# packages/oiduna_client/client.py

import httpx
from typing import Optional

class OidunaClient:
    """Oiduna HTTP APIクライアント"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self._client = httpx.Client(timeout=10.0)

    def apply_scene(self, scene: dict) -> dict:
        """シーン適用"""
        response = self._client.post(f"{self.base_url}/scene", json=scene)
        response.raise_for_status()
        return response.json()

    def play(self) -> dict:
        """再生開始"""
        response = self._client.post(f"{self.base_url}/playback/play")
        response.raise_for_status()
        return response.json()

    def stop(self) -> dict:
        """停止"""
        response = self._client.post(f"{self.base_url}/playback/stop")
        response.raise_for_status()
        return response.json()

    def set_bpm(self, bpm: float) -> dict:
        """BPM設定"""
        response = self._client.put(
            f"{self.base_url}/playback/bpm",
            json={"bpm": bpm}
        )
        response.raise_for_status()
        return response.json()

    def load_synthdef(self, name: str, code: str) -> dict:
        """SynthDefロード"""
        response = self._client.post(
            f"{self.base_url}/superdirt/synthdef",
            json={"name": name, "code": code}
        )
        response.raise_for_status()
        return response.json()

    def load_samples(self, category: str, path: str) -> dict:
        """サンプルロード"""
        response = self._client.post(
            f"{self.base_url}/superdirt/sample/load",
            json={"category": category, "path": path}
        )
        response.raise_for_status()
        return response.json()

    def list_buffers(self) -> dict:
        """バッファリスト"""
        response = self._client.get(f"{self.base_url}/superdirt/buffers")
        response.raise_for_status()
        return response.json()

    def health(self) -> dict:
        """ヘルスチェック"""
        response = self._client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
```

### oiduna_cli（コマンドラインツール）

#### コマンドモード

```python
# packages/oiduna_cli/commands.py

import click
import json
from pathlib import Path
from oiduna_client import OidunaClient

@click.group()
@click.option('--url', default='http://localhost:8000', help='Oiduna server URL')
@click.pass_context
def cli(ctx, url):
    """Oiduna CLI - Control Oiduna from command line"""
    ctx.ensure_object(dict)
    ctx.obj['client'] = OidunaClient(url)

@cli.command()
@click.argument('file', type=click.Path(exists=True))
@click.pass_context
def apply(ctx, file):
    """Apply scene from JSON file"""
    client = ctx.obj['client']
    scene = json.loads(Path(file).read_text())
    result = client.apply_scene(scene)
    click.echo(f"✓ Scene applied")

@cli.command()
@click.pass_context
def play(ctx):
    """Start playback"""
    client = ctx.obj['client']
    client.play()
    click.echo(f"✓ Playing")

@cli.command()
@click.pass_context
def stop(ctx):
    """Stop playback"""
    client = ctx.obj['client']
    client.stop()
    click.echo(f"✓ Stopped")

@cli.command()
@click.argument('value', type=float)
@click.pass_context
def bpm(ctx, value):
    """Set BPM"""
    client = ctx.obj['client']
    client.set_bpm(value)
    click.echo(f"✓ BPM set to {value}")

@cli.command('load-synthdef')
@click.argument('name')
@click.argument('file', type=click.Path(exists=True))
@click.pass_context
def load_synthdef(ctx, name, file):
    """Load SynthDef from .scd file"""
    client = ctx.obj['client']
    code = Path(file).read_text()
    result = client.load_synthdef(name, code)

    if result['loaded']:
        click.echo(f"✓ SynthDef '{name}' loaded")
    else:
        click.echo(f"✗ Failed: {result.get('message')}", err=True)

@cli.command('load-samples')
@click.argument('category')
@click.argument('path', type=click.Path(exists=True))
@click.pass_context
def load_samples(ctx, category, path):
    """Load samples from directory"""
    client = ctx.obj['client']
    result = client.load_samples(category, str(Path(path).absolute()))

    if result['loaded']:
        click.echo(f"✓ Samples '{category}' loaded")
    else:
        click.echo(f"✗ Failed: {result.get('message')}", err=True)

@cli.command('list-buffers')
@click.pass_context
def list_buffers(ctx):
    """List loaded buffers"""
    client = ctx.obj['client']
    result = client.list_buffers()
    buffers = result['buffers']
    click.echo(f"Loaded buffers ({result['count']}):")
    for buf in buffers:
        click.echo(f"  - {buf}")

@cli.command()
@click.pass_context
def health(ctx):
    """Check server health"""
    client = ctx.obj['client']
    result = client.health()
    click.echo(f"Status: {result['status']}")
    click.echo(f"SuperDirt: {'✓' if result['superdirt']['connected'] else '✗'}")
    click.echo(f"MIDI: {'✓' if result['midi']['connected'] else '✗'}")

if __name__ == '__main__':
    cli()
```

#### インタラクティブモード

```python
# packages/oiduna_cli/interactive.py

import cmd
import json
from pathlib import Path
from oiduna_client import OidunaClient

class OidunaShell(cmd.Cmd):
    intro = 'Oiduna Interactive CLI. Type help or ? to list commands.\n'
    prompt = 'oiduna> '

    def __init__(self, url='http://localhost:8000'):
        super().__init__()
        self.client = OidunaClient(url)
        print(f"Connected to {url}")

    def do_apply(self, arg):
        """Apply scene from JSON file: apply <file.json>"""
        try:
            scene = json.loads(Path(arg).read_text())
            self.client.apply_scene(scene)
            print("✓ Scene applied")
        except Exception as e:
            print(f"✗ Error: {e}")

    def do_play(self, arg):
        """Start playback"""
        try:
            self.client.play()
            print("✓ Playing")
        except Exception as e:
            print(f"✗ Error: {e}")

    def do_stop(self, arg):
        """Stop playback"""
        try:
            self.client.stop()
            print("✓ Stopped")
        except Exception as e:
            print(f"✗ Error: {e}")

    def do_bpm(self, arg):
        """Set BPM: bpm <value>"""
        try:
            bpm = float(arg)
            self.client.set_bpm(bpm)
            print(f"✓ BPM set to {bpm}")
        except Exception as e:
            print(f"✗ Error: {e}")

    def do_load_synthdef(self, arg):
        """Load SynthDef: load-synthdef <name> <file.scd>"""
        try:
            parts = arg.split()
            name = parts[0]
            file = parts[1]
            code = Path(file).read_text()
            result = self.client.load_synthdef(name, code)

            if result['loaded']:
                print(f"✓ SynthDef '{name}' loaded")
            else:
                print(f"✗ Failed: {result.get('message')}")
        except Exception as e:
            print(f"✗ Error: {e}")

    def do_list_buffers(self, arg):
        """List loaded buffers"""
        try:
            result = self.client.list_buffers()
            print(f"Loaded buffers ({result['count']}):")
            for buf in result['buffers']:
                print(f"  - {buf}")
        except Exception as e:
            print(f"✗ Error: {e}")

    def do_health(self, arg):
        """Check server health"""
        try:
            result = self.client.health()
            print(f"Status: {result['status']}")
            print(f"SuperDirt: {'✓' if result['superdirt']['connected'] else '✗'}")
            print(f"MIDI: {'✓' if result['midi']['connected'] else '✗'}")
        except Exception as e:
            print(f"✗ Error: {e}")

    def do_exit(self, arg):
        """Exit CLI"""
        print("Goodbye!")
        return True

    def do_EOF(self, arg):
        """Exit on EOF (Ctrl+D)"""
        print()
        return self.do_exit(arg)

if __name__ == '__main__':
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8000'
    OidunaShell(url).cmdloop()
```

---

## サンプルIRファイル集

開発用のサンプルIRを提供：

```
oiduna/
└── examples/
    ├── basic_kick.json          # 基本的なキックパターン
    ├── four_on_floor.json       # 4つ打ち
    ├── minimal_techno.json      # ミニマルテクノ
    ├── multi_track.json         # 複数トラック
    └── synthdefs/
        ├── kick.scd             # キックSynthDef
        ├── acid.scd             # 303風ベース
        └── pad.scd              # パッド
```

### basic_kick.json

```json
{
  "environment": {
    "bpm": 120
  },
  "tracks": [
    {
      "id": "bd",
      "sound": "bd",
      "orbit": 0,
      "gain": 0.9,
      "pan": 0.5,
      "muted": false,
      "solo": false,
      "length": 1,
      "sequence": [
        {"pitch": "0", "length": 0.25},
        {"pitch": "~", "length": 0.25},
        {"pitch": "~", "length": 0.25},
        {"pitch": "~", "length": 0.25}
      ]
    }
  ],
  "scenes": []
}
```

### four_on_floor.json

```json
{
  "environment": {
    "bpm": 128
  },
  "tracks": [
    {
      "id": "bd",
      "sound": "bd",
      "orbit": 0,
      "gain": 1.0,
      "sequence": [
        {"pitch": "0", "length": 0.25},
        {"pitch": "0", "length": 0.25},
        {"pitch": "0", "length": 0.25},
        {"pitch": "0", "length": 0.25}
      ]
    },
    {
      "id": "hh",
      "sound": "hh",
      "orbit": 1,
      "gain": 0.6,
      "sequence": [
        {"pitch": "0", "length": 0.125},
        {"pitch": "0", "length": 0.125},
        {"pitch": "0", "length": 0.125},
        {"pitch": "0", "length": 0.125},
        {"pitch": "0", "length": 0.125},
        {"pitch": "0", "length": 0.125},
        {"pitch": "0", "length": 0.125},
        {"pitch": "0", "length": 0.125}
      ]
    }
  ]
}
```

---

## 使用例

### 開発ワークフロー

```bash
# 1. Oiduna起動（別ターミナル）
cd oiduna
uv run python -m oiduna_api.main

# 2. SuperCollider起動・ブート

# 3. oiduna-cliでテスト
cd oiduna

# ヘルスチェック
uv run oiduna health

# サンプルIRを投げる
uv run oiduna apply examples/basic_kick.json
uv run oiduna play

# BPM変更
uv run oiduna bpm 140

# SynthDefロード
uv run oiduna load-synthdef kick examples/synthdefs/kick.scd

# バッファ確認
uv run oiduna list-buffers

# インタラクティブモード
uv run oiduna-cli

oiduna> apply examples/four_on_floor.json
✓ Scene applied

oiduna> play
✓ Playing

oiduna> bpm 135
✓ BPM set to 135

oiduna> exit
```

### 自動化スクリプト

```bash
#!/bin/bash
# test_phase2_features.sh

# Phase 2新機能の自動テスト

echo "=== Phase 2 Feature Test ==="

# リクエストID対応確認
echo "1. Loading SynthDef with request ID..."
uv run oiduna load-synthdef test_synth examples/synthdefs/kick.scd

# サンプルメタデータ確認
echo "2. Loading samples..."
uv run oiduna load-samples custom ~/samples/custom

# バッファリスト確認
echo "3. Listing buffers..."
uv run oiduna list-buffers

# エラーハンドリング確認
echo "4. Testing error handling (invalid synthdef)..."
uv run oiduna load-synthdef invalid examples/invalid.scd || echo "Expected error"

echo "=== Test Complete ==="
```

---

## Phase 2での位置づけ

### 優先度: 高

**理由:**

1. **開発加速**
   - MARS DSL開発と並行してOiduna開発可能
   - 新機能を即座にテスト

2. **ディストリビューション参考実装**
   - oiduna_clientのベストユース
   - 他のディストリビューション作成者の参考

3. **ドキュメント・デモ**
   - 実際に動くサンプル
   - チュートリアルで使用可能

### 実装順序

**Phase 2.0:**
1. oiduna_client ライブラリ（2-3日）
2. サンプルIRファイル作成（1日）

**Phase 2.1:**
3. oiduna-cli コマンドモード（2日）
4. サンプルSynthDefファイル（1日）

**Phase 2.2:**
5. oiduna-cli インタラクティブモード（2-3日）
6. ドキュメント整備（1日）

**合計:** 9-11日

---

## メリット

### 開発者（自分）

- **即座のフィードバック:** 新機能をすぐテスト
- **DSL非依存:** MARSの進捗に左右されない
- **デバッグ容易:** IRを直接投げて問題切り分け

### ディストリビューション作成者

- **参考実装:** oiduna_clientの使い方を学べる
- **テンプレート:** CLIツールのベース
- **サンプルコード:** すぐに試せるIR例

### ユーザー

- **簡易ツール:** GUIなしでも操作可能
- **スクリプト化:** 自動化が容易
- **学習:** Oiduna IRの理解が深まる

---

## 次のステップ

### Phase 2計画への統合

**Phase 2を3段階に分ける:**

**Phase 2.0: 信頼性向上（2週間）**
1. リクエストID導入
2. 基本キュー管理
3. SynthDef検証
4. サンプルメタデータ
5. エラーハンドリング強化
6. 統合テスト

**Phase 2.1: 開発ツール（1.5週間）**
7. oiduna_client ライブラリ
8. oiduna-cli コマンドモード
9. サンプルIRファイル集
10. サンプルSynthDefファイル

**Phase 2.2: 高度な機能（0.5週間）**
11. oiduna-cli インタラクティブモード
12. IRバリデーション関数
13. ディストリビューション作成ガイド

**Phase 2合計:** 4週間

---

## まとめ

**oiduna-cli = Oiduna開発の「リモコン」**

- DSL開発とOiduna開発を分離
- 即座のフィードバック
- ディストリビューション作成の参考実装
- 簡単な自動化・テスト

**Phase 2で最優先実装すべき**
