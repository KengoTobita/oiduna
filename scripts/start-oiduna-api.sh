#!/bin/bash
# Oiduna API 起動スクリプト（ポート57122使用）

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# ポート 57122 を使用中のプロセスを停止
echo "Checking port 57122..."
if lsof -ti:57122 > /dev/null 2>&1; then
    echo "Stopping existing process on port 57122..."
    lsof -ti:57122 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Oiduna API 起動
echo "Starting Oiduna API on port 57122..."
export PYTHONPATH="$PROJECT_ROOT/packages"
uv run python -m oiduna_api.main > /tmp/oiduna-api.log 2>&1 &
API_PID=$!

echo "Oiduna API starting (PID: $API_PID)..."

# ヘルスチェック（最大30秒待機）
for i in {1..30}; do
    if curl -s http://localhost:57122/health > /dev/null 2>&1; then
        echo "✓ Oiduna API is ready on port 57122!"
        curl -s http://localhost:57122/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:57122/health
        exit 0
    fi
    echo "Waiting for API... ($i/30)"
    sleep 1
done

echo "✗ Oiduna API failed to start within 30 seconds"
echo "Log:"
tail -50 /tmp/oiduna-api.log
exit 1
