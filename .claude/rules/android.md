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
Compose UI → ViewModel → Repository → (local cache | API)
```
Any local store is a **cache only**. It is never authoritative — DynamoDB is.

Dependency injection is a hand-written `AppContainer`, not Hilt. AGP 9 compiles Kotlin
natively and stacking KSP on top is unproven; the graph is small enough that generated code
would cost more than it saves. Reconsider when one file no longer explains it.

Room is deferred for the same reason. It is a cache, so nothing depends on it being there.

## Toolchain facts learned the hard way
- ktlint reads its code style from `.editorconfig`. The Gradle plugin's `android.set(true)`
  does not reach it.
- Amplify needs `isCoreLibraryDesugaringEnabled`; it fails at AAR metadata check, not compile.
- Adaptive icons need `mipmap-anydpi-v26` even at minSdk 26.
- `androidx.test.ext:junit` is at 1.3.0 and `espresso-core` at 3.7.0 — not the 1.4.x/3.8.x
  you might assume from the other AndroidX versions.

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
