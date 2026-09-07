# ICO demo-video editing handoff

The picture target is 1920×1080, 30 fps, 4:30, with a hard maximum below 5:00. The source
of truth for narration and claims is `docs/DEMO-VIDEO-SCRIPT.md`; `narration.txt` is the
plain-text voice input. Do not retain a spoken claim when the corresponding accepted live
capture is unavailable.

## Editorial sequence

| Time | Required picture evidence | Audio |
|---|---|---|
| 0:00–0:20 | Up to three approved human-context plates; generated footage totals under 20 seconds | Narration 1; music may begin quietly |
| 0:20–0:55 | Real plan entry, AgentCore response and literal preview | Narration 2 |
| 0:55–1:20 | Schedule, grace, Circle roles and explicit activation | Narration 3 |
| 1:20–2:10 | Live Drill, safe-sink label, Scheduler/workflow timeline | Narration 4 |
| 2:10–2:50 | Signed responder link, claim, visible lease, explicit resolution | Narration 5 |
| 2:50–3:30 | Redacted runtime/model/tool/Cedar trace and one denied arbitrary-contact request | Narration 6 |
| 3:30–3:55 | Focused retry, duplicate, lease-conflict and model-outage test evidence | Narration 7 |
| 3:55–4:20 | Android/web/responder montage and permission evidence | Narration 8 |
| 4:20–4:30 | ICO lockup, live demo URL and repository URL | Narration 9; clean resolve |

## Picture and sound rules

- Product behavior and AWS traces use real accepted captures only. Never composite a fake
  notification, console result, policy decision, device screen or timeline event.
- Redact account IDs, subject identifiers, contact endpoints, tokens and personal
  notifications before the image reaches the editing timeline.
- Generated plates are supporting context, not evidence, and stay below 20 seconds total.
- Keep music below narration and record its license/source in `media-provenance.json`.
- Captions must be retimed from the final narration waveform, not copied blindly from the
  planned beat boundaries.
- Export a high-quality review master first, inspect it end to end, then make the upload
  encode. The verifier checks the final local delivery master.

## Delivery layout

Place the local package under `submission/video/final/`:

```text
ico-demo-master-1080p.mp4
ico-narration.wav
ico-demo.en.srt
ico-demo.en.vtt
ico-youtube-thumbnail.png
media-provenance.json
<editable timeline export>
```

The directory is intentionally ignored by Git because it can contain large media and
redacted live material. Run `./scripts/verify-video-package.sh` before upload.
