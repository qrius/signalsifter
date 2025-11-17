#!/usr/bin/env zsh
# Backup VS Code Copilot Chat History
# Usage: ./scripts/backup_chat.sh [topic_name]

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="$PROJECT_ROOT/.copilot_sessions"
TIMESTAMP=$(date +"%Y-%m-%d_%H%M%S")
TOPIC="${1:-general}"

# VS Code chat history locations (macOS)
VSCODE_CHAT_DIRS=(
    "$HOME/Library/Application Support/Code/User/workspaceStorage"
    "$HOME/Library/Application Support/Code - Insiders/User/workspaceStorage"
    "$HOME/Library/Application Support/Cursor/User/workspaceStorage"
)

echo "🔍 Searching for VS Code chat history..."

# Find the workspace storage for this project
WORKSPACE_HASH=""
for chat_dir in "${VSCODE_CHAT_DIRS[@]}"; do
    if [[ -d "$chat_dir" ]]; then
        # Find workspace that matches our project
        for workspace in "$chat_dir"/*; do
            if [[ -f "$workspace/workspace.json" ]]; then
                if grep -q "SignalSifter" "$workspace/workspace.json" 2>/dev/null; then
                    WORKSPACE_HASH=$(basename "$workspace")
                    CHAT_DIR="$chat_dir/$WORKSPACE_HASH"
                    echo "✅ Found workspace: $WORKSPACE_HASH"
                    break 2
                fi
            fi
        done
    fi
done

if [[ -z "$WORKSPACE_HASH" ]]; then
    echo "⚠️  Could not auto-locate VS Code workspace storage."
    echo "📋 Manual export instructions:"
    echo "   1. Open VS Code Chat panel"
    echo "   2. Click '...' menu → 'Export Session'"
    echo "   3. Save to: $BACKUP_DIR/${TIMESTAMP}_${TOPIC}.md"
    exit 1
fi

# Look for chat history files
CHAT_FILES=(
    "$CHAT_DIR/state.vscdb"
    "$CHAT_DIR/chatHistory.json"
    "$CHAT_DIR/copilot/chatHistory.json"
)

FOUND=false
for chat_file in "${CHAT_FILES[@]}"; do
    if [[ -f "$chat_file" ]]; then
        echo "📦 Backing up: $chat_file"
        cp "$chat_file" "$BACKUP_DIR/${TIMESTAMP}_${TOPIC}_$(basename "$chat_file")"
        FOUND=true
    fi
done

if $FOUND; then
    echo "✅ Chat history backed up to: $BACKUP_DIR/"
    echo "📊 Total backups: $(ls -1 "$BACKUP_DIR" | grep -v README.md | wc -l | tr -d ' ')"
else
    echo "⚠️  No chat history files found in workspace storage."
    echo "💡 Try manual export from VS Code Chat panel"
fi

# Create index of all sessions
echo "📑 Creating session index..."
cat > "$BACKUP_DIR/INDEX.md" << EOF
# Chat Session Index
Last updated: $(date)

## Sessions

EOF

ls -t "$BACKUP_DIR"/*.md 2>/dev/null | grep -v "README.md\|INDEX.md" | while read file; do
    filename=$(basename "$file")
    size=$(wc -l < "$file" 2>/dev/null || echo "?")
    echo "- [$filename](./$filename) - $size lines" >> "$BACKUP_DIR/INDEX.md"
done

echo "✨ Done! View index: cat $BACKUP_DIR/INDEX.md"
