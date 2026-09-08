#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

final_dir=submission/video/final
provenance="$final_dir/media-provenance-v4.json"
master="$final_dir/ico-demo-v4-1080p.mp4"
narration="$final_dir/ico-narration-v4.wav"
srt="$final_dir/ico-demo-v4.en.srt"
vtt="$final_dir/ico-demo-v4.en.vtt"
thumbnail="$final_dir/ico-youtube-thumbnail.png"
build_script="scripts/build-video-v4.sh"
failures=()

fail() { failures+=("$1"); }
need_file() { [[ -s "$1" ]] || fail "missing or empty: $1"; }

for command in jq ffprobe magick rg shasum; do
  command -v "$command" >/dev/null 2>&1 || fail "required command is unavailable: $command"
done
for file in "$provenance" "$master" "$narration" "$srt" "$vtt" "$thumbnail" "$build_script"; do
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
  if ! awk -v value="$duration" 'BEGIN { exit !(value >= 120 && value < 240) }'; then
    fail "master duration must be at least 2:00 and below 4:00: ${duration:-unreadable}"
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
  rg -qi 'closes uncertainty without surveillance' "$srt" || fail "SRT omits the closing line"
fi
if [[ -s "$vtt" ]]; then
  head -n 1 "$vtt" | rg -q '^WEBVTT' || fail "VTT header is missing"
  rg -qi 'closes uncertainty without surveillance' "$vtt" || fail "VTT omits the closing line"
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

  music_path=$(jq -r '.music.path // empty' "$provenance")
  music_hash=$(jq -r '.music.sha256 // empty' "$provenance")
  music_provider=$(jq -r '.music.provider // empty' "$provenance")
  if [[ -s "$music_path" ]]; then
    actual_music=$(shasum -a 256 "$music_path" | awk '{print $1}')
    [[ "$actual_music" == "$music_hash" ]] || fail "music hash does not match provenance"
  else
    fail "original score is missing"
  fi
  [[ "$music_provider" == "Project-authored procedural synthesis" ]] || \
    fail "music provenance does not identify the original project score"

  narration_provider=$(jq -r '.narration.provider // empty' "$provenance")
  narration_engine=$(jq -r '.narration.engine // empty' "$provenance")
  narration_voice=$(jq -r '.narration.voice // empty' "$provenance")
  narration_job_count=$(jq -r '.narration.acceptedJobIds | length' "$provenance" 2>/dev/null)
  [[ "$narration_provider" == "Higgsfield Qwen Audio 3.0 TTS Flash" ]] || \
    fail "narration provenance does not identify Higgsfield Qwen Audio"
  [[ "$narration_engine" == "qwen_audio_tts" ]] || fail "narration engine is not qwen_audio_tts"
  [[ "$narration_voice" == "Marcus" ]] || fail "narration voice is not the accepted Marcus preset"
  [[ "$narration_job_count" -eq 15 ]] || fail "narration does not record all 15 accepted provider jobs"

  jq -e '.productCaptures | type == "array" and length >= 3 and all(.[]; .path and .sha256)' \
    "$provenance" >/dev/null 2>&1 || fail "provenance does not record the live product captures"
  while IFS=$'\t' read -r capture_path capture_hash; do
    if [[ -s "$capture_path" ]]; then
      actual_capture=$(shasum -a 256 "$capture_path" | awk '{print $1}')
      [[ "$actual_capture" == "$capture_hash" ]] || fail "capture hash does not match provenance: $capture_path"
    else
      fail "recorded product capture is missing: $capture_path"
    fi
  done < <(jq -r '.productCaptures[]? | [.path, .sha256] | @tsv' "$provenance")
  jq -e '(.picture.generatedCharacterFootageUsed == false) and (.picture.stockFootageUsed == false) and (.picture.croppedProductUi == false)' \
    "$provenance" >/dev/null 2>&1 || fail "the replacement cut must contain no generated character footage or unrecorded stock footage"

  for caption in srt vtt; do
    caption_path=$(jq -r --arg key "$caption" '.captions[$key] // empty' "$provenance")
    caption_hash=$(jq -r --arg key "$caption" '.captions[($key + "Sha256")] // empty' "$provenance")
    if [[ -s "$caption_path" ]]; then
      actual_caption=$(shasum -a 256 "$caption_path" | awk '{print $1}')
      [[ "$actual_caption" == "$caption_hash" ]] || fail "$caption hash does not match provenance"
    else
      fail "$caption path in provenance is missing or unreadable"
    fi
  done

  jq -e '.publication.platform == "YouTube" and .publication.videoId == "hDcBwr9dFsY" and .publication.visibility == "PUBLIC" and .publication.timedEnglishCaptionsPublished == true and .publication.copyrightCheck == "NO_ISSUES_FOUND" and .publication.communityGuidelinesCheck == "NO_ISSUES_FOUND"' \
    "$provenance" >/dev/null 2>&1 || fail "published YouTube evidence is incomplete"
fi

if [[ ${#failures[@]} -gt 0 ]]; then
  echo "VIDEO PACKAGE NOT READY (${#failures[@]} blockers)"
  printf '  - %s\n' "${failures[@]}"
  exit 1
fi

echo "VIDEO PACKAGE READY: published master, Marcus narration, captions, thumbnail, source build and provenance passed."
