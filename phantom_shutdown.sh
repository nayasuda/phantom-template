#!/bin/bash

# ============================================
# Project Phantom 停止スクリプト
# ============================================

echo "🎭 Project Phantom を停止中..."
echo ""

# phantomセッション
if tmux has-session -t phantom 2>/dev/null; then
    tmux kill-session -t phantom
    echo "✅ phantomセッションを停止しました"
else
    echo "⚠️  phantomセッションは存在しません"
fi

# membersセッション
if tmux has-session -t members 2>/dev/null; then
    tmux kill-session -t members
    echo "✅ membersセッションを停止しました"
else
    echo "⚠️  membersセッションは存在しません"
fi

echo ""
echo "🎭 Project Phantom 停止完了"
echo ""
