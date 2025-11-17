#!/usr/bin/env zsh
# Quick export of current chat session
# Usage: ./scripts/export_current_chat.sh [topic_name]

TOPIC="${1:-session}"
TIMESTAMP=$(date +"%Y-%m-%d_%H%M%S")
FILENAME="${TIMESTAMP}_${TOPIC}.md"
TARGET="$(dirname "$0")/../.copilot_sessions/$FILENAME"

echo "📝 Exporting current chat session..."
echo ""
echo "🎯 Target: $FILENAME"
echo ""
echo "📋 INSTRUCTIONS:"
echo "   1. In VS Code, open the Chat panel (Ctrl+Shift+I or Cmd+Shift+I)"
echo "   2. Click the '...' (more actions) menu in the chat panel"
echo "   3. Select 'Export Session' or 'Save Chat'"
echo "   4. Save to this location:"
echo ""
echo "      $TARGET"
echo ""
echo "   Alternatively, you can copy the chat manually and save it there."
echo ""
echo "✅ After saving, run: git add .copilot_sessions && git commit -m 'Archive chat: $TOPIC'"

# Open the directory in Finder (macOS)
open "$(dirname "$TARGET")"
