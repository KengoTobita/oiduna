#!/bin/bash
# Oiduna SuperDirt自動起動セットアップスクリプト

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Oiduna SuperDirt 自動起動セットアップ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# SuperCollider設定ディレクトリを検出
if [ "$(uname)" == "Darwin" ]; then
    # macOS
    SC_DIR="$HOME/Library/Application Support/SuperCollider"
elif [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
    # Linux
    SC_DIR="$HOME/.local/share/SuperCollider"
else
    echo "❌ サポートされていないOS"
    exit 1
fi

echo "SuperCollider設定ディレクトリ: $SC_DIR"
echo ""

# ディレクトリ作成
mkdir -p "$SC_DIR"

# Oidunaデータディレクトリのパス（絶対パス）
OIDUNA_DATA_PATH="$(cd "$(dirname "$0")/.." && pwd)/oiduna_data"
echo "Oidunaデータディレクトリ: $OIDUNA_DATA_PATH"
echo ""

# oiduna_dataディレクトリを作成
mkdir -p "$OIDUNA_DATA_PATH/samples"
mkdir -p "$OIDUNA_DATA_PATH/synthdefs"
echo "✓ Oidunaデータディレクトリ作成完了"
echo ""

# startup.scdが既に存在するか確認
STARTUP_FILE="$SC_DIR/startup.scd"
if [ -f "$STARTUP_FILE" ]; then
    echo "⚠️  既存のstartup.scdが見つかりました"
    echo "バックアップを作成します..."
    cp "$STARTUP_FILE" "$STARTUP_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    echo "✓ バックアップ作成完了: $STARTUP_FILE.backup.*"
    echo ""
fi

# startup.scdを作成
cat > "$STARTUP_FILE" << 'EOF'
/*
Oiduna SuperDirt 自動起動スクリプト

このファイルはSuperCollider起動時に自動実行されます。
手動編集する場合は、バックアップを取ってから行ってください。
*/

(
// Oidunaデータディレクトリ（自動設定）
~oidunaDataPath = "OIDUNA_DATA_PATH_PLACEHOLDER".standardizePath;

"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━".postln;
"Starting SuperDirt with Oiduna integration...".postln;
"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━".postln;
"".postln;

s.reboot {
    // Server options
    s.options.numBuffers = 1024 * 256;
    s.options.memSize = 8192 * 32;
    s.options.numWireBufs = 2048;
    s.options.maxNodes = 1024 * 32;
    s.options.numOutputBusChannels = 2;
    s.options.numInputBusChannels = 2;

    s.waitForBoot {
        ~dirt.stop;
        ~dirt = SuperDirt(2, s);

        "Loading samples...".postln;

        // Load default Dirt-Samples
        ~dirt.loadSoundFiles;

        // Load Oiduna custom samples
        if(File.exists(~oidunaDataPath +/+ "samples")) {
            ("Loading Oiduna samples from: " ++ ~oidunaDataPath +/+ "samples/*").postln;
            ~dirt.loadSoundFiles(~oidunaDataPath +/+ "samples/*");
        } {
            ("⚠ Oiduna samples directory not found: " ++ ~oidunaDataPath +/+ "samples").warn;
        };

        // Watch Oiduna samples directory
        if(File.exists(~oidunaDataPath +/+ "samples")) {
            ~oidunaSampleWatcher = PathWatcher.new(~oidunaDataPath +/+ "samples").watch({
                |path|
                if(path.endsWith(".wav") || path.endsWith(".aiff") || path.endsWith(".aif") || path.endsWith(".aifc")) {
                    "🔄 Oiduna: New sample detected, reloading...".postln;
                    fork {
                        1.wait;
                        ~dirt.loadSoundFiles(~oidunaDataPath +/+ "samples/*");
                        "✓ Samples reloaded".postln;
                    };
                };
            });
            "✓ Watching Oiduna samples directory".postln;
        };

        // Watch Oiduna SynthDefs directory
        if(File.exists(~oidunaDataPath +/+ "synthdefs")) {
            ~oidunaSynthDefWatcher = PathWatcher.new(~oidunaDataPath +/+ "synthdefs").watch({
                |path|
                if(path.endsWith(".scd")) {
                    ("🔄 Oiduna: Loading SynthDef: " ++ path).postln;
                    fork {
                        0.5.wait;
                        try {
                            path.load;
                            ("✓ SynthDef loaded: " ++ path.basename).postln;
                        } {
                            |error|
                            ("⚠ Failed to load SynthDef: " ++ path ++ "\n" ++ error).warn;
                        };
                    };
                };
            });
            "✓ Watching Oiduna SynthDefs directory".postln;
        };

        // Start SuperDirt
        ~dirt.start(57120, 0 ! 12);
        SuperDirt.default = ~dirt;

        // Orbit shortcuts
        (
            ~d1 = ~dirt.orbits[0]; ~d2 = ~dirt.orbits[1]; ~d3 = ~dirt.orbits[2];
            ~d4 = ~dirt.orbits[3]; ~d5 = ~dirt.orbits[4]; ~d6 = ~dirt.orbits[5];
            ~d7 = ~dirt.orbits[6]; ~d8 = ~dirt.orbits[7]; ~d9 = ~dirt.orbits[8];
            ~d10 = ~dirt.orbits[9]; ~d11 = ~dirt.orbits[10]; ~d12 = ~dirt.orbits[11];
        );

        "".postln;
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━".postln;
        "✓ SuperDirt ready with Oiduna integration".postln;
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━".postln;
        "".postln;
        ("Oiduna data: " ++ ~oidunaDataPath).postln;
        "Listening on OSC port 57120".postln;
        "".postln;
    };

    s.latency = 0.3;
};
);
EOF

# パスを置換
if [ "$(uname)" == "Darwin" ]; then
    sed -i '' "s|OIDUNA_DATA_PATH_PLACEHOLDER|$OIDUNA_DATA_PATH|g" "$STARTUP_FILE"
else
    sed -i "s|OIDUNA_DATA_PATH_PLACEHOLDER|$OIDUNA_DATA_PATH|g" "$STARTUP_FILE"
fi

echo "✓ startup.scd作成完了: $STARTUP_FILE"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "セットアップ完了！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "次回からSuperCollider (sclang)を起動するだけで、"
echo "SuperDirt + Oiduna連携が自動的に起動します。"
echo ""
echo "起動方法:"
echo "  $ sclang"
echo ""
echo "元のstartup.scdに戻したい場合:"
echo "  $ cp \"$STARTUP_FILE.backup\"* \"$STARTUP_FILE\""
echo ""
