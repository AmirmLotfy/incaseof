#!/usr/bin/env bash
# Mechanical half of the anti-slop rules (docs/design/DESIGN.md §2).
#
# A grep cannot see a layout, so this is a floor, not a ceiling: the
# visual-qa skill and design-reviewer agent do the part that requires looking.
# What this catches is the stuff that creeps in by autocomplete.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

SEARCH_PATHS=(apps android/app/src)
FAIL=0

# Restrict to source we author. Generated CSS/Kotlin and build output are excluded.
srcfiles() {
  find "${SEARCH_PATHS[@]}" -type f \
    \( -name '*.tsx' -o -name '*.ts' -o -name '*.css' -o -name '*.kt' -o -name '*.xml' \) \
    -not -path '*/node_modules/*' -not -path '*/.next/*' -not -path '*/out/*' \
    -not -path '*/build/*' \
    -not -name 'Tokens.kt' 2>/dev/null
}

report() {
  local label="$1" pattern="$2"
  local hits
  hits=$(srcfiles | xargs grep -nEi "$pattern" 2>/dev/null || true)
  if [ -n "$hits" ]; then
    echo "✗ $label"
    echo "$hits" | sed 's/^/    /'
    FAIL=1
  fi
}

echo "anti-slop scan"

report "gradient (docs/design/DESIGN.md §2 forbids gradients)" \
  'linear-gradient|radial-gradient|conic-gradient|mesh-gradient|Brush\.(linear|radial|sweep)Gradient'
report "glassmorphism / decorative blur" \
  'backdrop-filter|backdropFilter|blur\(|\.blur\('
report "banned marketing copy" \
  'revolutioni[sz]|reimagine|supercharge|seamless|next-generation|cutting-edge|future of safety'
report "AI-theatre language in product copy" \
  'AI is thinking|powered by AI|AI-powered|AI powered'

# Hardcoded colours: tokens exist precisely so these do not appear.
# res/values/colors.xml is the ONE documented exception: the launch window and the
# launcher icon are drawn before Compose exists, so they cannot read a token. Every other
# hardcoded hex is a defect.
hex=$(srcfiles \
      | grep -v 'res/values/colors.xml' \
      | grep -v 'res/drawable/ic_launcher_foreground.xml' \
      | xargs grep -nE '#[0-9a-fA-F]{6}\b' 2>/dev/null || true)
if [ -n "$hex" ]; then
  echo "✗ hardcoded hex colour — use var(--ico-*) or LocalIcoColors"
  echo "$hex" | sed 's/^/    /'
  FAIL=1
fi

if [ "$FAIL" -eq 0 ]; then
  echo "✓ clean — no gradients, glass, blur, banned copy or hardcoded hex"
  echo "  (layout-level slop still needs the visual-qa skill: cards-in-cards,"
  echo "   bento grids, phone-in-a-cloud heroes, generic SaaS section rhythm)"
fi
exit $FAIL
