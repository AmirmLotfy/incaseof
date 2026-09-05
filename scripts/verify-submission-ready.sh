#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

manifest="submission/release-evidence.json"
failures=()

fail() { failures+=("$1"); }
check_file() { [[ -f "$1" ]] || fail "missing file: $1"; }
check_jq() {
  local expression="$1"
  local label="$2"
  jq -e "$expression" "$manifest" >/dev/null 2>&1 || fail "$label"
}

check_file "$manifest"
if [[ ! -f "$manifest" ]]; then
  printf 'SUBMISSION NOT READY\n  - %s\n' "${failures[@]}"
  exit 1
fi

check_jq '.status == "ACCEPTED"' "release manifest status is not ACCEPTED"
check_jq '.acceptedCommit | type == "string" and length == 40' "accepted commit is missing"
check_jq '.tag | type == "string" and length > 0' "accepted release tag is missing"
check_jq '.builderIdSupplied == true' "AWS Builder ID is not recorded"
check_jq '.videoUrl | type == "string" and test("^https://(www\\.)?(youtube\\.com|youtu\\.be|vimeo\\.com)/")' "public YouTube/Vimeo URL is missing"
check_jq '.blogUrls | type == "array" and length >= 1 and all(.[]; test("^https://builder\\.aws/"))' "at least one public builder.aws post is missing"
check_jq '.canary.runtimeReadyForRequest == true' "AgentCore runtime canary is not ready"
check_jq '.canary.runtimeInvocationId | type == "string" and length > 0' "AgentCore invocation ID is missing"
check_jq '.canary.traceId | type == "string" and length > 0' "redacted model trace ID is missing"
check_jq '.liveDeterministicDrill.terminalState == "RESOLVED"' "live deterministic Drill did not resolve"
check_jq '.liveDeterministicDrill.auditEvents | index("RESPONDER_VERIFIED") != null' "live Drill lacks explicit responder resolution"
check_jq '.android.physicalDevice == "PASSED"' "physical Android device verification is missing"
check_jq '.artifacts.projectImage | type == "string" and length > 0' "Devpost project image is not recorded"

accepted_commit=$(jq -r '.acceptedCommit // empty' "$manifest")
if [[ -n "$accepted_commit" ]] && [[ "$(git rev-parse HEAD 2>/dev/null)" != "$accepted_commit" ]]; then
  fail "working HEAD is not the accepted commit"
fi
if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
  fail "Git worktree is not clean"
fi
if [[ -n "$accepted_commit" ]] && ! git merge-base --is-ancestor "$accepted_commit" origin/main 2>/dev/null; then
  fail "accepted commit is not on public origin/main"
fi

for key in marketing webApp demo canonicalApi apk; do
  url=$(jq -r --arg key "$key" '.urls[$key] // empty' "$manifest")
  if [[ "$url" != https://* ]]; then
    fail "canonical URL is missing: $key"
    continue
  fi
  curl_args=(--silent --show-error --fail --location --max-time 20)
  if [[ "$key" != canonicalApi ]]; then
    curl_args+=(--head)
  fi
  if ! curl "${curl_args[@]}" "$url" >/dev/null; then
    fail "canonical URL is not reachable: $key"
  fi
done

apk="apps/marketing/public/downloads/in-case-of.apk"
check_file "$apk"
check_file "$apk.sha256"
if [[ -f "$apk" ]]; then
  actual_apk=$(shasum -a 256 "$apk" | awk '{print $1}')
  manifest_apk=$(jq -r '.android.sha256 // empty' "$manifest")
  checksum_apk=$(awk '{print $1}' "$apk.sha256" 2>/dev/null)
  [[ "$actual_apk" == "$manifest_apk" ]] || fail "APK hash does not match the release manifest"
  [[ "$actual_apk" == "$checksum_apk" ]] || fail "APK hash does not match the published checksum"
fi

for artifact in \
  submission/architecture/in-case-of-architecture.png \
  submission/architecture/in-case-of-architecture.pdf \
  submission/devpost/in-case-of-project-1800x1200.png; do
  check_file "$artifact"
  if [[ -f "$artifact" ]] && [[ "$(stat -f %z "$artifact")" -ge 36700160 ]]; then
    fail "artifact exceeds Devpost's 35 MB limit: $artifact"
  fi
done
if [[ -f submission/devpost/in-case-of-project-1800x1200.png ]] && command -v magick >/dev/null; then
  dimensions=$(magick identify -format '%wx%h' submission/devpost/in-case-of-project-1800x1200.png)
  [[ "$dimensions" == "1800x1200" ]] || fail "Devpost project image is not 1800x1200"
fi

for screenshot in \
  marketing-desktop.png marketing-mobile.png web-plan-preview.png android-home.png \
  android-create.png android-circle.png android-drill.png responder-claim.png \
  responder-lease.png responder-resolved.png audit-timeline.png developer-trace-redacted.png; do
  check_file "submission/screenshots/$screenshot"
done

if [[ ${#failures[@]} -gt 0 ]]; then
  echo "SUBMISSION NOT READY (${#failures[@]} blockers)"
  printf '  - %s\n' "${failures[@]}"
  exit 1
fi

echo "SUBMISSION READY: every local and externally verifiable release field passed."
