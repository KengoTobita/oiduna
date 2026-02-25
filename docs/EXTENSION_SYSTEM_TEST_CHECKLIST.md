# Extension System Test Checklist

クイックリファレンス用の簡潔なチェックリスト。詳細は `EXTENSION_SYSTEM_TEST_PLAN.md` を参照。

---

## 🔧 セットアップ確認

```bash
# 1. 拡張のインストール
cd oiduna-extension-superdirt
uv pip install -e .

# 2. entry_points確認
python3 -c "from importlib.metadata import entry_points; print(list(entry_points(group='oiduna.extensions')))"
# → [EntryPoint(name='superdirt', ...)] が表示されればOK

# 3. Oiduna起動
cd oiduna
uvicorn oiduna_api.main:app --reload
# → "Extension registered: superdirt" が表示されればOK
```

---

## ✅ 基本機能テスト

### 1. カスタムエンドポイント

```bash
curl http://localhost:8000/superdirt/orbits
# → {"orbit_count": 12, "assignments": {}, "next_orbit": 0}
```

### 2. Session変換（Orbit割り当て）

```bash
curl -X POST http://localhost:8000/playback/session \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"destination_id": "superdirt", "cycle": 0.0, "step": 0,
       "params": {"s": "bd", "mixer_line_id": "kick"}}
    ],
    "bpm": 120.0,
    "pattern_length": 4.0
  }'

curl http://localhost:8000/superdirt/orbits
# → {"assignments": {"kick": 0}, ...}
```

### 3. 音出し確認（SuperDirt必須）

```bash
# SuperCollider起動後
curl -X POST http://localhost:8000/playback/session \
  -d '{"messages": [{"destination_id": "superdirt", "cycle": 0.0, "step": 0, "params": {"s": "bd"}}], "bpm": 120.0, "pattern_length": 1.0}'

curl -X POST http://localhost:8000/playback/start
# → キックドラムが鳴ればOK
```

---

## 🎯 重要テスト項目

| # | テスト項目 | 確認方法 | 期待結果 |
|---|-----------|---------|---------|
| 1 | entry_points登録 | `python3 -c "..."` | superdi表示 |
| 2 | 起動時ロード | ログ確認 | "Extension registered" |
| 3 | カスタムエンドポイント | `/superdirt/orbits` | 200 OK |
| 4 | Orbit割り当て | mixer_line_id送信 | orbitに変換 |
| 5 | パラメータ変換 | delay_send送信 | delaySendに変換 |
| 6 | CPS注入 | BPM変更後も同期 | テンポ変わる |
| 7 | 音出し | SuperDirtで再生 | 音が聞こえる |
| 8 | パフォーマンス | ベンチマーク実行 | p99 < 100μs |

---

## 🐛 よくある問題

### 拡張が認識されない
```bash
# 再インストール
uv pip uninstall oiduna-extension-superdirt
cd oiduna-extension-superdirt && uv pip install -e .
```

### 音が出ない
```supercollider
// SuperCollider
s.boot
SuperDirt.start
```

```bash
# Oiduna healthチェック
curl http://localhost:8000/health
# → "osc": {"connected": true} を確認
```

---

## 📝 テスト結果記録テンプレート

```
日付: 2026-XX-XX
環境: [OS名、Python版、SuperDirt版]

✅ セットアップ
✅ カスタムエンドポイント
✅ Orbit割り当て
✅ パラメータ変換
✅ CPS注入
✅ 音出し確認
✅ パフォーマンス
⚠️ [問題があった項目]

備考:
- [気づいた点]
- [改善提案]
```

---

詳細な手順は `EXTENSION_SYSTEM_TEST_PLAN.md` を参照してください。
