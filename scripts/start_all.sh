#!/bin/bash
# Oiduna全体（SuperDirt + Oiduna API）を起動

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Oiduna システム起動"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# tmuxが利用可能かチェック
if ! command -v tmux &> /dev/null; then
    echo "⚠️  tmuxがインストールされていません"
    echo ""
    echo "tmuxをインストールしてください:"
    echo "  macOS: brew install tmux"
    echo "  Linux: sudo apt install tmux"
    echo ""
    echo "または、各コンポーネントを手動で起動してください:"
    echo "  1. SuperDirt: $SCRIPT_DIR/start_superdirt.sh"
    echo "  2. Oiduna API: cd $PROJECT_ROOT && uv run python -m oiduna_api.main"
    exit 1
fi

# tmuxセッション名
SESSION_NAME="oiduna"

# 既存のセッションがある場合は終了
tmux has-session -t "$SESSION_NAME" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "既存のOidunaセッションを終了しています..."
    tmux kill-session -t "$SESSION_NAME"
    sleep 1
fi

# 新しいtmuxセッションを作成
echo "tmuxセッション '$SESSION_NAME' を作成中..."
tmux new-session -d -s "$SESSION_NAME" -n "superdirt"

# ウィンドウ1: SuperDirt
echo "✓ ウィンドウ1: SuperDirt起動中..."
tmux send-keys -t "$SESSION_NAME:superdirt" "cd '$SCRIPT_DIR' && ./start_superdirt.sh" C-m

# ウィンドウ2: Oiduna API
echo "✓ ウィンドウ2: Oiduna API起動準備..."
tmux new-window -t "$SESSION_NAME" -n "oiduna-api"
tmux send-keys -t "$SESSION_NAME:oiduna-api" "cd '$PROJECT_ROOT'" C-m
tmux send-keys -t "$SESSION_NAME:oiduna-api" "echo 'SuperDirtの起動を待機中（10秒）...'" C-m
tmux send-keys -t "$SESSION_NAME:oiduna-api" "sleep 10" C-m
tmux send-keys -t "$SESSION_NAME:oiduna-api" "echo ''" C-m
tmux send-keys -t "$SESSION_NAME:oiduna-api" "echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'" C-m
tmux send-keys -t "$SESSION_NAME:oiduna-api" "echo 'Oiduna API起動中...'" C-m
tmux send-keys -t "$SESSION_NAME:oiduna-api" "echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'" C-m
tmux send-keys -t "$SESSION_NAME:oiduna-api" "echo ''" C-m
tmux send-keys -t "$SESSION_NAME:oiduna-api" "uv run python -m oiduna_api.main" C-m

# ウィンドウ3: コマンド用
echo "✓ ウィンドウ3: コマンドシェル準備..."
tmux new-window -t "$SESSION_NAME" -n "shell"
tmux send-keys -t "$SESSION_NAME:shell" "cd '$PROJECT_ROOT'" C-m
tmux send-keys -t "$SESSION_NAME:shell" "echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'" C-m
tmux send-keys -t "$SESSION_NAME:shell" "echo 'Oiduna コマンドシェル'" C-m
tmux send-keys -t "$SESSION_NAME:shell" "echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'" C-m
tmux send-keys -t "$SESSION_NAME:shell" "echo ''" C-m
tmux send-keys -t "$SESSION_NAME:shell" "echo 'ウィンドウ切り替え: Ctrl+b n (next), Ctrl+b p (previous)'" C-m
tmux send-keys -t "$SESSION_NAME:shell" "echo 'セッション終了: Ctrl+b :kill-session'" C-m
tmux send-keys -t "$SESSION_NAME:shell" "echo ''" C-m
tmux send-keys -t "$SESSION_NAME:shell" "echo 'ステータス確認:'" C-m
tmux send-keys -t "$SESSION_NAME:shell" "echo '  curl http://localhost:57122/health'" C-m
tmux send-keys -t "$SESSION_NAME:shell" "echo ''" C-m

# SuperDirtウィンドウに戻る
tmux select-window -t "$SESSION_NAME:superdirt"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✓ Oiduna システム起動完了"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "tmuxセッションにアタッチするには:"
echo "  tmux attach -t $SESSION_NAME"
echo ""
echo "ウィンドウ構成:"
echo "  1. superdirt   - SuperDirt (OSC port 57120)"
echo "  2. oiduna-api  - Oiduna API (HTTP port 57122)"
echo "  3. shell       - コマンドシェル"
echo ""
echo "操作方法:"
echo "  ウィンドウ切り替え: Ctrl+b n (次), Ctrl+b p (前)"
echo "  デタッチ: Ctrl+b d"
echo "  終了: Ctrl+b :kill-session"
echo ""

# 自動的にアタッチするか確認
read -p "tmuxセッションにアタッチしますか？ (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    tmux attach -t "$SESSION_NAME"
fi
