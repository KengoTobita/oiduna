#!/bin/bash
# SuperCollider startup.scdを元に戻すスクリプト

set -e

# SuperCollider設定ディレクトリを検出
if [ "$(uname)" == "Darwin" ]; then
    SC_DIR="$HOME/Library/Application Support/SuperCollider"
elif [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
    SC_DIR="$HOME/.local/share/SuperCollider"
else
    echo "❌ サポートされていないOS"
    exit 1
fi

STARTUP_FILE="$SC_DIR/startup.scd"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "SuperCollider startup.scd 復元"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# バックアップファイルを探す
BACKUP_FILES=$(ls -t "$STARTUP_FILE.backup"* 2>/dev/null || true)

if [ -z "$BACKUP_FILES" ]; then
    echo "❌ バックアップファイルが見つかりません"
    echo ""
    echo "バックアップは以下の場所に保存されます:"
    echo "  $STARTUP_FILE.backup.YYYYMMDD_HHMMSS"
    echo ""
    exit 1
fi

# 最新のバックアップを表示
echo "利用可能なバックアップ:"
echo ""
ls -lh "$STARTUP_FILE.backup"* | awk '{print $9, "(" $5 ")"}'
echo ""

# 最新のバックアップファイル
LATEST_BACKUP=$(echo "$BACKUP_FILES" | head -n 1)

read -p "最新のバックアップ ($LATEST_BACKUP) から復元しますか？ (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # 現在のstartup.scdをバックアップ
    if [ -f "$STARTUP_FILE" ]; then
        cp "$STARTUP_FILE" "$STARTUP_FILE.before_restore.$(date +%Y%m%d_%H%M%S)"
        echo "✓ 現在のファイルをバックアップしました"
    fi

    # 復元
    cp "$LATEST_BACKUP" "$STARTUP_FILE"
    echo "✓ 復元完了: $STARTUP_FILE"
    echo ""
    echo "次回のSuperCollider起動時に、元の設定が使用されます。"
else
    echo "キャンセルしました。"
fi

echo ""
