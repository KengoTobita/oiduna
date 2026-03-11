# Extension System Test Plan

Oiduna拡張システムの動作確認テストプラン。

---

## テスト環境

### 必要なもの

- **Oiduna本体**: 拡張システム実装済み
- **SuperDirt拡張**: `oiduna-extension-superdirt`
- **SuperCollider + SuperDirt**: 音出し確認用
- **HTTPクライアント**: curl または httpie
- **Python環境**: Python 3.13+, uv

---

## Phase 1: 拡張の自動発見テスト

### 1.1. entry_pointsへの登録確認

**目的**: `pip install` で拡張がentry_pointsに登録されるか

```bash
# SuperDirt拡張をインストール
cd oiduna-extension-superdirt
uv pip install -e .

# entry_pointsを確認
python3 -c "
from importlib.metadata import entry_points
eps = list(entry_points(group='oiduna.extensions'))
print(f'Found {len(eps)} extension(s):')
for ep in eps:
    print(f'  - {ep.name}: {ep.value}')
"
```

**期待される出力**:
```
Found 1 extension(s):
  - superdirt: oiduna_extension_superdirt:SuperDirtExtension
```

**✅ 成功条件**: `superdirt` が表示される

**❌ 失敗時の対処**:
- pyproject.tomlの `[project.entry-points."oiduna.extensions"]` を確認
- `uv pip install -e .` を再実行

---

### 1.2. 拡張のアンインストール確認

**目的**: `pip uninstall` で拡張が消えるか

```bash
# アンインストール
uv pip uninstall oiduna-extension-superdirt

# entry_pointsを確認
python3 -c "
from importlib.metadata import entry_points
eps = list(entry_points(group='oiduna.extensions'))
print(f'Found {len(eps)} extension(s)')
"
```

**期待される出力**:
```
Found 0 extension(s)
```

**✅ 成功条件**: 0件になる

**後処理**: 再インストール
```bash
cd oiduna-extension-superdirt
uv pip install -e .
```

---

## Phase 2: 拡張のロードテスト

### 2.1. サーバー起動時のロードログ確認

**目的**: Oiduna起動時に拡張が自動ロードされるか

```bash
cd oiduna
uvicorn oiduna_api.main:app --reload
```

**期待されるログ**:
```
INFO:     Extension registered: superdirt
INFO:     Registered router from extension: superdirt
INFO:     Starting extension: superdirt
SuperDirt extension ready
INFO:     Loop engine started
```

**✅ 成功条件**:
- `Extension registered: superdirt` が表示される
- `SuperDirt extension ready` が表示される

**❌ 失敗時の対処**:
- `discover_extensions()` がlifespan内で呼ばれているか確認
- SuperDirt拡張のインストール状況を確認

---

### 2.2. 複数拡張のロード確認（オプション）

**目的**: 複数の拡張が共存できるか

```bash
# 別の拡張を作成してインストール
# （SuperDirt拡張に加えて）

# entry_pointsを確認
python3 -c "
from importlib.metadata import entry_points
for ep in entry_points(group='oiduna.extensions'):
    print(f'{ep.name}: {ep.value}')
"
```

**期待される出力**:
```
superdirt: oiduna_extension_superdirt:SuperDirtExtension
myext: oiduna_extension_myext:MyExtension
```

**✅ 成功条件**: 複数の拡張が表示される

---

## Phase 3: カスタムエンドポイントテスト

### 3.1. `/superdirt/orbits` エンドポイント

**目的**: 拡張が提供するHTTPエンドポイントが動作するか

```bash
# サーバー起動後
curl http://localhost:8000/superdirt/orbits
```

**期待される出力**:
```json
{
  "orbit_count": 12,
  "assignments": {},
  "next_orbit": 0
}
```

**✅ 成功条件**: 200 OK、JSONが返る

---

### 3.2. `/superdirt/reset-orbits` エンドポイント

```bash
curl -X POST http://localhost:8000/superdirt/reset-orbits
```

**期待される出力**:
```json
{
  "status": "ok",
  "message": "Orbit assignments reset"
}
```

**✅ 成功条件**: 200 OK

---

### 3.3. OpenAPI仕様への反映確認

```bash
# OpenAPIドキュメントを確認
curl http://localhost:8000/openapi.json | jq '.paths | keys' | grep superdirt
```

**期待される出力**:
```
"/superdirt/orbits"
"/superdirt/panic"
"/superdirt/reset-orbits"
```

**✅ 成功条件**: SuperDirt拡張のエンドポイントがOpenAPI仕様に含まれる

---

## Phase 4: Session変換テスト（transform）

### 4.1. Orbit割り当てテスト

**目的**: `mixer_line_id` が `orbit` に変換されるか

