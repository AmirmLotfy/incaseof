---
description: Android / Kotlin / Compose conventions
globs: ["android/**"]
---

# Android rules

## Toolchain facts (verified — do not "correct" these)
- AGP 9 has **built-in Kotlin**. Never apply `org.jetbrains.kotlin.android`.
- `org.jetbrains.kotlin.plugin.compose` **is** still applied separately.
- `kotlin { compilerOptions { } }` goes **outside** the `android { }` block.
- compileSdk/targetSdk **37**, minSdk 26. AndroidX requires 37+.
- Pin to current stable. Material3 1.5.x is alpha — do not adopt it for the hackathon.

## Architecture
```
Compose UI → ViewModel → UseCase → Repository → (Room cache | API)
```
Room is a **cache only**. It is never authoritative — DynamoDB is.

## WorkManager
Allowed: cache sync, telemetry upload, refreshing non-critical content.
**Never**: "in 30 minutes contact Maya." Safety timers live in EventBridge. A device-owned timer
does not fire when the device is off, which is exactly the case the product exists for.

## Compose
- No dynamic colour. "Orange means unresolved" cannot be true only on some wallpapers.
- Use `LocalIcoColors` for semantic colours Material3 has no slot for (`signal`, `resolved`).
- Times use tabular figures. Reflowing digits read as instability.
- Hoist state; keep composables free of business logic.
- Handle process death — an Alert must survive it.

## Accessibility (blocking, not aspirational)
- TalkBack labels on every interactive element.
- 48dp minimum touch target.
- Never convey state by colour alone; pair with text or shape.
- Support large text and reduced motion.
- Timeline content must read in chronological order to a screen reader.

## Notifications
The primary action ("I'M OKAY") must work **from the notification**, without opening the app.
Someone checking in at 2am should not have to navigate.

## Never
- Request a permission before the feature that needs it ships.
- Add location permission — the product does not use it.
- Hardcode a phone number, even in a test.
