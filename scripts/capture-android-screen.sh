#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

usage() {
  echo "Usage: ICO_EXPECT_TEXT='visible text' $0 android-home|android-create|android-circle|android-drill" >&2
}

label="${1:-}"
case "$label" in
  android-home|android-create|android-circle|android-drill) ;;
  *) usage; exit 2 ;;
esac
: "${ICO_EXPECT_TEXT:?Set ICO_EXPECT_TEXT to text that uniquely proves the intended screen is visible}"

for command in jq magick rg shasum; do
  command -v "$command" >/dev/null 2>&1 || { echo "Required command is unavailable: $command" >&2; exit 1; }
done

adb_bin="${ANDROID_HOME:-}/platform-tools/adb"
if [[ ! -x "$adb_bin" && -x "$PWD/.android-sdk/platform-tools/adb" ]]; then
  adb_bin="$PWD/.android-sdk/platform-tools/adb"
fi
[[ -x "$adb_bin" ]] || { echo "adb is unavailable at $adb_bin" >&2; exit 1; }

if [[ -n "${ANDROID_SERIAL:-}" ]]; then
  serial="$ANDROID_SERIAL"
else
  device_count=$("$adb_bin" devices | awk 'NR > 1 && $2 == "device" {count++} END {print count+0}')
  [[ "$device_count" -eq 1 ]] || {
    echo "Connect exactly one Android device, or set ANDROID_SERIAL explicitly." >&2
    exit 1
  }
  serial=$("$adb_bin" devices | awk 'NR > 1 && $2 == "device" {print $1; exit}')
fi

adb=("$adb_bin" -s "$serial")
"${adb[@]}" get-state | rg -q '^device$' || { echo "Android device is not ready." >&2; exit 1; }
"${adb[@]}" shell pm path com.incaof.app | rg -q '^package:' || {
  echo "Signed release package com.incaof.app is not installed." >&2
  exit 1
}

foreground=$("${adb[@]}" shell dumpsys window windows | rg 'mCurrentFocus|mFocusedApp' || true)
rg -q 'com\.incaof\.app' <<<"$foreground" || {
  echo "Bring the signed In Case Of release app to the foreground before capture." >&2
  exit 1
}

"${adb[@]}" shell uiautomator dump /sdcard/ico-submission-ui.xml >/dev/null
ui=$("${adb[@]}" exec-out cat /sdcard/ico-submission-ui.xml)
rg -Fq "$ICO_EXPECT_TEXT" <<<"$ui" || {
  echo "Expected screen text was not visible: $ICO_EXPECT_TEXT" >&2
  exit 1
}
if rg -qi 'localhost|local repository|sample data|fixture' <<<"$ui"; then
  echo "Release capture rejected because local/sample markers are visible." >&2
  exit 1
fi

mkdir -p submission/screenshots
output="submission/screenshots/$label.png"
"${adb[@]}" exec-out screencap -p >"$output"
dimensions=$(magick identify -format '%wx%h' "$output")
image_sha=$(shasum -a 256 "$output" | awk '{print $1}')
serial_sha=$(printf '%s' "$serial" | shasum -a 256 | awk '{print $1}')
model=$("${adb[@]}" shell getprop ro.product.model | tr -d '\r')
sdk=$("${adb[@]}" shell getprop ro.build.version.sdk | tr -d '\r')
qemu=$("${adb[@]}" shell getprop ro.kernel.qemu | tr -d '\r')
version=$("${adb[@]}" shell dumpsys package com.incaof.app | awk -F= '/versionName=/{print $2; exit}' | tr -d '\r')
captured_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
source_commit=$(git rev-parse HEAD)

jq -n \
  --arg filename "$label.png" \
  --arg capturedAt "$captured_at" \
  --arg sourceCommit "$source_commit" \
  --arg deviceSerialSha256 "$serial_sha" \
  --arg model "$model" \
  --arg sdk "$sdk" \
  --arg emulator "$qemu" \
  --arg packageName "com.incaof.app" \
  --arg versionName "$version" \
  --arg expectedText "$ICO_EXPECT_TEXT" \
  --arg dimensions "$dimensions" \
  --arg sha256 "$image_sha" \
  '{
    filename: $filename,
    capturedAt: $capturedAt,
    sourceCommit: $sourceCommit,
    deviceSerialSha256: $deviceSerialSha256,
    device: { model: $model, sdk: ($sdk | tonumber), emulator: ($emulator == "1") },
    app: { packageName: $packageName, versionName: $versionName },
    expectedVisibleText: $expectedText,
    dimensions: $dimensions,
    sha256: $sha256,
    statement: "Captured from the foreground signed release app after a UI text assertion; no image synthesis or fixture substitution."
  }' >"submission/screenshots/$label.provenance.json"

echo "Captured $output ($dimensions, $image_sha)."
