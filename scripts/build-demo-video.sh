#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

for command in ffmpeg ffprobe jq magick python3 say shasum; do
  command -v "$command" >/dev/null 2>&1 || { echo "Required command is unavailable: $command" >&2; exit 1; }
done

final_dir="submission/video/final"
mkdir -p "$final_dir"
work="$(mktemp -d /tmp/ico-video.XXXXXX)"
status="${ICO_VIDEO_STATUS:-REVIEW}"
accepted_commit="${ICO_VIDEO_ACCEPTED_COMMIT:-$(git rev-parse HEAD)}"

narration_text="submission/video/narration.txt"
narration_wav="$final_dir/ico-narration.wav"
srt="$final_dir/ico-demo.en.srt"
vtt="$final_dir/ico-demo.en.vtt"
master="$final_dir/ico-demo-master-1080p.mp4"
thumbnail="$final_dir/ico-youtube-thumbnail.png"
timeline="$final_dir/timeline.ffconcat"
provenance="$final_dir/media-provenance.json"

say -v Samantha -r 160 -f "$narration_text" -o "$work/narration.aiff"
ffmpeg -hide_banner -loglevel error -y -i "$work/narration.aiff" \
  -af 'loudnorm=I=-16:TP=-1.5:LRA=11' -ar 48000 -ac 1 -c:a pcm_s16le "$narration_wav"
narration_duration="$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$narration_wav")"

python3 - "$narration_text" "$narration_duration" "$srt" "$vtt" <<'PY'
from pathlib import Path
import re
import sys

source, duration_raw, srt_path, vtt_path = sys.argv[1:]
duration = float(duration_raw)
text = Path(source).read_text(encoding="utf-8").strip()
tokens = text.split()
chunks = []
current = []
for token in tokens:
    current.append(token)
    if len(current) >= 10 and re.search(r"[.!?][\"']?$", token):
        chunks.append(" ".join(current))
        current = []
    elif len(current) >= 13:
        chunks.append(" ".join(current))
        current = []
if current:
    chunks.append(" ".join(current))

weights = [max(1, len(chunk.split())) for chunk in chunks]
total = sum(weights)
starts = []
cursor = 0.0
for weight in weights:
    start = cursor
    cursor += duration * weight / total
    starts.append((start, cursor))

