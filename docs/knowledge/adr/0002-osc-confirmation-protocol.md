# ADR-0002: OSC確認プロトコルの設計

## ステータス

承認済み

## 日付

- 作成: 2026-02-22
- 承認: 2026-02-22

## コンテキスト

### 問題

Oiduna v2 Phase 1では、SynthDefやサンプルをHTTP API経由でリモートロードする機能を実装します。しかし、従来のOSC通信は「送りっぱなし」で、SuperColliderでの処理が成功したか失敗したかをAPI側で知る手段がありませんでした。

**具体的な問題：**
- SynthDefロード失敗（構文エラー等）をユーザーに通知できない
- サンプルディレクトリが存在しない場合のエラーハンドリング不可
- タイムアウト検出ができない（SuperColliderが応答しない場合）
- HTTPレスポンスが常に200 OKになり、実際の結果が分からない

### 制約

- SuperColliderとの通信はOSCプロトコル（UDP）を使用
- FastAPI（asyncio）との統合が必要
- Pythonの`pythonosc`ライブラリを使用
- レイテンシ増加は最小限に（目標: <100ms）

### 要件

- **機能要件:**
  - SuperColliderからの確認メッセージ受信
  - 成功/失敗の判定
  - エラーメッセージの取得
  - タイムアウト検出（デフォルト5秒）

- **非機能要件:**
  - スレッドセーフ（OSCスレッド ↔ asyncio）
  - 複数の同時リクエストをサポート
  - 低レイテンシ（確認待機時間 <100ms）

## 決定事項

**双方向OSC通信プロトコルを実装する。**

### アーキテクチャ

```
┌─────────────┐                    ┌──────────────────┐
│  FastAPI    │  OSC (Port 57120)  │  SuperCollider   │
│  (Python)   │───────────────────>│  (scsynth/       │
│             │  1. Send command   │   supernova)     │
│             │                    │                  │
│             │  OSC (Port 57121)  │                  │
│             │<───────────────────│  2. Send confirm │
│             │                    │                  │
└─────────────┘                    └──────────────────┘
     ↑
     │ 3. HTTP Response
     ↓
┌─────────────┐
│   Client    │
│  (Browser/  │
│   curl)     │
└─────────────┘
```

### 実装詳細

**1. ポート構成:**
- **送信ポート (57120):** Oiduna → SuperCollider（コマンド送信）
- **受信ポート (57121):** SuperCollider → Oiduna（確認受信）

**2. SuperCollider側（OSCdef）:**
```supercollider
OSCdef(\oiduna_synthdef_load, { |msg|
    var name = msg[1].asString;
    var code = msg[2].asString;
    var responseAddr = NetAddr("127.0.0.1", 57121);

    fork {
        try {
            code.interpret;
            s.sync;
            // 成功確認
            responseAddr.sendMsg(
                '/oiduna/synthdef/loaded',
                name,
                1  // success flag
            );
        } { |error|
            // 失敗確認
            responseAddr.sendMsg(
                '/oiduna/synthdef/loaded',
                name,
                0,  // failure flag
                error.errorString
            );
        };
    };
}, '/oiduna/synthdef/load');
```

**3. Python側（OSC Receiver）:**

`SuperDirtOscReceiver`クラス:
- バックグラウンドスレッドで`ThreadingOSCUDPServer`を実行
- 受信した確認を`asyncio.Queue`に格納
- `wait_for_confirmation()`メソッドでタイムアウト付き待機

**4. スレッド間ブリッジ:**
```python
def _handle_osc_message(self, address: str, *args: Any) -> None:
    confirmation = OscConfirmation(address=address, args=args)
    # スレッドセーフな配信
    self._loop.call_soon_threadsafe(
        self._confirmation_queue.put_nowait,
        confirmation
    )
```

**5. フィルタ関数:**
複数の同時リクエストを区別するため、フィルタ関数で名前マッチング:
```python
confirmation = await receiver.wait_for_confirmation(
    '/oiduna/synthdef/loaded',
    timeout=5.0,
    filter_func=lambda args: args[0] == req.name
)
```

**成功基準:**
- SuperColliderからの確認メッセージを正しく受信
- タイムアウトが正常に動作（5秒）
- 複数の同時リクエストで確認が混同しない
- エラーメッセージがHTTPレスポンスに含まれる

## 理由

1. **信頼性:** コマンド実行結果を確実に把握できる
2. **ユーザー体験:** エラーの原因を明確に通知可能
3. **デバッグ性:** SuperColliderのエラーをAPI経由で確認可能
4. **標準プロトコル:** OSCは既存のSuperCollider通信と同じ
5. **シンプル性:** UDPベースで追加の依存なし

## 代替案

### 案1: HTTPポーリング

**概要:** SuperColliderにHTTPサーバーを立て、Pythonからポーリングで結果取得

**長所:**
- HTTPは確認応答が標準
- RESTfulなインターフェース

