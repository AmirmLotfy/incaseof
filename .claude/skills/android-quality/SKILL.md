---
name: android-quality
description: Review Android Compose code for state handling, accessibility, edge-to-edge, process death and stable dependencies. Use after writing or changing any Android screen, ViewModel, or notification.
---

# Android quality review

## Build gate
```bash
cd android && ./gradlew assembleDebug testDebugUnitTest lintDebug ktlintCheck
```
All four, not just assemble.

## Compose
- State hoisted; composables free of business logic.
- No dynamic colour — semantics must be identical on every device.
- Semantic colours via `LocalIcoColors`; never hardcode a hex.
- `@Preview` for every new screen, in light and dark.
- Times use tabular figures.

## Accessibility — blocking
- TalkBack label on every interactive element.
- 48dp minimum touch target.
- **No state by colour alone.** Pair with text or shape.
- Large text and reduced motion supported.
- Timelines read chronologically to a screen reader.

Verify with TalkBack and large-font settings, not by inspection.

## Lifecycle
- Survives process death: an active Alert must reappear correctly after the app is killed.
- Survives configuration change.
- Notification primary action works **without opening the app**.
- No safety timer on the device. Ever.

## Dependencies
Current stable only. If a version is alpha, do not adopt it — see `.claude/rules/android.md`.
