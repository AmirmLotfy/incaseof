#!/usr/bin/env bash
# Everything that must be green before a phase or milestone is called done.
# Runs all checks and reports every failure, rather than stopping at the first —
# a partial picture leads to fixing one thing at a time and re-running for ten minutes.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

FAILED=()
run() {
  local label="$1"; shift
  echo ""
  echo "─── $label ───"
  if "$@"; then
    echo "✓ $label"
  else
    echo "✗ $label"
    FAILED+=("$label")
  fi
}

run "python: tests"        uv run pytest
run "python: lint"         uv run ruff check .
run "python: format"       uv run ruff format --check .
run "python: types"        uv run mypy services
run "design tokens"        npm run tokens:check --silent
run "api contracts"        npm run contracts:check --silent
run "web: typecheck"       npm run typecheck --silent
run "web: tests"           npm run test -w @incaseof/responder --silent
run "web: build"           npm run build --silent
# After the build, because the accessibility gate drives the real production output.
run "web: accessibility"   node --import tsx --test test/a11y.test.ts
run "secrets"              python3 scripts/check-secrets.py
run "phone numbers"        python3 scripts/check-phone-numbers.py
run "anti-slop"            ./scripts/check-antislop.sh
run "android"              env -C android ./gradlew --quiet assembleDebug testDebugUnitTest lintDebug ktlintCheck
run "infra: tests"         npm run test -w @incaseof/infra --silent
run "cdk synth"            env -C infra/cdk npx --no-install cdk synth --quiet

echo ""
echo "════════════════════════════════════"
if [ ${#FAILED[@]} -eq 0 ]; then
  echo "PREFLIGHT PASSED"
  exit 0
fi
echo "PREFLIGHT FAILED (${#FAILED[@]}):"
printf '  ✗ %s\n' "${FAILED[@]}"
exit 1