**短所:**
- SuperColliderにHTTPサーバー実装が必要（複雑）
- ポーリングによるレイテンシ増加
- SuperColliderの依存関係増加（HTTPライブラリ）
- OSCとHTTPの2つのプロトコル混在

**却下理由:**
SuperColliderでのHTTPサーバー実装は複雑で、OSCで十分実現可能。

### 案2: WebSocket双方向通信

**概要:** PythonとSuperCollider間でWebSocket接続

**長所:**
- 双方向通信が標準
- リアルタイム性が高い
- 接続状態の管理が容易

**短所:**
- SuperColliderにWebSocketライブラリが必要
- OSCより複雑なプロトコル
- 接続維持のオーバーヘッド
- SuperColliderエコシステムで一般的でない

**却下理由:**
OSCで実現可能な機能にWebSocketは過剰。既存のOSC通信と統一した方がシンプル。

### 案3: 共有ファイルシステム

**概要:** SuperColliderが結果をファイルに書き込み、Pythonが読み取る

**長所:**
- ネットワーク不要
- 実装が簡単

**短所:**
- ファイルI/Oのオーバーヘッド
- ファイル競合の管理が必要
- リアルタイム性が低い
- 一時ファイルのクリーンアップが必要

**却下理由:**
パフォーマンスとリアルタイム性が要件を満たさない。

### 案4: 確認なし（送りっぱなし）

**概要:** v1同様、OSC送信のみで確認なし

**長所:**
- 実装が最も簡単
- レイテンシゼロ

**短所:**
- エラーハンドリング不可
- ユーザー体験が悪い（失敗しても分からない）
- デバッグが困難

**却下理由:**
Phase 1の目標である「信頼性の向上」に反する。

## 影響

### プラスの影響

- **信頼性向上:** コマンド実行結果を確実に取得
- **エラー通知:** 失敗理由をユーザーに提示可能
- **タイムアウト検出:** SuperCollider無応答を検出
- **デバッグ容易性:** SuperColliderエラーをAPI経由で確認

### マイナスの影響

- **レイテンシ増加:** 確認待機分（実測: 10-50ms）
- **複雑性増加:** OSCレシーバー実装が必要
- **スレッド管理:** OSCスレッドとasyncioの統合

### リスク

- **リスク:** OSCレシーバースレッドのクラッシュ
  - **軽減策:** 例外ハンドリング、ログ記録、ヘルスチェック

- **リスク:** 確認メッセージの混同（同時リクエスト）
  - **軽減策:** フィルタ関数で名前マッチング（Phase 2でリクエストID導入）

- **リスク:** タイムアウト値が環境依存
  - **軽減策:** 設定ファイルでタイムアウト値を変更可能

### 移行コスト

- **工数:** 約2日（レシーバー実装、SuperColliderスクリプト、テスト）
- **技術的負債:** スレッド管理の複雑性（将来的にはRust化で解消可能）
- **学習コスト:** 開発者はOSC双方向通信を理解する必要

## 検証方法

1. **正常系テスト:**
   - SynthDefロード成功時、200 OKとloaded: trueが返る
   - サンプルロード成功時、200 OKとloaded: trueが返る

2. **異常系テスト:**
   - 構文エラーのSynthDef → 200 OKだがloaded: false、エラーメッセージ含む
   - 存在しないパス → 400 Bad Request

3. **タイムアウトテスト:**
   - SuperColliderを停止 → 504 Gateway Timeout

4. **同時リクエストテスト:**
   - 2つの異なるSynthDefを同時ロード → 両方正しく確認受信

5. **パフォーマンステスト:**
   - 確認待機時間を測定 → 目標: <100ms

## 関連するADR

- [ADR-0001: supernova マルチコア処理] - SuperCollider通信基盤

## 参考資料

- [pythonosc Documentation](https://pypi.org/project/python-osc/)
- [SuperCollider OSCdef Guide](https://doc.sccode.org/Classes/OSCdef.html)
- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [Oiduna Phase 1 Implementation](../../oiduna/docs/PHASE1_IMPLEMENTATION_SUMMARY.md)

## メモ

### Phase 2での改善予定

1. **リクエストID導入:**
   - 各リクエストに一意のIDを付与
   - フィルタ関数を名前ではなくIDでマッチング
   - 同名の同時リクエストにも対応

2. **WebSocket通知:**
   - 長時間かかる処理（大量サンプルロード等）の進捗通知
   - クライアントにリアルタイム更新

3. **メッセージキュー:**
   - 高負荷時の確認メッセージバッファリング
   - 優先度付きキュー（重要なコマンドを優先処理）

### 実装時の考慮事項

- OSCレシーバーのポートが既に使用中の場合のエラーハンドリング
- レシーバースレッドの優雅な停止（アプリケーション終了時）
- 確認キューのメモリ制限（無限に溜まらないように）

## 履歴

- 2026-02-22: 初稿作成（ステータス: 提案中）
- 2026-02-22: Phase 1実装完了により承認（ステータス: 承認済み）