```bash
curl -X POST http://localhost:8000/playback/session \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "destination_id": "superdirt",
        "cycle": 0.0,
        "step": 0,
        "params": {
          "s": "bd",
          "mixer_line_id": "kick"
        }
      }
    ],
    "bpm": 120.0,
    "pattern_length": 4.0
  }'
```

**期待される動作**:
- レスポンス: `{"status": "ok"}`
- 内部処理: `mixer_line_id: "kick"` → `orbit: 0` に変換
- `mixer_line_id` はメッセージから削除される

**確認方法1**: Orbit割り当てを確認
```bash
curl http://localhost:8000/superdirt/orbits
```

**期待される出力**:
```json
{
  "orbit_count": 12,
  "assignments": {
    "kick": 0
  },
  "next_orbit": 1
}
```

**✅ 成功条件**: `"kick": 0` が表示される

---

### 4.2. パラメータ名変換テスト

**目的**: `snake_case` → `camelCase` 変換が動作するか

```bash
curl -X POST http://localhost:8000/playback/session \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "destination_id": "superdirt",
        "cycle": 0.0,
        "step": 0,
        "params": {
          "s": "bd",
          "delay_send": 0.5,
          "delay_time": 0.3
        }
      }
    ],
    "bpm": 120.0,
    "pattern_length": 4.0
  }'
```

**期待される内部変換**:
```
delay_send → delaySend
delay_time → delaytime
```

**確認方法**: ログまたはデバッガーで変換後のparamsを確認

**✅ 成功条件**: パラメータ名がcamelCaseに変換される

---

### 4.3. 複数mixer_lineのOrbit割り当てテスト

**目的**: 異なるmixer_line_idが異なるorbitに割り当てられるか

```bash
curl -X POST http://localhost:8000/playback/session \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"destination_id": "superdirt", "cycle": 0.0, "step": 0,
       "params": {"s": "bd", "mixer_line_id": "kick"}},
      {"destination_id": "superdirt", "cycle": 0.0, "step": 0,
       "params": {"s": "sn", "mixer_line_id": "snare"}},
      {"destination_id": "superdirt", "cycle": 0.0, "step": 0,
       "params": {"s": "hh", "mixer_line_id": "hihat"}}
    ],
    "bpm": 120.0,
    "pattern_length": 4.0
  }'
```

```bash
curl http://localhost:8000/superdirt/orbits
```

**期待される出力**:
```json
{
  "orbit_count": 12,
  "assignments": {
    "kick": 0,
    "snare": 1,
    "hihat": 2
  },
  "next_orbit": 3
}
```

**✅ 成功条件**: 3つの異なるorbitが割り当てられる

---

## Phase 5: Runtime Hook テスト（before_send_messages）

### 5.1. CPS注入の確認（ログベース）

**目的**: 送信直前に `cps` パラメータが注入されるか

**準備**: ログレベルをDEBUGに設定（loop_engine）

```bash
# 環境変数でログレベルを設定
export LOG_LEVEL=DEBUG
uvicorn oiduna_api.main:app --reload
```

```bash
# セッションをロード
curl -X POST http://localhost:8000/playback/session \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"destination_id": "superdirt", "cycle": 0.0, "step": 0,
       "params": {"s": "bd"}}
    ],
    "bpm": 120.0,
    "pattern_length": 4.0
  }'

# 再生開始
curl -X POST http://localhost:8000/playback/start
```

**確認**: ログに `cps` パラメータが含まれることを確認
（実際のSuperDirtへの送信ログ）

**期待されるcps値**:
```
BPM 120 → cps = 120 / 60 / 4 = 0.5
```

**✅ 成功条件**: 送信メッセージに `"cps": 0.5` が含まれる

---

### 5.2. BPM変更時のCPS再計算テスト

**目的**: BPM変更後もcpsが正しく計算されるか

```bash
# セッションロード（BPM 120）
curl -X POST http://localhost:8000/playback/session \
  -d '{"messages": [...], "bpm": 120.0, "pattern_length": 4.0}'

# 再生開始
curl -X POST http://localhost:8000/playback/start

# BPMを140に変更
curl -X POST http://localhost:8000/playback/bpm \
  -H "Content-Type: application/json" \
  -d '{"bpm": 140.0}'
```

**期待される動作**:
- BPM 120時: `cps = 0.5`
- BPM 140時: `cps = 0.583...`

**確認方法**: ログまたはSuperDirtでのテンポ変化を確認

**✅ 成功条件**: BPM変更後、cpsも変わる

---

## Phase 6: 音出し確認（SuperDirt統合）

### 準備

1. **SuperColliderを起動**
```supercollider
SuperDirt.start
```

2. **Oidunaを起動**
```bash
cd oiduna
uvicorn oiduna_api.main:app --reload
```

---

### 6.1. 基本的な音出し