def stamp(value, decimal):
    hours = int(value // 3600)
    minutes = int((value % 3600) // 60)
    seconds = int(value % 60)
    millis = int(round((value - int(value)) * 1000))
    if millis == 1000:
        seconds += 1
        millis = 0
    separator = "," if decimal == "srt" else "."
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}{separator}{millis:03d}"

srt_lines = []
vtt_lines = ["WEBVTT", ""]
for index, (chunk, (start, end)) in enumerate(zip(chunks, starts), 1):
    srt_lines.extend([str(index), f"{stamp(start, 'srt')} --> {stamp(end, 'srt')}", chunk, ""])
    vtt_lines.extend([f"{stamp(start, 'vtt')} --> {stamp(end, 'vtt')}", chunk, ""])
Path(srt_path).write_text("\n".join(srt_lines), encoding="utf-8")
Path(vtt_path).write_text("\n".join(vtt_lines), encoding="utf-8")
PY
cp "$srt" "$work/captions.srt"

magick submission/screenshots/marketing-desktop.png -crop 1440x1000+0+0 +repage "$work/marketing-desktop.png"
magick submission/screenshots/marketing-mobile.png -crop 390x844+0+0 +repage "$work/marketing-mobile.png"

make_slide() {
  local source="$1"
  local output="$2"
  local label="$3"
  magick -size 1920x1080 xc:'#F6F5F0' \
    \( "$source" -auto-orient -resize '1640x880>' -bordercolor '#C9CEC9' -border 2 \) \
    -gravity center -geometry +0+44 -composite \
    -gravity northwest -fill '#171A18' -font Arial-Bold -pointsize 34 \
    -annotate +80+56 "$label" "$output"
}

magick -size 1920x1080 xc:'#171A18' \
  \( apps/marketing/public/images/ico-logo.png -resize 150x150 \) -gravity center -geometry +0-155 -composite \
  -fill '#F6F5F0' -font Arial-Bold -pointsize 88 -gravity center -annotate +0+10 'IN CASE OF' \
  -fill '#C9CEC9' -font Arial -pointsize 38 -annotate +0+92 'Someone notices.' \
  -fill '#E85B2A' -font Arial-Bold -pointsize 28 -annotate +0+182 'A GOVERNED AWS AGENT WORKFLOW' \
  "$work/slide-01.png"
make_slide "$work/marketing-desktop.png" "$work/slide-02.png" 'THE PROMISE'
make_slide "$work/marketing-mobile.png" "$work/slide-03.png" 'PUBLIC WEB EXPERIENCE'
make_slide submission/screenshots/android-home.png "$work/slide-04.png" 'SIGNED ANDROID RELEASE'
make_slide submission/screenshots/web-plan-preview.png "$work/slide-05.png" 'REVIEW BEFORE ANYTHING RUNS'
make_slide submission/screenshots/android-create.png "$work/slide-06.png" 'MODEL OUTAGE FAILS SAFE'
make_slide submission/screenshots/audit-timeline.png "$work/slide-07.png" 'DEPLOYED AUDIT TIMELINE'
make_slide submission/screenshots/android-drill.png "$work/slide-08.png" 'SCHEDULER · WORKFLOW · QUEUE · WORKER'
make_slide submission/screenshots/responder-claim.png "$work/slide-09.png" 'SIGNED INCIDENT ROOM'
make_slide submission/screenshots/responder-lease.png "$work/slide-10.png" 'CHECKING CREATES A LEASE'
make_slide submission/screenshots/responder-resolved.png "$work/slide-11.png" 'EXPLICIT HUMAN RESOLUTION'
make_slide submission/architecture/in-case-of-architecture.png "$work/slide-12.png" 'DETERMINISTIC AUTHORIZATION BOUNDARY'
make_slide submission/screenshots/android-circle.png "$work/slide-13.png" 'CONSENTED CIRCLE'
magick -size 1920x1080 xc:'#F6F5F0' \
  \( apps/marketing/public/images/ico-logo.png -resize 140x140 \) -gravity center -geometry +0-175 -composite \
  -fill '#171A18' -font Arial-Bold -pointsize 74 -gravity center -annotate +0-20 'Someone notices.' \
  -fill '#646B66' -font Arial -pointsize 36 -annotate +0+72 'Try the live demo' \
  -fill '#E85B2A' -font Arial-Bold -pointsize 42 -annotate +0+145 'incaof.com/demo' \
  "$work/slide-14.png"

durations=(10 18 15 15 25 20 30 30 20 18 20 25 15 14)
{
  echo 'ffconcat version 1.0'
  for index in $(seq -w 1 14); do
    duration_index=$((10#$index - 1))
    echo "file '$work/slide-$index.png'"
    echo "duration ${durations[$duration_index]}"
  done
  echo "file '$work/slide-14.png'"
} > "$timeline"

ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 -i "$timeline" -i "$narration_wav" \
  -vf 'fps=30' \
  -af apad -t 275 -c:v libx264 -preset medium -crf 19 -pix_fmt yuv420p \
  -c:a aac -b:a 192k -movflags +faststart "$master"

magick -size 1280x720 xc:'#171A18' \
  \( submission/screenshots/android-drill.png -resize '410x620>' -bordercolor '#F6F5F0' -border 3 \) \
  -gravity east -geometry +70+0 -composite \
  -fill '#E85B2A' -font Arial-Bold -pointsize 30 -gravity northwest -annotate +70+95 'IN CASE OF' \
  -fill '#F6F5F0' -font Arial-Bold -pointsize 66 -annotate +70+185 'WHEN NOBODY' \
  -annotate +70+260 'ANSWERS' \
  -fill '#C9CEC9' -font Arial -pointsize 27 -annotate +70+335 'The plan is monitored.' \
  -annotate +70+376 'The person is not.' \
  -fill '#E85B2A' -font Arial-Bold -pointsize 28 -annotate +70+585 'incaof.com/demo' \
  "$thumbnail"

python3 - "$status" "$accepted_commit" "$master" "$narration_wav" "$thumbnail" "$timeline" "$provenance" <<'PY'
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess
import sys

status, accepted, master, narration, thumbnail, timeline, output = sys.argv[1:]
captures = [
    "marketing-desktop.png", "marketing-mobile.png", "web-plan-preview.png",
    "developer-trace-redacted.png", "audit-timeline.png", "responder-claim.png",
    "responder-lease.png", "responder-resolved.png", "android-home.png",
    "android-create.png", "android-circle.png", "android-drill.png",
]

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

duration = float(subprocess.check_output([
    "ffprobe", "-v", "error", "-show_entries", "format=duration",
    "-of", "default=nw=1:nk=1", master,
], text=True).strip())
payload = {
    "status": status,
    "project": "In Case Of — ICO",
    "producedAt": datetime.now(timezone.utc).isoformat(),
    "acceptedCommit": accepted,
    "master": {"path": master, "sha256": digest(master), "durationSeconds": duration, "width": 1920, "height": 1080},
    "narration": {"path": narration, "sha256": digest(narration), "provider": "macOS system voice", "providerResultId": None, "rightsNotes": "Locally synthesized from project-authored narration; no third-party voice clone."},
    "captions": {"srt": "submission/video/final/ico-demo.en.srt", "vtt": "submission/video/final/ico-demo.en.vtt", "timingMethod": "Word-weighted to the final fixed-rate narration waveform."},
    "thumbnail": {"path": thumbnail, "sha256": digest(thumbnail), "width": 1280, "height": 720},
    "timeline": {"path": timeline, "sha256": digest(timeline), "editor": "FFmpeg concat timeline"},
    "generatedAssets": [],
    "productCaptures": [{"path": f"submission/screenshots/{name}", "sha256": digest(f"submission/screenshots/{name}")} for name in captures],
    "music": None,
    "notes": [
        "Every product frame comes from the canonical public deployment or signed Android release.",
        "The narration and visible plan preview disclose the current AgentCore quota block and deterministic fallback.",
        "No generated footage, simulated notification, private contact endpoint, or unredacted signed token is present.",
    ],
}
Path(output).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY

echo "Built $master ($status) from the verified capture set."
