#!/bin/bash

# ============================================
# Project Phantom 起動スクリプト（Sub-agents版）
# ============================================

PROJECT_DIR={{PROJECT_DIR}}

echo "🎭 Project Phantom 起動中..."
echo ""

# --------------------------------------------
# 1. Policy Engine設定のコピー
# --------------------------------------------
echo "📋 Policy Engine設定をコピー中..."
mkdir -p ~/.gemini/policies
if [ -f "$PROJECT_DIR/.gemini/policies/phantom.toml" ]; then
    cp "$PROJECT_DIR/.gemini/policies/phantom.toml" ~/.gemini/policies/
    echo "  ✅ phantom.toml をコピーしました"
else
    echo "  ⚠️ phantom.toml が見つかりません"
fi

# --------------------------------------------
# 2. プロジェクトディレクトリの確認
# --------------------------------------------
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ プロジェクトディレクトリが存在しません: $PROJECT_DIR"
    exit 1
fi

if [ ! -f "$PROJECT_DIR/GEMINI.md" ]; then
    echo "⚠️ GEMINI.md が見つかりません（オプション）"
fi

# Sub-agents確認
if [ -d "$PROJECT_DIR/.gemini/agents" ]; then
    echo "📦 Sub-agents:"
    ls -1 "$PROJECT_DIR/.gemini/agents/" | sed 's/^/  - /'
else
    echo "❌ .gemini/agents/ が見つかりません"
    exit 1
fi

# --------------------------------------------
# 3. 既存セッションの確認
# --------------------------------------------
if tmux has-session -t phantom 2>/dev/null; then
    echo ""
    echo "⚠️  phantomセッションが既に存在します"
    read -p "削除して再作成しますか？ (y/N): " confirm
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        tmux kill-session -t phantom
        echo "既存セッションを削除しました"
    else
        echo "起動を中止します"
        exit 1
    fi
fi

# --------------------------------------------
# 4. tmuxセッション作成（画面表示用）
# --------------------------------------------
echo ""
echo "📦 tmuxセッションを作成中..."
tmux new-session -d -s phantom -n main

# --------------------------------------------
# 5. メインエージェント起動
# --------------------------------------------
echo "🎭 メインエージェントを起動中..."
tmux send-keys -t phantom:main "cd $PROJECT_DIR" C-m
sleep 1
tmux send-keys -t phantom:main "gemini" C-m
sleep 3

# --------------------------------------------
# 6. 完了
# --------------------------------------------
echo ""
echo "============================================"
echo "🎭 Project Phantom 起動完了！"
echo "============================================"
echo ""
echo "【接続方法】"
echo "  tmux attach -t phantom:main"
echo ""
echo "【停止方法】"
echo "  tmux kill-session -t phantom"
echo ""
echo "【利用可能なSub-agents（11名）】"
echo "  - navi(system.md) : オーケストレーター（指揮・調整）"
echo "  - queen   : 作戦立案・品質検査・PDCA記録"
echo "  - mona    : タスク分解・作業モード判断・PRレビュー"
echo "  - skull   : Git操作・シェルコマンド実行"
echo "  - panther : ドキュメント作成・日報"
echo "  - wolf    : バックエンド・インフラ・外部デプロイ"
echo "  - fox     : フロントエンド・UI"
echo "  - noir    : テスト・品質保証"
echo "  - crow    : デバッグ・問題解決"
echo "  - sophie  : セキュリティ監査"
echo "  - violet  : リサーチ・技術調査"
echo ""
echo "【作業モード（反映先ベース）】"
echo "  - PRフロー     : main のコード変更 → ブランチ→PR→レビュー"
echo "  - 直接コミット : 外部デプロイ(GAS等) / docs下書き → mainで直接コミット"
echo "  - Git操作なし  : Project管理・調査 → ブランチ不要"
echo "  ※ 詳細は .gemini/CHANGELOG.md を参照"
echo ""
echo "【ポイント】"
echo "  - Sub-agentsはメインエージェント(ナビ)が自動で呼び出します"
echo "  - Git操作は skull に委譲されます"
echo "  - Policy Engineで危険操作はブロックされます"
echo "  - タスク管理は Project v2 (draft item中心) で運用"
echo ""
echo "メインエージェントに接続してジョーカーとして指示を出してください！"
echo "  $ tmux attach -t phantom:main"
echo ""