**目的**: SuperDirtから音が出るか

```bash
curl -X POST http://localhost:8000/playback/session \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "destination_id": "superdirt",
        "cycle": 0.0,
        "step": 0,
        "params": {"s": "bd", "gain": 0.8}
      }
    ],
    "bpm": 120.0,
    "pattern_length": 1.0
  }'

curl -X POST http://localhost:8000/playback/start
```

**期待される動作**: キックドラムが1秒に2回鳴る（BPM 120、pattern_length 1.0）

**✅ 成功条件**: 音が聞こえる

---

### 6.2. Orbit分離の確認

**目的**: 異なるorbitで異なるエフェクトがかかるか

```bash
# SuperColliderでorbit 0にreverbを追加
# SuperDirt.orbits[0].set(\room, 0.9, \size, 0.9)

curl -X POST http://localhost:8000/playback/session \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"destination_id": "superdirt", "cycle": 0.0, "step": 0,
       "params": {"s": "bd", "mixer_line_id": "kick"}},
      {"destination_id": "superdirt", "cycle": 0.5, "step": 8,
       "params": {"s": "sn", "mixer_line_id": "snare"}}
    ],
    "bpm": 120.0,
    "pattern_length": 1.0
  }'

curl -X POST http://localhost:8000/playback/start
```

**期待される動作**:
- kickはorbit 0（reverbあり）
- snareはorbit 1（reverbなし）

**✅ 成功条件**: kickにだけreverbがかかる

---

### 6.3. パラメータ名変換の音響確認

**目的**: 変換されたパラメータが実際に効くか

```bash
curl -X POST http://localhost:8000/playback/session \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "destination_id": "superdirt",
        "cycle": 0.0,
        "step": 0,
        "params": {
          "s": "bd",
          "delay_send": 0.8,
          "delay_time": 0.5
        }
      }
    ],
    "bpm": 120.0,
    "pattern_length": 1.0
  }'

curl -X POST http://localhost:8000/playback/start
```

**期待される動作**: キックドラムにディレイがかかる

**✅ 成功条件**: ディレイエフェクトが聞こえる

---

### 6.4. CPS同期の確認

**目的**: SuperDirtのテンポがOidunaのBPMと同期するか

```bash
# BPM 120でセッションロード
curl -X POST http://localhost:8000/playback/session \
  -d '{"messages": [...], "bpm": 120.0, "pattern_length": 4.0}'

curl -X POST http://localhost:8000/playback/start

# メトロノームと比較して120 BPMか確認

# BPMを140に変更
curl -X POST http://localhost:8000/playback/bpm \
  -d '{"bpm": 140.0}'

# メトロノームと比較して140 BPMか確認
```

**✅ 成功条件**: BPM変更後もテンポが正確

---

## Phase 7: パフォーマンステスト

### 7.1. before_send_messagesの実行時間測定

**ツール**: `test_extension_performance.py`

```bash
cd oiduna/packages/oiduna_loop
pytest tests/test_extension_performance.py -v -s
```

**期待される出力**:
```
1 message: mean=0.5μs, p99=1.2μs
4 messages: mean=2.1μs, p99=5.3μs
10 messages: mean=8.5μs, p99=18.7μs
```

**✅ 成功条件**: p99 < 100μs（全てのケース）

---

### 7.2. ステップタイミング精度テスト

**目的**: 拡張がタイミング精度に影響を与えないか

**方法**: 長時間再生してドリフトを測定

```bash
# BPM 120で10分間再生
curl -X POST http://localhost:8000/playback/session \
  -d '{"messages": [...], "bpm": 120.0, "pattern_length": 4.0}'

curl -X POST http://localhost:8000/playback/start

# 10分後に停止
# メトロノームとのズレを確認
```

**✅ 成功条件**: 10分後のズレが±100ms以内

---

## Phase 8: エラーハンドリングテスト

### 8.1. 拡張のtransform()エラー

**目的**: 拡張のエラーが適切に処理されるか

**準備**: SuperDirt拡張を一時的に壊す
```python
# SuperDirtExtension.transform()内に
raise ValueError("Test error")
```

```bash
curl -X POST http://localhost:8000/playback/session \
  -d '{"messages": [...], "bpm": 120.0, "pattern_length": 4.0}'
```

**期待される動作**:
- HTTPレスポンス: 500 Internal Server Error
- エラーメッセージ: `Extension 'superdirt' failed`

**✅ 成功条件**: サーバーがクラッシュせず、エラーレスポンスを返す

**後処理**: エラーを元に戻す

---

### 8.2. 拡張のbefore_send_messages()エラー

**準備**: before_send_messages()内にエラーを仕込む

```python
def before_send_messages(self, messages, current_bpm, current_step):
    raise RuntimeError("Test runtime error")
```

