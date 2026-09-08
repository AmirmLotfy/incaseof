#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

for command in ffmpeg ffprobe magick python3 jq shasum; do
  command -v "$command" >/dev/null 2>&1 || { echo "Required command unavailable: $command" >&2; exit 1; }
done

root="submission/video/v4"
voice="$root/voice"
captures="submission/video/remake/captures"
final="submission/video/final"
work="$(mktemp -d /tmp/ico-video-v3.XXXXXX)"
trap 'rm -rf "$work"' EXIT
mkdir -p "$final" "$root/cards"

browser="$captures/live-demo-flow.webm"
android_timeline="$captures/android-timeline.mp4"
android_flow="$captures/android-live-demo.mp4"
score="$final/ico-original-score.wav"
architecture="submission/architecture/in-case-of-architecture.png"
master="$final/ico-demo-v4-1080p.mp4"
vo_master="$final/ico-narration-v4.wav"
srt="$final/ico-demo-v4.en.srt"
vtt="$final/ico-demo-v4.en.vtt"
provenance="$final/media-provenance-v4.json"
thumbnail="$final/ico-youtube-thumbnail.png"
font="Arial"
font_bold="Arial-Bold"

for source in "$browser" "$android_timeline" "$android_flow" "$score" "$architecture" "$thumbnail"; do
  [[ -s "$source" ]] || { echo "Missing V3 source: $source" >&2; exit 1; }
done
for index in $(seq -w 1 15); do
  [[ -s "$voice/take$index.wav" ]] || { echo "Missing narration take: $voice/take$index.wav" >&2; exit 1; }
done

title_state() {
  local output="$1" eyebrow="$2" title="$3" subtitle="$4" accent="$5"
  magick -size 1920x1080 xc:'#F4F1EA' \
    -fill '#111714' -draw 'circle 114,116 114,70' \
    -fill "$accent" -draw 'circle 139,116 139,109' \
    -fill '#5E6761' -font "$font_bold" -pointsize 26 -gravity northwest -annotate +184+82 "$eyebrow" \
    -fill '#111714' -font "$font_bold" -pointsize 108 -annotate +184+250 "$title" \
    -fill '#5E6761' -font "$font" -pointsize 42 -annotate +190+410 "$subtitle" \
    -fill "$accent" -draw 'roundrectangle 184,560 1130,574 7,7' \
    -fill '#111714' -font "$font_bold" -pointsize 28 -annotate +184+650 'IN CASE OF  •  EXPECTED MOMENTS, NOT SURVEILLANCE' \
    "$output"
}

label_overlay() {
  local output="$1" title="$2" subtitle="$3" accent="$4"
  magick -size 1920x1080 xc:none \
    -fill '#111714E8' -draw 'roundrectangle 42,38 990,142 22,22' \
    -fill "$accent" -draw 'roundrectangle 62,58 76,122 7,7' \
    -fill '#FFFFFF' -font "$font_bold" -pointsize 30 -gravity northwest -annotate +100+54 "$title" \
    -fill '#CDD3CF' -font "$font" -pointsize 22 -annotate +100+96 "$subtitle" \
    "$output"
}

browser_beat() {
  local start="$1" source_duration="$2" target_duration="$3" output="$4" title="$5" subtitle="$6" accent="${7:-#EE5B2B}"
  local overlay="$work/$(basename "$output" .mp4)-label.png"
  local ratio
  ratio="$(python3 -c "print(float('$target_duration')/float('$source_duration'))")"
  label_overlay "$overlay" "$title" "$subtitle" "$accent"
  ffmpeg -hide_banner -loglevel error -y -ss "$start" -i "$browser" -loop 1 -i "$overlay" \
    -filter_complex "[0:v]trim=duration=$source_duration,setpts=$ratio*(PTS-STARTPTS),fps=30,scale=1920:1080:flags=lanczos,setsar=1[screen];[1:v]fps=30[overlay];[screen][overlay]overlay=0:0:shortest=1,trim=duration=$target_duration,format=yuv420p[v]" \
    -map '[v]' -an -t "$target_duration" -c:v libx264 -preset veryfast -crf 18 -r 30 "$output"
}

