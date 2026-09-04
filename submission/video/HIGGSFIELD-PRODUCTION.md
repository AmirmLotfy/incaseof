# Higgsfield production control

Status: **prepared; no paid generation authorized**.

Before any generation, confirm an authenticated Higgsfield tab, project name, available
credits and a user-approved fixed shot budget. Dispatch one job at a time and visibly
review the result before retrying.

## Maximum generation scope

| Shot | Duration | Purpose | Attempts | Status |
|---|---:|---|---:|---|
| HF-01 | 5s | Calm independent living plate | 1 + 1 repair | Not dispatched |
| HF-02 | 5s | Late commute plate | 1 + 1 repair | Not dispatched |
| HF-03 | 5s | Solo outdoor activity plate | 1 + 1 repair | Not dispatched |
| VO-01 | 4:30 max | Warm neutral English narration | 1 + 1 repair | Not dispatched |

Generated footage must remain below 20 seconds of the final film. If authenticated
Higgsfield does not expose voice generation, stop that lane and use a human recording;
do not switch providers silently.

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