```bash
curl -X POST http://localhost:8000/playback/start
```

**期待される動作**: ログにエラーが記録されるが、ループは継続

**✅ 成功条件**: サーバーがクラッシュしない

---

### 8.3. 存在しない拡張のロード試行

**準備**: pyproject.tomlで存在しないクラスを指定

```toml
[project.entry-points."oiduna.extensions"]
broken = "nonexistent_module:NonExistentClass"
```

**期待される動作**: 起動時にエラーログ、起動は失敗

**✅ 成功条件**: 明確なエラーメッセージが表示される

---

## Phase 9: 統合テスト（実際のユースケース）

### 9.1. MARSからのセッション送信シミュレーション

**シナリオ**: MARSが複数トラックのセッションを送信

```bash
curl -X POST http://localhost:8000/playback/session \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"destination_id": "superdirt", "cycle": 0.0, "step": 0,
       "params": {"s": "bd", "gain": 0.8, "mixer_line_id": "kick"}},
      {"destination_id": "superdirt", "cycle": 0.0, "step": 0,
       "params": {"s": "sn", "gain": 0.7, "mixer_line_id": "snare"}},
      {"destination_id": "superdirt", "cycle": 0.0, "step": 0,
       "params": {"s": "hh", "gain": 0.6, "mixer_line_id": "hihat"}},
      {"destination_id": "superdirt", "cycle": 0.25, "step": 4,
       "params": {"s": "hh", "gain": 0.4, "mixer_line_id": "hihat"}},
      {"destination_id": "superdirt", "cycle": 0.5, "step": 8,
       "params": {"s": "sn", "gain": 0.7, "mixer_line_id": "snare"}},
      {"destination_id": "superdirt", "cycle": 0.75, "step": 12,
       "params": {"s": "hh", "gain": 0.4, "mixer_line_id": "hihat"}}
    ],
    "bpm": 120.0,
    "pattern_length": 1.0
  }'

curl -X POST http://localhost:8000/playback/start
```

**期待される動作**: 基本的なドラムパターンが鳴る

**✅ 成功条件**:
- 3つのorbitに分離される
- リズムが正確
- 音が鳴る

---

## テストチェックリスト

実行時にチェックボックスとして使用：

### Phase 1: 拡張の自動発見
- [ ] 1.1. entry_pointsへの登録確認
- [ ] 1.2. 拡張のアンインストール確認

### Phase 2: 拡張のロード
- [ ] 2.1. サーバー起動時のロードログ確認
- [ ] 2.2. 複数拡張のロード確認（オプション）

### Phase 3: カスタムエンドポイント
- [ ] 3.1. `/superdirt/orbits` エンドポイント
- [ ] 3.2. `/superdirt/reset-orbits` エンドポイント
- [ ] 3.3. OpenAPI仕様への反映確認

### Phase 4: Session変換（transform）
- [ ] 4.1. Orbit割り当てテスト
- [ ] 4.2. パラメータ名変換テスト
- [ ] 4.3. 複数mixer_lineのOrbit割り当てテスト

### Phase 5: Runtime Hook（before_send_messages）
- [ ] 5.1. CPS注入の確認
- [ ] 5.2. BPM変更時のCPS再計算テスト

### Phase 6: 音出し確認
- [ ] 6.1. 基本的な音出し
- [ ] 6.2. Orbit分離の確認
- [ ] 6.3. パラメータ名変換の音響確認
- [ ] 6.4. CPS同期の確認

### Phase 7: パフォーマンス
- [ ] 7.1. before_send_messagesの実行時間測定
- [ ] 7.2. ステップタイミング精度テスト

### Phase 8: エラーハンドリング
- [ ] 8.1. 拡張のtransform()エラー
- [ ] 8.2. 拡張のbefore_send_messages()エラー
- [ ] 8.3. 存在しない拡張のロード試行

### Phase 9: 統合テスト
- [ ] 9.1. MARSからのセッション送信シミュレーション

---

## トラブルシューティング

### 拡張が認識されない

1. entry_pointsを確認
```bash
python3 -c "from importlib.metadata import entry_points; print(list(entry_points(group='oiduna.extensions')))"
```

2. インストール状況を確認
```bash
uv pip list | grep oiduna-extension
```

3. pyproject.tomlを確認
```bash
cat pyproject.toml | grep -A 2 "entry-points"
```

### 音が出ない

1. SuperDirtが起動しているか確認
```supercollider
s.boot
SuperDirt.start
```

2. OSC接続を確認
```bash
curl http://localhost:8000/health
# "osc": {"connected": true} であることを確認
```

3. ログを確認
```bash
# Oidunaのログ
# SuperDirtへの送信ログがあるか確認
```

---

**作成日**: 2026-02-25
**バージョン**: 1.0
