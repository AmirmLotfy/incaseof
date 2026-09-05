#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

final_dir=submission/video/final
provenance="$final_dir/media-provenance.json"
master="$final_dir/ico-demo-master-1080p.mp4"
narration="$final_dir/ico-narration.wav"
srt="$final_dir/ico-demo.en.srt"
vtt="$final_dir/ico-demo.en.vtt"
thumbnail="$final_dir/ico-youtube-thumbnail.png"
failures=()

fail() { failures+=("$1"); }
need_file() { [[ -s "$1" ]] || fail "missing or empty: $1"; }

for command in jq ffprobe magick rg shasum; do
  command -v "$command" >/dev/null 2>&1 || fail "required command is unavailable: $command"
done
for file in "$provenance" "$master" "$narration" "$srt" "$vtt" "$thumbnail"; do
  need_file "$file"
done

if [[ -s "$provenance" ]] && ! jq -e '.status == "FINAL"' "$provenance" >/dev/null 2>&1; then
  fail "media provenance status is not FINAL"
fi

if [[ -s "$master" ]] && command -v ffprobe >/dev/null; then
  dimensions=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height \
    -of csv=s=x:p=0 "$master" 2>/dev/null)
  [[ "$dimensions" == "1920x1080" ]] || fail "master is not 1920x1080: ${dimensions:-unreadable}"
  duration=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$master" 2>/dev/null)
  if ! awk -v value="$duration" 'BEGIN { exit !(value >= 240 && value < 300) }'; then
    fail "master duration must be at least 4:00 and below 5:00: ${duration:-unreadable}"
  fi
  audio_streams=$(ffprobe -v error -select_streams a -show_entries stream=index -of csv=p=0 "$master" 2>/dev/null | wc -l | tr -d ' ')
  [[ "$audio_streams" -ge 1 ]] || fail "master has no audio stream"
fi

if [[ -s "$narration" ]] && command -v ffprobe >/dev/null; then
  narration_format=$(ffprobe -v error -show_entries format=format_name -of default=nw=1:nk=1 "$narration" 2>/dev/null)
  [[ "$narration_format" == *wav* ]] || fail "narration is not a WAV file"
fi

if [[ -s "$thumbnail" ]] && command -v magick >/dev/null; then
  thumbnail_dimensions=$(magick identify -format '%wx%h' "$thumbnail" 2>/dev/null)
  [[ "$thumbnail_dimensions" == "1280x720" ]] || fail "thumbnail is not 1280x720"
fi

if [[ -s "$srt" ]]; then
  rg -q '^1$' "$srt" || fail "SRT does not begin with cue 1"
  rg -qi 'Someone notices' "$srt" || fail "SRT omits the closing line"
fi
if [[ -s "$vtt" ]]; then
  head -n 1 "$vtt" | rg -q '^WEBVTT' || fail "VTT header is missing"
  rg -qi 'Someone notices' "$vtt" || fail "VTT omits the closing line"
fi

if [[ -s "$provenance" ]]; then
  accepted_commit=$(jq -r '.acceptedCommit // empty' "$provenance")
  [[ "$accepted_commit" =~ ^[0-9a-f]{40}$ ]] || fail "provenance acceptedCommit is missing"
  for pair in master narration thumbnail; do
    path=$(jq -r --arg key "$pair" '.[$key].path // empty' "$provenance")
    recorded=$(jq -r --arg key "$pair" '.[$key].sha256 // empty' "$provenance")
    if [[ -s "$path" ]]; then
      actual=$(shasum -a 256 "$path" | awk '{print $1}')
      [[ "$actual" == "$recorded" ]] || fail "$pair hash does not match provenance"
    else
      fail "$pair path in provenance is missing or unreadable"
    fi
  done

  timeline=$(jq -r '.timeline.path // empty' "$provenance")
  timeline_hash=$(jq -r '.timeline.sha256 // empty' "$provenance")
  if [[ -s "$timeline" ]]; then
    actual_timeline=$(shasum -a 256 "$timeline" | awk '{print $1}')
    [[ "$actual_timeline" == "$timeline_hash" ]] || fail "timeline hash does not match provenance"
  else
    fail "editable timeline export is missing"
  fi
  jq -e '.productCaptures | type == "array" and length >= 12 and all(.[]; .path and .sha256)' \
    "$provenance" >/dev/null 2>&1 || fail "provenance does not record all 12 product captures"
  while IFS=$'\t' read -r capture_path capture_hash; do
    if [[ -s "$capture_path" ]]; then
      actual_capture=$(shasum -a 256 "$capture_path" | awk '{print $1}')
      [[ "$actual_capture" == "$capture_hash" ]] || fail "capture hash does not match provenance: $capture_path"
    else
      fail "recorded product capture is missing: $capture_path"
    fi
  done < <(jq -r '.productCaptures[]? | [.path, .sha256] | @tsv' "$provenance")
  jq -e '.generatedAssets | type == "array" and all(.[]; .localId and .prompt and .model and .jobId and .resultId and (.chargedCredits | type == "number") and .sha256 and .rightsNotes)' \
    "$provenance" >/dev/null 2>&1 || fail "a generated asset lacks provider, cost, hash or rights evidence"
fi

if [[ ${#failures[@]} -gt 0 ]]; then
  echo "VIDEO PACKAGE NOT READY (${#failures[@]} blockers)"
  printf '  - %s\n' "${failures[@]}"
  exit 1
fi

echo "VIDEO PACKAGE READY: master, audio, captions, thumbnail, timeline and provenance passed."
