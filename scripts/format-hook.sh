#!/usr/bin/env bash
# Claude Code PostToolUse hook: format and lint the file that was just edited.
#
# Deterministic work belongs in deterministic tooling, not in the model's attention.
# Reads the hook payload on stdin and dispatches by extension. Always exits 0 —
# a formatter failing must not block the edit; CI is the gate that blocks.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 0

payload=$(cat)
file=$(printf '%s' "$payload" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
print(d.get('tool_input', {}).get('file_path', ''))
" 2>/dev/null)

[ -z "$file" ] && exit 0
[ -f "$file" ] || exit 0

case "$file" in
  */node_modules/*|*/build/*|*/.next/*|*/cdk.out/*|*/.venv/*) exit 0 ;;
esac

case "$file" in
  *.py)
    uv run ruff format "$file" >/dev/null 2>&1
    uv run ruff check --fix "$file" >/dev/null 2>&1
    ;;
  *.kt|*.kts)
    # Regenerated tokens are the generator's output, not hand-written style.
    case "$file" in */core/design/Tokens.kt) exit 0 ;; esac
    (cd android && ./gradlew --quiet --offline ktlintFormat) >/dev/null 2>&1
    ;;
  *.ts|*.tsx|*.mjs|*.css)
    ;;
  packages/design-tokens/tokens.json)
    npm run tokens --silent >/dev/null 2>&1
    echo "design tokens regenerated for web and Android — commit the generated files" >&2
    ;;
esac

exit 0