phone_beat() {
  local source="$1" start="$2" source_duration="$3" target_duration="$4" output="$5" title="$6" subtitle="$7"
  local panel="$work/$(basename "$output" .mp4)-panel.png"
  local ratio
  ratio="$(python3 -c "print(float('$target_duration')/float('$source_duration'))")"
  magick -size 1920x1080 xc:'#F4F1EA' \
    -fill '#EE5B2B' -draw 'roundrectangle 108,164 124,842 8,8' \
    -fill '#6A736D' -font "$font_bold" -pointsize 26 -gravity northwest -annotate +164+170 'SIGNED ANDROID CLIENT' \
    -fill '#111714' -font "$font_bold" -pointsize 62 -annotate +164+244 "$title" \
    -fill '#5E6761' -font "$font" -pointsize 32 -annotate +168+352 "$subtitle" \
    -fill '#DDE7E2' -draw 'roundrectangle 164,550 1080,720 26,26' \
    -fill '#225F50' -font "$font_bold" -pointsize 28 -annotate +210+590 'REAL UI  •  DEPLOYED API  •  SAME AUDIT TRAIL' \
    -fill '#5E6761' -font "$font" -pointsize 24 -annotate +210+648 'No simulated app screens. No hidden demo logic.' \
    "$panel"
  ffmpeg -hide_banner -loglevel error -y -ss "$start" -i "$source" -loop 1 -i "$panel" \
    -filter_complex "[0:v]trim=duration=$source_duration,setpts=$ratio*(PTS-STARTPTS),fps=30,scale=-2:946:flags=lanczos[phone];[1:v]fps=30[base];[base][phone]overlay=1370:67:shortest=1,trim=duration=$target_duration,format=yuv420p[v]" \
    -map '[v]' -an -t "$target_duration" -c:v libx264 -preset veryfast -crf 18 -r 30 "$output"
}

