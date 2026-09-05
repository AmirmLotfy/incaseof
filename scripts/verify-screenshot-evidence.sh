#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

manifest=submission/release-evidence.json
directory=submission/screenshots
failures=()
fail() { failures+=("$1"); }
need_file() { [[ -s "$1" ]] || fail "missing or empty: $1"; }

for command in git jq magick rg shasum; do
  command -v "$command" >/dev/null 2>&1 || fail "required command is unavailable: $command"
done
need_file "$manifest"

browser=(
  marketing-desktop.png marketing-mobile.png web-plan-preview.png responder-claim.png
  responder-lease.png responder-resolved.png audit-timeline.png developer-trace-redacted.png
)
android=(android-home.png android-create.png android-circle.png android-drill.png)
for screenshot in "${browser[@]}" "${android[@]}"; do
  need_file "$directory/$screenshot"
done

web_provenance="$directory/web-provenance.json"
need_file "$web_provenance"
if [[ -s "$web_provenance" ]]; then
  jq -e '
    .mode == "final" and
    (.baseUrl | test("^https://(www\\.)?incaof\\.com$")) and
    (.captures | type == "array" and length == 8) and
    all(.captures[]; .filename and .sha256 and (.sourceUrl | test("^https://(www\\.)?incaof\\.com/")))
  ' "$web_provenance" >/dev/null 2>&1 || fail "web provenance is not a canonical final capture record"
  if rg -q '/(r|i)/(?!\[redacted\])' "$web_provenance" --pcre2; then
    fail "web provenance contains an unredacted signed-link path"
  fi
  while IFS=$'\t' read -r filename recorded; do
    path="$directory/$filename"
    if [[ -s "$path" ]]; then
      actual=$(shasum -a 256 "$path" | awk '{print $1}')
      [[ "$actual" == "$recorded" ]] || fail "web capture hash mismatch: $filename"
    else
      fail "web provenance points to a missing capture: $filename"
    fi
  done < <(jq -r '.captures[]? | [.filename, .sha256] | @tsv' "$web_provenance")
fi

for screenshot in "${android[@]}"; do
  sidecar="$directory/${screenshot%.png}.provenance.json"
  need_file "$sidecar"
  if [[ -s "$sidecar" ]]; then
    jq -e --arg filename "$screenshot" '
      .filename == $filename and
      .app.packageName == "com.incaof.app" and
      (.device.sdk >= 26) and
      (.sha256 | test("^[0-9a-f]{64}$")) and
      (.deviceSerialSha256 | test("^[0-9a-f]{64}$"))
    ' "$sidecar" >/dev/null 2>&1 || fail "invalid Android provenance: $screenshot"
    recorded=$(jq -r '.sha256 // empty' "$sidecar")
    if [[ -s "$directory/$screenshot" ]]; then
      actual=$(shasum -a 256 "$directory/$screenshot" | awk '{print $1}')
      [[ "$actual" == "$recorded" ]] || fail "Android capture hash mismatch: $screenshot"
    fi
  fi
done

if command -v magick >/dev/null; then
  if [[ -s "$directory/marketing-desktop.png" ]]; then
    [[ "$(magick identify -format '%w' "$directory/marketing-desktop.png" 2>/dev/null)" == "1440" ]] || fail "desktop capture width is not 1440"
  fi
  if [[ -s "$directory/marketing-mobile.png" ]]; then
    [[ "$(magick identify -format '%w' "$directory/marketing-mobile.png" 2>/dev/null)" == "390" ]] || fail "mobile capture width is not 390"
  fi
fi

accepted_commit=$(jq -r '.acceptedCommit // empty' "$manifest" 2>/dev/null)
if [[ "$accepted_commit" =~ ^[0-9a-f]{40}$ ]]; then
  source_commits=()
  [[ -s "$web_provenance" ]] && source_commits+=("$(jq -r '.sourceCommit // empty' "$web_provenance")")
  for screenshot in "${android[@]}"; do
    sidecar="$directory/${screenshot%.png}.provenance.json"
    [[ -s "$sidecar" ]] && source_commits+=("$(jq -r '.sourceCommit // empty' "$sidecar")")
  done
  for source_commit in "${source_commits[@]}"; do
    if [[ ! "$source_commit" =~ ^[0-9a-f]{40}$ ]] || ! git merge-base --is-ancestor "$source_commit" "$accepted_commit" 2>/dev/null; then
      fail "capture source is not an ancestor of the accepted commit: ${source_commit:-missing}"
    fi
  done
else
  fail "accepted commit is unavailable for screenshot provenance"
fi

if [[ ${#failures[@]} -gt 0 ]]; then
  echo "SCREENSHOT EVIDENCE NOT READY (${#failures[@]} blockers)"
  printf '  - %s\n' "${failures[@]}"
  exit 1
fi

echo "SCREENSHOT EVIDENCE READY: 12 real captures, hashes, provenance and dimensions passed."
