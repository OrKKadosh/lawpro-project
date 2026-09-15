#!/bin/bash
# Blocks any git commit that stages .env or CREDENTIALS.md.
# Wired up as a PreToolUse hook on Bash in .claude/settings.json.

staged=$(git diff --cached --name-only 2>/dev/null)

if echo "$staged" | grep -qE '(^|/)(\.env|CREDENTIALS\.md)$'; then
  echo "BLOCKED: .env or CREDENTIALS.md is staged for commit. Unstage it before committing." >&2
  exit 1
fi

exit 0
