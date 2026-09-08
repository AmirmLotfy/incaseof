#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

for command in ffmpeg ffprobe jq magick python3 shasum; do
  command -v "$command" >/dev/null 2>&1 || { echo "Required command is unavailable: $command" >&2; exit 1; }
done

hf="submission/video/higgsfield"
final="submission/video/final"
mkdir -p "$final"
work="$(mktemp -d /tmp/ico-cinematic.XXXXXX)"
trap 'rm -rf "$work"' EXIT

voice_parts=("$hf/voice-01.wav" "$hf/voice-02a.wav" "$hf/voice-02b.wav")
required=(
  "$hf/scene-01-independent-life.png" "$hf/scene-01-independent-life.mp4"
  "$hf/scene-02-responder.png" "$hf/scene-02-responder.mp4"
  "$hf/scene-03-loop-closed.png" "$hf/scene-03-loop-closed.mp4"
  "submission/video/narration-cinematic.txt" "$final/ico-original-score.wav"
  "submission/video/higgsfield/generation-provenance.json"
  "submission/screenshots/marketing-desktop.png" "submission/screenshots/marketing-mobile.png"
  "submission/screenshots/web-plan-preview.png" "submission/screenshots/developer-trace-redacted.png"
  "submission/screenshots/audit-timeline.png" "submission/screenshots/responder-claim.png"
  "submission/screenshots/responder-lease.png" "submission/screenshots/responder-resolved.png"
  "submission/screenshots/android-home.png" "submission/screenshots/android-create.png"
  "submission/screenshots/android-circle.png" "submission/screenshots/android-drill.png"
  "submission/architecture/in-case-of-architecture.png" "apps/marketing/public/images/ico-logo.png"
)
required+=("${voice_parts[@]}")
for path in "${required[@]}"; do
  [[ -s "$path" ]] || { echo "Missing cinematic source: $path" >&2; exit 1; }
done

narration="$final/ico-narration.wav"
score="$final/ico-original-score.wav"
master="$final/ico-demo-master-1080p.mp4"
srt="$final/ico-demo.en.srt"
vtt="$final/ico-demo.en.vtt"
thumbnail="$final/ico-youtube-thumbnail.png"
timeline="$final/timeline.ffconcat"
provenance="$final/media-provenance.json"
accepted_commit="${ICO_VIDEO_ACCEPTED_COMMIT:-$(git rev-parse HEAD)}"
status="${ICO_VIDEO_STATUS:-FINAL}"

ffmpeg -hide_banner -loglevel error -y \
  -i "${voice_parts[0]}" -f lavfi -t 0.65 -i anullsrc=r=48000:cl=stereo \
  -i "${voice_parts[1]}" -f lavfi -t 0.65 -i anullsrc=r=48000:cl=stereo \
  -i "${voice_parts[2]}" \
  -filter_complex '[0:a][1:a][2:a][3:a][4:a]concat=n=5:v=0:a=1,loudnorm=I=-16:TP=-1.5:LRA=9[a]' \
  -map '[a]' -ar 48000 -ac 2 -c:a pcm_s24le "$narration"

python3 - "${voice_parts[@]}" "$hf/voice-01.txt" "$hf/voice-02a.txt" "$hf/voice-02b.txt" "$srt" "$vtt" <<'PY'
from pathlib import Path
import re
import subprocess
import sys

audio_paths = sys.argv[1:4]
text_paths = sys.argv[4:7]
srt_path, vtt_path = sys.argv[7:9]
durations = [float(subprocess.check_output([
    "ffprobe", "-v", "error", "-show_entries", "format=duration",
    "-of", "default=nw=1:nk=1", path,
], text=True).strip()) for path in audio_paths]

