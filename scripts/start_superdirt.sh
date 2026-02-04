#!/bin/bash
# SuperDirt with Oidunaを起動するスクリプト（startup.scd不要）

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OIDUNA_DATA_PATH="$SCRIPT_DIR/../oiduna_data"

# oiduna_dataディレクトリを作成
mkdir -p "$OIDUNA_DATA_PATH/samples"
mkdir -p "$OIDUNA_DATA_PATH/synthdefs"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Starting SuperDirt with Oiduna integration..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Oiduna data: $OIDUNA_DATA_PATH"
echo ""

# SuperColliderコードを一時ファイルに生成
TEMP_SC_FILE="/tmp/oiduna_superdirt_$$.scd"

cat > "$TEMP_SC_FILE" << EOF
(
~oidunaDataPath = "$OIDUNA_DATA_PATH".standardizePath;

"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━".postln;
"Starting SuperDirt with Oiduna integration...".postln;
"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━".postln;
"".postln;

s.reboot {
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
        ~dirt.loadSoundFiles;

        if(File.exists(~oidunaDataPath +/+ "samples")) {
            ("Loading Oiduna samples from: " ++ ~oidunaDataPath +/+ "samples/*").postln;
            ~dirt.loadSoundFiles(~oidunaDataPath +/+ "samples/*");
        } {
            ("⚠ Oiduna samples directory not found: " ++ ~oidunaDataPath +/+ "samples").warn;
        };

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

        ~dirt.start(57120, 0 ! 12);
        SuperDirt.default = ~dirt;

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

# sclangを起動（インタラクティブモード）
sclang "$TEMP_SC_FILE"

# 終了時にクリーンアップ
trap "rm -f $TEMP_SC_FILE" EXIT
