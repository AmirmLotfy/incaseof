#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

manifest=submission/release-evidence.json
mode="${ICO_PROJECT_IMAGE_MODE:-final}"
if [[ "$mode" != "final" && "$mode" != "review" ]]; then
  echo "ICO_PROJECT_IMAGE_MODE must be final or review." >&2
  exit 2
fi
if [[ ! -f "$manifest" ]]; then
  echo "Missing $manifest." >&2
  exit 1
fi
if ! jq -e '
  (.liveDeterministicDrill.terminalState == "RESOLVED") and
  ([.urls.marketing, .urls.demo, .urls.canonicalApi] |
    all(type == "string" and startswith("https://")))
' "$manifest" >/dev/null; then
  echo "Resolved Drill and canonical URL evidence must pass before composing project art." >&2
  exit 1
fi
if [[ "$mode" == "final" ]]; then
  jq -e '.canary.runtimeReadyForRequest == true' "$manifest" >/dev/null || {
    echo "Final project art requires a successful AgentCore runtime canary." >&2
    exit 1
  }
else
  jq -e '.artifacts.webCaptureMode == "REHEARSAL_CANONICAL_DETERMINISTIC_FALLBACK"' "$manifest" >/dev/null || {
    echo "Review art requires the canonical deterministic-fallback capture record." >&2
    exit 1
  }
fi

for key in marketing demo canonicalApi; do
  url=$(jq -r --arg key "$key" '.urls[$key]' "$manifest")
  if ! curl --silent --show-error --fail --location --max-time 20 "$url" >/dev/null; then
    echo "Recorded live URL is not reachable: $key ($url)" >&2
    exit 1
  fi
done

sources=(
  submission/screenshots/audit-timeline.png
  submission/screenshots/web-plan-preview.png
  submission/screenshots/android-drill.png
  submission/screenshots/responder-resolved.png
)
for source in "${sources[@]}"; do
  if [[ ! -f "$source" ]]; then
    echo "Missing real deployed capture: $source" >&2
    echo "Final Devpost art is not generated from placeholders or fabricated UI." >&2
    exit 1
  fi
  dimensions=$(magick identify -format '%w %h' "$source")
  read -r width height <<<"$dimensions"
  if [[ "$width" -lt 720 || "$height" -lt 720 ]]; then
    echo "Capture is too small for the final project image: $source (${width}x${height})" >&2
    exit 1
  fi
done

mkdir -p submission/devpost
work=$(mktemp -d /tmp/ico-devpost.XXXXXX)
trap 'rm -rf "$work"' EXIT

for index in 0 1 2 3; do
  magick "${sources[$index]}" -auto-orient -resize '780x760^' -gravity center \
    -extent 780x760 -bordercolor '#C9CEC9' -border 2 "$work/$index.png"
done

magick -size 1800x1200 xc:'#F6F5F0' \
  \( apps/marketing/public/images/ico-logo.png -resize 88x88 \) -geometry +100+54 -composite \
  -fill '#171A18' -font Arial-Bold -pointsize 76 -draw "text 214,120 'In Case Of — ICO'" \
  -fill '#646B66' -font Arial -pointsize 32 -draw "text 214,170 'Someone notices. The plan is monitored, not the person.'" \
  "$work/0.png" -geometry 780x760+100+245 -composite \
  "$work/1.png" -geometry 780x760+920+245 -composite \
  "$work/2.png" -geometry 360x350+130+780 -composite \
  "$work/3.png" -geometry 360x350+1310+780 -composite \
  -fill '#E85B2A' -draw 'circle 900,1065 900,1032' \
  -fill '#171A18' -font Arial-Bold -pointsize 42 -gravity south -annotate +0+42 'GOVERNED AWS AGENTS + EXPLICIT HUMAN RESOLUTION' \
  submission/devpost/in-case-of-project-1800x1200.png

dimensions=$(magick identify -format '%wx%h' submission/devpost/in-case-of-project-1800x1200.png)
[[ "$dimensions" == "1800x1200" ]] || { echo "Unexpected output size: $dimensions" >&2; exit 1; }
echo "Created submission/devpost/in-case-of-project-1800x1200.png from real captures ($mode)."
