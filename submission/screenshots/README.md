# Required live screenshot set

Capture only after the demo release manifest passes. Keep the browser and Android status
bars clean and redact accounts, tokens, contact endpoints and personal notifications.

Required files:

1. `marketing-desktop.png` - 1440px-wide canonical homepage.
2. `marketing-mobile.png` - 390px-wide homepage and navigation.
3. `web-plan-preview.png` - authenticated compiled plan preview.
4. `android-home.png` - physical or API 37 device home.
5. `android-create.png` - natural-language creation and literal preview.
6. `android-circle.png` - invitation/consent state with synthetic names.
7. `android-drill.png` - visible demo timing and live Alert state.
8. `responder-claim.png` - unclaimed signed link in a private window.
9. `responder-lease.png` - checking lease; Alert still open.
10. `responder-resolved.png` - explicit resolution.
11. `audit-timeline.png` - deployed end-to-end timeline.
12. `developer-trace-redacted.png` - AgentCore/model/tool/Cedar/deterministic evidence.

`scripts/build-devpost-image.sh` refuses to write the final project image until its four
required source captures are present.