def stamp(value, kind):
    hours = int(value // 3600)
    minutes = int((value % 3600) // 60)
    seconds = int(value % 60)
    millis = int(round((value - int(value)) * 1000))
    if millis == 1000:
        seconds += 1
        millis = 0
    separator = "," if kind == "srt" else "."
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}{separator}{millis:03d}"

cues = []
offset = 0.0
for index, (audio_duration, text_path) in enumerate(zip(durations, text_paths)):
    words = Path(text_path).read_text(encoding="utf-8").split()
    chunks, current = [], []
    for word in words:
        current.append(word)
        if len(current) >= 8 and re.search(r'[.!?]["\']?$', word):
            chunks.append(" ".join(current)); current = []
        elif len(current) >= 12:
            chunks.append(" ".join(current)); current = []
    if current:
        chunks.append(" ".join(current))
    weights = [len(chunk.split()) for chunk in chunks]
    cursor = offset
    usable = max(0.1, audio_duration - 0.25)
    for chunk, weight in zip(chunks, weights):
        start = cursor
        cursor += usable * weight / sum(weights)
        cues.append((start, cursor, chunk))
    offset += audio_duration + (0.65 if index < len(durations) - 1 else 0.0)

srt_lines, vtt_lines = [], ["WEBVTT", ""]
for number, (start, end, text) in enumerate(cues, 1):
    srt_lines += [str(number), f"{stamp(start, 'srt')} --> {stamp(end, 'srt')}", text, ""]
    vtt_lines += [f"{stamp(start, 'vtt')} --> {stamp(end, 'vtt')}", text, ""]
Path(srt_path).write_text("\n".join(srt_lines), encoding="utf-8")
Path(vtt_path).write_text("\n".join(vtt_lines), encoding="utf-8")
PY

make_panel() {
  local source="$1" output="$2" label="$3" sub="$4"
  magick -size 1920x1080 xc:'#F4F1EA' \
    -fill '#E85B2A' -draw 'rectangle 0,0 18,1080' \
    -fill '#171A18' -font Arial-Bold -pointsize 38 -gravity northwest -annotate +72+64 "$label" \
    -fill '#646B66' -font Arial -pointsize 25 -annotate +72+112 "$sub" \
    \( "$source" -auto-orient -resize '1660x820>' -bordercolor '#CFD1CC' -border 2 \
       \( +clone -background black -shadow 28x8+0+12 \) +swap -background none -layers merge +repage \) \
    -gravity center -geometry +0+62 -composite "$output"
}

make_split() {
  local left="$1" right="$2" output="$3" label="$4" sub="$5"
  magick -size 1920x1080 xc:'#171A18' \
    -fill '#E85B2A' -draw 'rectangle 0,0 18,1080' \
    -fill '#F4F1EA' -font Arial-Bold -pointsize 38 -gravity northwest -annotate +72+64 "$label" \
    -fill '#AEB5AE' -font Arial -pointsize 25 -annotate +72+112 "$sub" \
    \( "$left" -auto-orient -resize '780x810>' -bordercolor '#535B55' -border 2 \) -gravity west -geometry +115+70 -composite \
    \( "$right" -auto-orient -resize '780x810>' -bordercolor '#535B55' -border 2 \) -gravity east -geometry +115+70 -composite "$output"
}

make_cinematic_card() {
  local source="$1" output="$2" title="$3" sub="$4"
  magick "$source" -auto-orient -resize '1920x1080^' -gravity center -extent 1920x1080 \
    -fill 'rgba(0,0,0,0.52)' -draw 'rectangle 0,0 1920,1080' \
    -fill '#F4F1EA' -font Arial-Bold -pointsize 70 -gravity southwest -annotate +105+190 "$title" \
    -fill '#E85B2A' -font Arial-Bold -pointsize 29 -annotate +108+135 "$sub" "$output"
}

make_phone_on_scene() {
  local scene="$1" phone="$2" output="$3" label="$4" sub="$5"
  magick "$scene" -auto-orient -resize '1920x1080^' -gravity center -extent 1920x1080 -blur 0x18 \
    -fill 'rgba(23,26,24,0.60)' -draw 'rectangle 0,0 1920,1080' \
    -fill '#F4F1EA' -font Arial-Bold -pointsize 40 -gravity northwest -annotate +90+74 "$label" \
    -fill '#C9CEC9' -font Arial -pointsize 25 -annotate +90+122 "$sub" \
    \( "$phone" -auto-orient -resize '470x850>' -bordercolor '#F4F1EA' -border 3 \
       \( +clone -background black -shadow 30x10+0+12 \) +swap -background none -layers merge +repage \) \
    -gravity center -geometry +0+60 -composite "$output"
}

magick submission/screenshots/marketing-desktop.png -crop 1440x1000+0+0 +repage "$work/marketing-desktop.png"
magick submission/screenshots/marketing-mobile.png -crop 390x844+0+0 +repage "$work/marketing-mobile.png"

magick "$hf/scene-01-independent-life.png" -resize '1920x1080^' -gravity center -extent 1920x1080 \
  -fill 'rgba(0,0,0,0.48)' -draw 'rectangle 0,0 1920,1080' \
  \( apps/marketing/public/images/ico-logo.png -resize 118x118 \) -gravity center -geometry +0-190 -composite \
  -fill '#F4F1EA' -font Arial-Bold -pointsize 92 -annotate +0-25 'IN CASE OF' \
  -fill '#F4F1EA' -font Arial -pointsize 42 -annotate +0+70 'Someone notices.' \
  -fill '#E85B2A' -font Arial-Bold -pointsize 26 -annotate +0+150 'A GOVERNED AWS AGENT FOR HUMAN JUDGMENT' "$work/slide-01.png"
make_cinematic_card "$hf/scene-01-independent-life.png" "$work/slide-03.png" 'Most days, nothing happens.' 'MONITOR THE PLAN · NOT THE PERSON'
make_panel "$work/marketing-desktop.png" "$work/slide-04.png" 'ONE QUIET PROMISE' 'An expected Moment can close normally—or start a bounded check.'
make_split "$work/marketing-mobile.png" submission/screenshots/android-home.png "$work/slide-05.png" 'WEB OR ANDROID' 'The same public promise and the same isolated judge flow.'
make_panel submission/screenshots/web-plan-preview.png "$work/slide-06.png" 'REVIEW BEFORE ACTIVATION' 'Language becomes a draft. Policy and consent decide what may run.'
make_split submission/screenshots/android-create.png submission/screenshots/developer-trace-redacted.png "$work/slide-07.png" 'THE MODEL DOES NOT OWN SAFETY' 'The disclosed fallback remains useful without inventing a model trace.'
make_panel submission/architecture/in-case-of-architecture.png "$work/slide-08.png" 'GOVERNED INTERPRETATION · DETERMINISTIC EXECUTION' 'Strands proposes. Cedar authorizes. Durable AWS services own state.'
make_split submission/screenshots/audit-timeline.png submission/screenshots/android-drill.png "$work/slide-09.png" 'THE DEPLOYED DRILL' 'Scheduler · workflow · durable intent · queue · worker · audit.'
make_panel submission/screenshots/responder-claim.png "$work/slide-11.png" 'ONE EXPIRING LINK' 'The responder needs no account and sees only this Alert.'
make_panel submission/screenshots/responder-lease.png "$work/slide-12.png" 'I’M CHECKING IS A LEASE' 'Human action pauses the next rung. It does not invent resolution.'
make_panel submission/screenshots/responder-resolved.png "$work/slide-13.png" 'ONLY AN EXPLICIT OUTCOME CLOSES THE LOOP' 'Acknowledged is never mistaken for resolved.'
make_split submission/screenshots/developer-trace-redacted.png submission/architecture/in-case-of-architecture.png "$work/slide-14.png" 'RETRIES ARE PART OF THE DESIGN' 'Durable identities, last-moment authorization, and reconciliation.'
make_split submission/screenshots/android-circle.png submission/screenshots/android-drill.png "$work/slide-15.png" 'THE SAME PROOF IN THE SIGNED APK' 'Consent, deployed events, and release configuration are visible.'
make_cinematic_card "$hf/scene-03-loop-closed.png" "$work/slide-17.png" 'Uncertainty closes with people.' 'CALM · CONSENTED · AUDITABLE'
magick "$hf/scene-03-loop-closed.png" -resize '1920x1080^' -gravity center -extent 1920x1080 \
  -fill 'rgba(244,241,234,0.78)' -draw 'rectangle 0,0 1920,1080' \
  \( apps/marketing/public/images/ico-logo.png -resize 128x128 \) -gravity center -geometry +0-190 -composite \
  -fill '#171A18' -font Arial-Bold -pointsize 78 -annotate +0-25 'Someone notices.' \
  -fill '#646B66' -font Arial -pointsize 34 -annotate +0+62 'Try the working demo' \
  -fill '#E85B2A' -font Arial-Bold -pointsize 46 -annotate +0+135 'incaof.com/demo' "$work/slide-18.png"

image_segment() {
  local source="$1" seconds="$2" output="$3" direction="${4:-in}"
  local frames
  frames="$(python3 -c "print(round(float('$seconds') * 30))")"
  if [[ "$direction" == "out" ]]; then
    zoom="if(lte(on,1),1.055,max(1.0,zoom-0.00025))"
  else
    zoom="min(zoom+0.00025,1.055)"
  fi
  ffmpeg -hide_banner -loglevel error -y -loop 1 -i "$source" -t "$seconds" \
    -vf "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,zoompan=z='$zoom':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=$frames:s=1920x1080:fps=30,format=yuv420p" \
    -an -c:v libx264 -preset fast -crf 19 -r 30 "$output"
}

clip_segment() {
  local source="$1" seconds="$2" output="$3"
  ffmpeg -hide_banner -loglevel error -y -i "$source" -t "$seconds" \
    -vf 'scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30,format=yuv420p' \
    -an -c:v libx264 -preset fast -crf 18 -r 30 "$output"
}

durations=(6 5 12 16 16 21 21 23 25 5 15 15 15 23 21 5 12 10)
image_segment "$work/slide-01.png" 6 "$work/segment-01.mp4" in
clip_segment "$hf/scene-01-independent-life.mp4" 5 "$work/segment-02.mp4"
image_segment "$work/slide-03.png" 12 "$work/segment-03.mp4" out
image_segment "$work/slide-04.png" 16 "$work/segment-04.mp4" in
image_segment "$work/slide-05.png" 16 "$work/segment-05.mp4" out
image_segment "$work/slide-06.png" 21 "$work/segment-06.mp4" in
image_segment "$work/slide-07.png" 21 "$work/segment-07.mp4" out
image_segment "$work/slide-08.png" 23 "$work/segment-08.mp4" in
image_segment "$work/slide-09.png" 25 "$work/segment-09.mp4" out
clip_segment "$hf/scene-02-responder.mp4" 5 "$work/segment-10.mp4"
image_segment "$work/slide-11.png" 15 "$work/segment-11.mp4" in
image_segment "$work/slide-12.png" 15 "$work/segment-12.mp4" out
image_segment "$work/slide-13.png" 15 "$work/segment-13.mp4" in
image_segment "$work/slide-14.png" 23 "$work/segment-14.mp4" out
image_segment "$work/slide-15.png" 21 "$work/segment-15.mp4" in
clip_segment "$hf/scene-03-loop-closed.mp4" 5 "$work/segment-16.mp4"
image_segment "$work/slide-17.png" 12 "$work/segment-17.mp4" out
image_segment "$work/slide-18.png" 10 "$work/segment-18.mp4" in

{
  echo 'ffconcat version 1.0'
  for index in $(seq -w 1 18); do
    echo "file '$work/segment-$index.mp4'"
  done
} > "$timeline"

ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 -i "$timeline" -i "$narration" -i "$score" \
  -filter_complex '[1:a]apad,atrim=duration=266,asplit=2[voside][vomix];[2:a]apad,atrim=duration=266,loudnorm=I=-27:TP=-3:LRA=8[music];[music][voside]sidechaincompress=threshold=0.025:ratio=7:attack=18:release=650[ducked];[vomix][ducked]amix=inputs=2:weights=1 0.72:normalize=0,alimiter=limit=0.95[a]' \
  -map 0:v -map '[a]' -t 266 -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p \
  -c:a aac -b:a 256k -ar 48000 -movflags +faststart "$master"

magick -size 1280x720 xc:'#171A18' \
  \( "$hf/scene-01-independent-life.png" -resize '760x720^' -gravity center -extent 760x720 \) -gravity east -composite \
  -fill 'rgba(23,26,24,0.35)' -draw 'rectangle 520,0 1280,720' \
  \( submission/screenshots/android-drill.png -resize '300x580>' -bordercolor '#F4F1EA' -border 3 \) -gravity east -geometry +70+0 -composite \
  \( apps/marketing/public/images/ico-logo.png -resize 82x82 \) -gravity northwest -geometry +66+68 -composite \
  -fill '#E85B2A' -font Arial-Bold -pointsize 27 -gravity northwest -annotate +66+190 'IN CASE OF' \
  -fill '#F4F1EA' -font Arial-Bold -pointsize 58 -annotate +66+260 'SOMEONE' -annotate +66+325 'NOTICES.' \
  -fill '#C9CEC9' -font Arial -pointsize 25 -annotate +68+385 'A governed AWS agent' -annotate +68+422 'for human judgment.' \
  -fill '#E85B2A' -font Arial-Bold -pointsize 25 -annotate +68+625 'incaof.com/demo' "$thumbnail"

python3 - "$status" "$accepted_commit" "$master" "$narration" "$score" "$thumbnail" "$timeline" "$provenance" <<'PY'
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess
import sys

status, accepted, master, narration, score, thumbnail, timeline, output = sys.argv[1:]

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def duration(path):
    return float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", path,
    ], text=True).strip())

