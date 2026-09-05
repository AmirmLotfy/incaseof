# Higgsfield production control

Status: **authenticated and budget prepared; no generation dispatched**.

The live account audit on 2026-09-04 confirmed a Max plan with 119 credits remaining.
Seedance 2.5 cost 45 credits for the default five-second shot; Seedance 2.0 Mini cost 20.
MiniMax Speech 2.8 HD showed 6.6 credits for a narration-length script. Re-check each price
immediately before dispatch because provider pricing is live state.

The proposed hard cap is **113.2 credits**: three 20-credit base shots, no more than two
20-credit repair attempts shared across all shots, and no more than two 6.6-credit voice
attempts. Stop if a displayed price would exceed that cap or leave insufficient credits for
the remaining approved items. Dispatch one job at a time and visibly review it before any
repair.

## Maximum generation scope

| Shot | Duration | Purpose | Attempts | Status |
|---|---:|---|---:|---|
| HF-01 | 5s | Calm independent living plate | 1 base; shared repair pool | Not dispatched |
| HF-02 | 5s | Late commute plate | 1 base; shared repair pool | Not dispatched |
| HF-03 | 5s | Solo outdoor activity plate | 1 base; shared repair pool | Not dispatched |
| VO-01 | 4:30 max | Warm neutral English narration | 1 + 1 repair | Not dispatched |

Generated footage must remain below 20 seconds of the final film. If authenticated
Higgsfield does not expose voice generation, stop that lane and use a human recording;
do not switch providers silently.

## Locked shot prompts

All plates are 16:9, five seconds, natural live-action realism, restrained camera movement,
no visible product UI, no text, no logos and no emergency imagery.

**HF-01 - independent living:** "Quiet blue-hour interior of a modest contemporary
apartment. An adult woman in her fifties finishes watering a windowsill plant, sets the
watering can down and looks contentedly toward the evening light. Slow, nearly imperceptible
push-in from across the room, natural practical lighting, grounded documentary realism,
calm and self-possessed, no phone close-up, no distress."

**HF-02 - late commute:** "A well-lit urban train platform after sunset. An adult commuter
in a simple coat steps off a train and walks steadily toward the exit among a few ordinary
passengers. Gentle lateral tracking shot, realistic transit lighting, quiet confidence,
unhurried everyday moment, no pursuit, no empty threatening station, no alarm imagery."

**HF-03 - solo outdoors:** "Wide golden-hour view on a clearly marked hillside trail. A
solo adult hiker pauses to take in the landscape, adjusts one backpack strap and continues
at an easy pace. Stable slow pan, natural wind in clothing and grass, expansive but safe,
documentary realism, no fall, no injury, no rescue imagery."

**VO-01:** Use only the narration paragraphs in `docs/DEMO-VIDEO-SCRIPT.md`, in timeline
order. Warm neutral English voice, measured and reassuring, lightly conversational, no
trailer intensity and no synthetic urgency. Pronounce ICO as the three letters "I C O."

## Provenance ledger fields

For every dispatched item record: local shot ID, exact prompt, model, project, visible job
ID, visible result ID, dispatch time, completion time, charged credits, exported filename,
SHA-256, review decision, repair relationship and rights/license notes.

## Delivery package

- `ico-demo-master-1080p.mp4`
- `ico-narration.wav`
- `ico-music-licensed.wav` if used
- `ico-demo.en.srt` and `ico-demo.en.vtt`
- `ico-youtube-thumbnail.png`
- editable source timeline
- `media-provenance.json`

Real deployed capture must be used for every claimed feature and AWS trace.

Checked-in preparation now includes `narration.txt`, `EDITING-HANDOFF.md` and
`media-provenance.template.json`. Final binaries and live-capture provenance belong in the
Git-ignored `submission/video/final/` directory and must pass
`scripts/verify-video-package.sh` before upload.
