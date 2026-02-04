#!/bin/bash
# Assetsエンドポイントとの統合テスト

set -e

BASE_URL="http://localhost:8000"
OIDUNA_DATA="./oiduna_data"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Assets統合テスト"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Oiduna APIが起動しているか確認
echo "1. Oiduna APIの確認..."
if curl -s "$BASE_URL/health" > /dev/null 2>&1; then
    echo "✓ Oiduna API起動中 (port 8000)"
else
    echo "❌ Oiduna APIが起動していません"
    echo ""
    echo "起動してください:"
    echo "  uv run python -m oiduna_api.main"
    exit 1
fi
echo ""

# oiduna_dataディレクトリの確認
echo "2. oiduna_dataディレクトリの確認..."
if [ -d "$OIDUNA_DATA" ]; then
    echo "✓ oiduna_dataディレクトリ存在: $OIDUNA_DATA"
    echo "  絶対パス: $(cd $OIDUNA_DATA && pwd)"
else
    echo "⚠️  oiduna_dataディレクトリが存在しません"
    echo "  作成中..."
    mkdir -p "$OIDUNA_DATA/samples"
    mkdir -p "$OIDUNA_DATA/synthdefs"
    echo "✓ 作成完了"
fi
echo ""

# テスト用のサンプルファイルを作成
echo "3. テスト用サンプルの作成..."
TEST_SAMPLE="/tmp/test_kick.wav"

# ミニマルなWAVファイルを生成（44.1kHz, 16bit, mono, 0.1秒）
python3 << 'PYTHON'
import wave
import struct
import math

sample_rate = 44100
duration = 0.1
num_samples = int(sample_rate * duration)

with wave.open('/tmp/test_kick.wav', 'w') as wav:
    wav.setnchannels(1)
    wav.setsampwidth(2)
    wav.setframerate(sample_rate)

    for i in range(num_samples):
        # 簡単なキック音（サイン波 + エンベロープ）
        t = i / sample_rate
        freq = 100 * (1 - t / duration)  # ピッチダウン
        envelope = (1 - t / duration) ** 2  # エンベロープ
        sample = math.sin(2 * math.pi * freq * t) * envelope
        sample_int = int(sample * 32767)
        wav.writeframes(struct.pack('<h', sample_int))

print("✓ Test sample created: /tmp/test_kick.wav")
PYTHON

if [ -f "$TEST_SAMPLE" ]; then
    echo "✓ テストサンプル作成完了: $TEST_SAMPLE"
    echo "  サイズ: $(du -h $TEST_SAMPLE | cut -f1)"
else
    echo "❌ テストサンプルの作成に失敗"
    exit 1
fi
echo ""

# サンプルをアップロード
echo "4. サンプルのアップロード..."
UPLOAD_RESPONSE=$(curl -s -X POST "$BASE_URL/assets/samples" \
  -F "file=@$TEST_SAMPLE" \
  -F "category=test_kicks" \
  -F "tags=test,808")

if echo "$UPLOAD_RESPONSE" | grep -q '"status":"ok"'; then
    echo "✓ アップロード成功"
    echo "$UPLOAD_RESPONSE" | python3 -m json.tool
else
    echo "❌ アップロード失敗"
    echo "$UPLOAD_RESPONSE"
    exit 1
fi
echo ""

# ファイルシステム上で確認
echo "5. ファイルシステムの確認..."
UPLOADED_FILE="$OIDUNA_DATA/samples/test_kicks/test_kick.wav"
if [ -f "$UPLOADED_FILE" ]; then
    echo "✓ ファイルが配置されています: $UPLOADED_FILE"
    ls -lh "$UPLOADED_FILE"
else
    echo "❌ ファイルが見つかりません"
    exit 1
fi
echo ""

# サンプル一覧を取得
echo "6. サンプル一覧の確認..."
SAMPLES_RESPONSE=$(curl -s "$BASE_URL/assets/samples")
echo "$SAMPLES_RESPONSE" | python3 -m json.tool
echo ""

# SuperDirtで使用可能か確認するためのSuperColliderコード生成
echo "7. SuperCollider確認用コード..."
SC_TEST_FILE="/tmp/test_superdirt_samples.scd"
cat > "$SC_TEST_FILE" << 'EOF'
// Oidunaサンプルの確認

(
"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━".postln;
"Checking Oiduna samples in SuperDirt...".postln;
"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━".postln;
"".postln;

// SuperDirtが起動しているか確認
if(SuperDirt.default.isNil) {
    "⚠️  SuperDirt is not running!".warn;
    "Please start SuperDirt first.".postln;
} {
    var dirt = SuperDirt.default;
    var library = dirt.soundLibrary;

    "✓ SuperDirt is running".postln;
    "".postln;

    // test_kicksが登録されているか確認
    if(library.buffers[\test_kicks].notNil) {
        var buffers = library.buffers[\test_kicks];
        "✓ 'test_kicks' sample found!".postln;
        "  Number of variants: %".format(buffers.size).postln;
        buffers.do { |buf, i|
            "  [%] % frames, % channels".format(i, buf.numFrames, buf.numChannels).postln;
        };
        "".postln;
        "You can use it in Oiduna:".postln;
        "{\"sound\": \"test_kicks\", \"orbit\": 0, ...}".postln;
    } {
        "⚠️  'test_kicks' sample NOT found".warn;
        "".postln;
        "Available samples:".postln;
        library.buffers.keys.asArray.sort.do { |key|
            "  - %".format(key).postln;
        };
    };
};
);
EOF

echo "✓ SuperCollider確認用コード作成: $SC_TEST_FILE"
echo ""
echo "SuperColliderで実行してください:"
echo "  \"$SC_TEST_FILE\".load;"
echo ""
echo "または手動で確認:"
echo "  SuperDirt.default.soundLibrary.buffers.keys.postln;"
echo ""

# 結果サマリー
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "テスト結果"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✓ Oiduna API: 起動中"
echo "✓ サンプルアップロード: 成功"
echo "✓ ファイル配置: $UPLOADED_FILE"
echo ""
echo "次のステップ:"
echo "1. SuperColliderが起動していることを確認"
echo "2. SuperColliderで実行: \"$SC_TEST_FILE\".load;"
echo "3. 'test_kicks' が見つかればOK"
echo ""
echo "PathWatcherテスト:"
echo "  SuperDirt起動中に新しいサンプルをアップロードすると、"
echo "  自動的にリロードされるはずです。"
echo ""