captures = [
    "marketing-desktop.png", "marketing-mobile.png", "web-plan-preview.png",
    "developer-trace-redacted.png", "audit-timeline.png", "responder-claim.png",
    "responder-lease.png", "responder-resolved.png", "android-home.png",
    "android-create.png", "android-circle.png", "android-drill.png",
]
hf_provenance = json.loads(Path("submission/video/higgsfield/generation-provenance.json").read_text())
payload = {
    "status": status,
    "project": "In Case Of — ICO",
    "producedAt": datetime.now(timezone.utc).isoformat(),
    "acceptedCommit": accepted,
    "master": {"path": master, "sha256": digest(master), "durationSeconds": duration(master), "width": 1920, "height": 1080},
    "narration": {
        "path": narration, "sha256": digest(narration), "provider": "Higgsfield Seed Audio 1.0",
        "voice": "Maeve", "voiceId": "64cf4f1a-61c8-5938-9aea-83d12b2e1d13",
        "providerJobIds": hf_provenance["audioJobIds"],
        "rightsNotes": "Generated from project-authored narration with a Higgsfield preset voice; no voice clone.",
    },
    "captions": {"srt": "submission/video/final/ico-demo.en.srt", "vtt": "submission/video/final/ico-demo.en.vtt", "timingMethod": "Per-provider-chunk waveform duration and word weighting."},
    "thumbnail": {"path": thumbnail, "sha256": digest(thumbnail), "width": 1280, "height": 720},
    "timeline": {"path": timeline, "sha256": digest(timeline), "editor": "FFmpeg H.264 segment timeline"},
    "generatedAssets": hf_provenance["assets"],
    "productCaptures": [{"path": f"submission/screenshots/{name}", "sha256": digest(f"submission/screenshots/{name}")} for name in captures],
    "music": {
        "path": score, "sha256": digest(score), "provider": "Project-authored procedural synthesis",
        "generator": "scripts/generate-original-score.py", "rightsNotes": "Original synthesis; no stock or licensed recording.",
    },
    "notes": [
        "Cinematic assets were generated through Higgsfield and reviewed at full frame before use.",
        "Every product frame comes from the canonical public deployment or signed Android release.",
        "The narration and visible preview disclose the current AgentCore quota block and deterministic fallback.",
        "No private contact endpoint or unredacted signed token is present.",
    ],
}
Path(output).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY

echo "Built cinematic $master ($status)."