still_sequence() {
  local output="$1" duration="$2"
  shift 2
  local count="$#" each list="$work/$(basename "$output" .mp4)-stills.txt"
  each="$(python3 -c "print(float('$duration')/int('$count'))")"
  : > "$list"
  for image in "$@"; do
    if [[ "$image" = /* ]]; then image_path="$image"; else image_path="$PWD/$image"; fi
    printf "file '%s'\nduration %s\n" "$image_path" "$each" >> "$list"
  done
  image="${!#}"
  if [[ "$image" = /* ]]; then image_path="$image"; else image_path="$PWD/$image"; fi
  printf "file '%s'\n" "$image_path" >> "$list"
  ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 -i "$list" -vf "fps=30,scale=1920:1080:flags=lanczos,format=yuv420p" \
    -an -t "$duration" -c:v libx264 -preset veryfast -crf 18 -r 30 "$output"
}

# Beat 01: three quick story cards, matching the real product's visual language.
title_state "$root/cards/01-missed.png" 'AN EXPECTED MOMENT' 'A missed check-in.' "It may be ordinary. It may be nothing." '#EE5B2B'
title_state "$root/cards/02-unanswered.png" 'WHEN NOBODY ANSWERS' 'Uncertainty grows.' "People need a clear next step, not constant tracking." '#F0B54A'
title_state "$root/cards/03-notices.png" 'THE PROMISE' 'Someone notices.' "Only the people Mona chose. Only when the plan says so." '#55C7AE'
still_sequence "$work/beat-01.mp4" 9.6 "$root/cards/01-missed.png" "$root/cards/02-unanswered.png" "$root/cards/03-notices.png"

# Beats 02–10: one coherent, full-frame real judge journey. No cropping or zooming.
browser_beat 0.0 14.15 9.0 "$work/beat-02.mp4" 'PUBLIC JUDGE PATH' 'Landing page → isolated live demo'
browser_beat 14.15 11.63 9.0 "$work/beat-03.mp4" 'LANGUAGE → LITERAL PLAN' 'Ordinary words become a reviewable preview' '#55C7AE'
browser_beat 25.78 8.72 9.0 "$work/beat-04.mp4" 'REVIEW BEFORE ANYTHING RUNS' 'Typed validation, consent, channels, and policy' '#55C7AE'
browser_beat 34.50 8.00 9.0 "$work/beat-05.mp4" 'EXPLICIT ACTIVATION' 'Save draft → Test this plan'
browser_beat 42.50 56.50 9.0 "$work/beat-06.mp4" 'ACCELERATED JUDGE CLOCK' 'Due moment → deterministic workflow → audit trail' '#F0B54A'
browser_beat 99.00 50.50 9.0 "$work/beat-07.mp4" 'APPROVED LADDER ADVANCES' 'Consent rechecked • one durable delivery outcome' '#F0B54A'
browser_beat 149.50 8.22 9.0 "$work/beat-08.mp4" 'SCOPED RESPONDER ROOM' 'One alert • short-lived access • minimal disclosure' '#55C7AE'
browser_beat 157.72 8.64 9.0 "$work/beat-09.mp4" "I'M CHECKING ≠ RESOLVED" 'A checking lease pauses escalation while the Alert stays open' '#55C7AE'
browser_beat 166.36 6.08 9.0 "$work/beat-10.mp4" 'A HUMAN CLOSES THE LOOP' 'Explicit outcome → resolved → retries stop' '#55C7AE'

# Beats 11–12: real Android motion in a readable editorial frame.
phone_beat "$android_flow" 0.0 18.0 9.0 "$work/beat-11.mp4" 'Plan controls' 'Review, activate, and run the same synthetic drill.'
phone_beat "$android_timeline" 0.0 11.27 9.0 "$work/beat-12.mp4" 'Deployed timeline' 'The subject sees each recorded transition on Android.'

# Beat 13: reliability proof revealed in three compact states.
title_state "$root/cards/13-write.png" '01  •  AT ACTIVATION' 'Plan + outbox.' 'Saved together in one DynamoDB transaction.' '#55C7AE'
title_state "$root/cards/14-deliver.png" '02  •  AT DELIVERY' 'One durable outcome.' 'SQS retries only after consent and authorization are rechecked.' '#EE5B2B'
title_state "$root/cards/15-reconcile.png" '03  •  AFTER A TIMEOUT' 'Reconcile first.' 'An unknown provider outcome is never blindly resent.' '#F0B54A'
still_sequence "$work/beat-13.mp4" 9.6 "$root/cards/13-write.png" "$root/cards/14-deliver.png" "$root/cards/15-reconcile.png"

# Beat 14: a legible 16:9 architecture reveal built from the same two-lane model as the submission diagram.
magick -size 1920x1080 xc:'#F4F1EA' \
  -fill '#6A736D' -font "$font_bold" -pointsize 24 -gravity northwest -annotate +100+74 'GOVERNED AI. DETERMINISTIC SAFETY.' \
  -fill '#111714' -font "$font_bold" -pointsize 62 -annotate +100+118 'The model proposes. Software decides and acts.' \
  -fill '#DDEDE8' -draw 'roundrectangle 100,240 886,760 34,34' \
  -fill '#2D7665' -font "$font_bold" -pointsize 24 -annotate +148+280 'AI MAY PROPOSE' \
  -fill '#111714' -font "$font_bold" -pointsize 34 -annotate +148+340 'Language  →  Strands + Nova' \
  -fill '#111714' -font "$font_bold" -pointsize 34 -annotate +148+440 'Cedar policy  →  typed preview' \
  -fill '#2D7665' -font "$font_bold" -pointsize 24 -annotate +148+610 'NO WRITES  •  NO SCHEDULES  •  NO CONTACT' \
  -fill '#FBE8DE' -draw 'roundrectangle 1034,240 1820,760 34,34' \
  -fill '#EE5B2B' -font "$font_bold" -pointsize 24 -annotate +1082+280 'SOFTWARE MAY ACT' \
  -fill '#111714' -font "$font_bold" -pointsize 34 -annotate +1082+340 'Transaction  →  Scheduler' \
  -fill '#111714' -font "$font_bold" -pointsize 34 -annotate +1082+440 'Step Functions  →  SQS worker' \
  -fill '#EE5B2B' -font "$font_bold" -pointsize 24 -annotate +1082+610 'AUTHORIZED  •  IDEMPOTENT  •  AUDITED' \
  -fill '#111714' -draw 'roundrectangle 100,824 1820,980 28,28' \
  -fill '#F4F1EA' -font "$font_bold" -pointsize 30 -annotate +148+860 'RESPONDER CLAIM  →  CHECKING LEASE  →  EXPLICIT OUTCOME  →  RESOLVED' \
  -fill '#AAB3AD' -font "$font" -pointsize 22 -annotate +148+920 'Amazon Cognito • API Gateway • Lambda • CloudWatch • X-Ray • KMS' \
  "$root/cards/16-architecture.png"
magick "$root/cards/16-architecture.png" \
  -fill '#2D7665' -draw 'roundrectangle 124,708 862,742 17,17' \
  "$root/cards/17-architecture-ai.png"
magick "$root/cards/16-architecture.png" \
  -fill '#EE5B2B' -draw 'roundrectangle 1058,708 1796,742 17,17' \
  "$root/cards/18-architecture-action.png"
still_sequence "$work/beat-14.mp4" 9.0 "$root/cards/16-architecture.png" "$root/cards/17-architecture-ai.png" "$root/cards/18-architecture-action.png"

# Beat 15: final product proof, then one clear action.
browser_beat 166.30 6.14 4.3 "$work/beat-15a.mp4" 'THE ALERT IS CLOSED' 'The deployed audit trail keeps the proof' '#55C7AE'
title_state "$root/cards/19-close.png" 'TRY THE SYNTHETIC JUDGE DRILL' 'Someone notices.' 'incaof.com/demo   •   github.com/AmirmLotfy/incaseof' '#EE5B2B'
still_sequence "$work/beat-15b.mp4" 4.7 "$root/cards/19-close.png"
printf "file '%s'\nfile '%s'\n" "$work/beat-15a.mp4" "$work/beat-15b.mp4" > "$work/beat-15.txt"
ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 -i "$work/beat-15.txt" -an -c copy "$work/beat-15.mp4"

durations=(9.6 9 9 9 9 9 9 9 9 9 9 9 9.6 9 9)
: > "$work/visual-list.txt"
for index in $(seq -w 1 15); do printf "file '%s'\n" "$work/beat-$index.mp4" >> "$work/visual-list.txt"; done
ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 -i "$work/visual-list.txt" \
  -an -c copy -movflags +faststart "$work/visual.mp4"

# Place each accepted take at the start of its visual beat without stretching it.
audio_inputs=()
for index in $(seq -w 1 15); do audio_inputs+=(-i "$voice/take$index.wav"); done
audio_filter=""
for zero_index in $(seq 0 14); do
  duration="${durations[$zero_index]}"
  audio_filter+="[$zero_index:a]apad,atrim=duration=$duration,asetpts=PTS-STARTPTS[a$zero_index];"
done
for zero_index in $(seq 0 14); do audio_filter+="[a$zero_index]"; done
audio_filter+="concat=n=15:v=0:a=1,loudnorm=I=-16:TP=-1.5:LRA=8[vo]"
ffmpeg -hide_banner -loglevel error -y "${audio_inputs[@]}" -filter_complex "$audio_filter" \
  -map '[vo]' -ar 48000 -ac 2 -c:a pcm_s24le "$vo_master"

visual_duration="$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$work/visual.mp4")"
fade_out="$(python3 -c "print(max(0,float('$visual_duration')-3))")"
ffmpeg -hide_banner -loglevel error -y -i "$work/visual.mp4" -i "$vo_master" -i "$score" \
  -filter_complex "[1:a]asplit=2[voside][vomix];[2:a]atrim=0:$visual_duration,afade=t=in:st=0:d=1.5,afade=t=out:st=$fade_out:d=3,loudnorm=I=-29:TP=-4:LRA=7[music];[music][voside]sidechaincompress=threshold=0.025:ratio=8:attack=12:release=500[ducked];[vomix][ducked]amix=inputs=2:weights=1 0.82:normalize=0,alimiter=limit=0.94[a]" \
  -map 0:v -map '[a]' -t "$visual_duration" -c:v copy -c:a aac -b:a 256k -ar 48000 -movflags +faststart "$master"

python3 - "$voice" "submission/video/narration-v4-lines.txt" "$srt" "$vtt" "$master" "$vo_master" "$score" "$architecture" "$thumbnail" "$provenance" <<'PY'
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json, subprocess, sys

voice_dir, lines_path, srt_path, vtt_path, master, narration, score, architecture, thumbnail, output = map(Path, sys.argv[1:])
beat_durations = [9.6] + [9.0] * 11 + [9.6, 9.0, 9.0]
lines = [line.split('|', 1)[1] for line in lines_path.read_text().splitlines() if line.strip()]
audio = [voice_dir / f'take{i:02d}.wav' for i in range(1, 16)]

def duration(path):
    return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(path)], text=True).strip())
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def stamp(value, comma):
    millis = int(round(value * 1000)); hours, rem = divmod(millis, 3600000); minutes, rem = divmod(rem, 60000); seconds, ms = divmod(rem, 1000)
    return f'{hours:02d}:{minutes:02d}:{seconds:02d}{"," if comma else "."}{ms:03d}'

offset = 0.0; cues = []
for text, path, beat in zip(lines, audio, beat_durations):
    end = min(offset + duration(path), offset + beat - 0.05)
    cues.append((offset, end, text)); offset += beat
srt=[]; vtt=['WEBVTT','']
for i,(start,end,text) in enumerate(cues,1):
    srt += [str(i), f'{stamp(start, True)} --> {stamp(end, True)}', text, '']
    vtt += [f'{stamp(start, False)} --> {stamp(end, False)}', text, '']
srt_path.write_text('\n'.join(srt), encoding='utf-8'); vtt_path.write_text('\n'.join(vtt), encoding='utf-8')

job_ids = [
 'd1526d95-aaae-49d3-903b-8bdf2ca8249d','626aee2e-17c8-4159-8bcf-fabe03626e02','d60edc4a-f9c1-4280-ab66-4e694ca067f5',
 'caf16e8e-ddae-4792-8e2c-6a537520f20c','63befa3a-4872-4d37-9a1a-50c747a2b6cc','36addf76-4e5a-4e70-a2d3-d6aed0c8a714',
 'a3c40479-4f58-4a7a-abd4-a860f70cc613','93c45a43-3d2a-4ace-aafa-c0b63081bddc','9ea8eb0a-c546-487b-a2f2-16aa06587f88',
 '6f845752-5f9a-42c8-bdd9-b8a4ac3cc83c','1fd6d749-56e9-4738-bf53-8d2a1cbb780f','22170788-ad31-43c9-8423-02afc57ee2f7',
 'bde14d03-a6c5-48dc-af3d-a1a2840de261','1d50f1ad-4644-4dc0-82c2-be1008d176a3','fc029561-9d24-4cbb-81ec-d7970f640085'
]
captures=[Path('submission/video/remake/captures/live-demo-flow.webm'),Path('submission/video/remake/captures/android-timeline.mp4'),Path('submission/video/remake/captures/android-live-demo.mp4')]
payload={
 'status':'FINAL','project':'In Case Of — ICO','producedAt':datetime.now(timezone.utc).isoformat(),
 'acceptedCommit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
 'master':{'path':str(master),'sha256':digest(master),'durationSeconds':duration(master),'width':1920,'height':1080,'fps':30},
 'narration':{'path':str(narration),'sha256':digest(narration),'provider':'Higgsfield Qwen Audio 3.0 TTS Flash','engine':'qwen_audio_tts','voice':'Marcus','voiceId':'6f98d3dd-324f-4845-8c28-c1d1647a06cd','gender':'male','acceptedJobIds':job_ids,'rightsNotes':'Project-authored copy performed by the built-in Marcus male preset with controlled conversational delivery; no cloning or imitation.'},
 'picture':{'liveBrowserCapture':str(captures[0]),'androidCaptures':[str(captures[1]),str(captures[2])],'generatedCharacterFootageUsed':False,'stockFootageUsed':False,'croppedProductUi':False,'statement':'The cut uses the full real public judge capture, real Android emulator motion, and project-authored editorial graphics.'},
 'productCaptures':[{'path':str(p),'sha256':digest(p)} for p in captures],
 'architecture':{'path':str(architecture),'sha256':digest(architecture)},
 'thumbnail':{'path':str(thumbnail),'sha256':digest(thumbnail),'width':1280,'height':720},
 'music':{'path':str(score),'sha256':digest(score),'provider':'Project-authored procedural synthesis','rightsNotes':'Original score with no third-party recording or sample.'},
 'captions':{'srt':str(srt_path),'srtSha256':digest(srt_path),'vtt':str(vtt_path),'vttSha256':digest(vtt_path)},
 'editorial':{'beatCount':15,'maximumBeatSeconds':9.6,'longWaits':'visibly accelerated','transitions':'straight cuts','sourceMethod':'STAY-inspired proof-first product journey'},
 'publication':{'platform':'YouTube','url':'https://youtu.be/hDcBwr9dFsY','videoId':'hDcBwr9dFsY','visibility':'PUBLIC','publishedAt':'2026-09-08','timedEnglishCaptionsPublished':True,'captionCueCount':15,'customThumbnailUploaded':True,'copyrightCheck':'NO_ISSUES_FOUND','communityGuidelinesCheck':'NO_ISSUES_FOUND'}
}
output.write_text(json.dumps(payload,indent=2)+'\n')
PY

echo "Built $master"
ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height,r_frame_rate,sample_rate,channels -of json "$master"
