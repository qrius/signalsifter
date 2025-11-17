# Copilot Chat Session Archive

This directory stores exported GitHub Copilot chat sessions.

## Quick Export (Easiest Method)

**From terminal:**
```bash
save-chat topic_name
```

This will:
1. Create a timestamped file
2. Open it in VS Code
3. You just copy-paste your chat into it

**Steps:**
1. Run: `save-chat setup_session` (use your own topic name)
2. In VS Code Chat panel: `Cmd+A` (select all) → `Cmd+C` (copy)
3. Switch to opened file tab
4. Paste below the header: `Cmd+V`
5. Save: `Cmd+S`

## Alternative Methods

### Via VS Code Task:
- `Cmd+Shift+P` → `Tasks: Run Task` → `Export Copilot Chat`
- Enter topic name
- Copy-paste chat content into opened file

### Manual:
- Create file: `.copilot_sessions/$(date +%Y-%m-%d_%H%M%S)_topic.md`
- Copy chat content (`Cmd+A`, `Cmd+C` in chat panel)
- Paste and save

## Search Sessions

```bash
# Search for keyword
grep -r "keyword" .copilot_sessions/

# Or use VS Code task
# Cmd+Shift+P → "Tasks: Run Task" → "Search Chat History"
```

## View All Sessions

```bash
ls -lt .copilot_sessions/

# Or use VS Code task
# Cmd+Shift+P → "Tasks: Run Task" → "View Chat Sessions"
```
