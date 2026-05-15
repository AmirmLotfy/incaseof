# In Case Of

> **A local-first safety agent that converts "what if something happens?" into trusted, user-approved action plans using Gemma 4 on-device.**

Built for the [Gemma 4 Good Hackathon](https://www.kaggle.com/competitions/gemma-4-good-hackathon).

---

## What it does

You describe a safety scenario using two simple fields:

```
In case of...   → I don't check in for 24 hours
The app should... → Ask me if I'm okay, then message my mom
```

Gemma 4 converts this into a verified safety workflow. You review every detail, approve the plan, and the app monitors silently in the background — acting only if you don't respond.

---

## Why it matters

People living alone, solo travelers, hikers, caregivers, and night-shift workers need simple safety plans. Emergency services are for crises. This fills the gap: **trusted contacts, on-device intelligence, user approval always.**

---

## How Gemma 4 is used

| Role | Details |
|------|---------|
| Natural language → workflow JSON | User describes scenario in plain English; Gemma outputs structured JSON |
| Risk detection | Gemma classifies risk level (low/medium/high) with reasons |
| Permission explanation | Gemma generates human-readable permission justifications |
| Emergency message copy | Gemma drafts the trusted contact alert message |
| Safety boundary enforcement | Gemma flags unsupported or unsafe requests |
| Clarifying questions | Gemma asks follow-up questions when intent is ambiguous |

**Architecture principle:** Gemma plans. Deterministic Kotlin validates. WorkManager schedules. Android intents execute only after user approval.

---

## Architecture

```
User input (text or voice)
        ↓
  Gemma 4 E2B on-device (LiteRT-LM)
        ↓
  JSON workflow output
        ↓
  WorkflowSafetyValidator (deterministic rules)
        ↓
  Safety Review Screen (user approval)
        ↓
  Room database (persisted)
        ↓
  WorkManager (15-min periodic InactivityCheckWorker)
        ↓
  Missed check-in detected
        ↓
  Verification notification → "Are you okay? [I'm safe]"
        ↓
  No response → VerificationTimeoutWorker
        ↓
  Action Review Screen (user confirms)
        ↓
  SMS/Email/Call intent (user sends)
        ↓
  CaseEventLogger → Room → Emergency Log
```

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Language | Kotlin |
| UI | Jetpack Compose + Material 3 |
| AI | LiteRT-LM 0.11.0 / Gemma 4 E2B (on-device, no API key) |
| Background | WorkManager |
| Persistence | Room + DataStore |
| DI | Hilt |
| Serialization | kotlinx.serialization |
| Location | Fused Location Provider |
| Navigation | Navigation Compose |

---

## Demo flow

1. **Create case** — type or speak your scenario using the two-field input
2. **Gemma compiles** — animated 4-step planning screen with live status
3. **Safety review** — inspect trigger, verification, actions, permissions, and risk level
4. **Activate** — choose trusted contact, enable the case
5. **Simulation** — tap "Run simulation" to watch the full 24-hour workflow in seconds
6. **Check-in missed** — WorkManager detects inactivity, sends verification notification
7. **Action review** — confirm before SMS is sent to trusted contact
8. **Emergency log** — full timeline of every event

---

## Key screens

| Screen | Purpose |
|--------|---------|
| Onboarding | Explains local-first, user-approval model (3 cards) |
| Create Case | Two-field natural language input + voice buttons + suggestion chips |
| Compiling | Animated Gemma planning screen |
| Safety Review | Full plan review: trigger / verification / actions / permissions / risk |
| Contact Picker | Add trusted contact name, phone, email, relationship |
| Case Detail | Tabs: Plan · Timeline · Actions · Simulation |
| Simulation | Step-by-step demo of the full missed check-in workflow |
| Action Review | "Send this message to Mom?" final confirmation |
| Emergency Log | Full timeline of all case events |
| About | Architecture, Gemma usage, limitations, hackathon context |

---

## Running the app

```bash
# Build debug APK
./gradlew assembleDebug

# Install on connected device/emulator
./gradlew installDebug
```

**Requirements:** Android SDK 35, Java 17, Android device/emulator API 26+

### Switching to real Gemma model

**No API key required.** Gemma runs 100% on-device via LiteRT-LM (Apache 2.0 license).

By default the app uses a `MockCasePlanner` (5 demo scenarios). To use the real model:

1. Download `gemma-4-E2B-it.litertlm` from [HuggingFace litert-community](https://huggingface.co/litert-community/gemma-4-E2B-it-litert-lm)
2. Push to device: `adb push gemma-4-E2B-it.litertlm /data/local/tmp/llm/`
3. In `app/build.gradle.kts`, uncomment the `litertlm-android` dependency
4. In `app/build.gradle.kts`, set `USE_MOCK_PLANNER` to `"false"`
5. Rebuild with `./gradlew assembleDebug`

---

## Safety design

- ❌ No hidden monitoring
- ❌ No automatic SMS/calls without user confirmation
- ❌ No background microphone
- ❌ No emergency services dispatch
- ❌ No broad contacts permission
- ✅ User approves every action before execution
- ✅ Verification notification always sent first
- ✅ Every step logged to local database
- ✅ "I'm safe" cancels all pending actions instantly
- ✅ All data stays on device

---

## Limitations

- WhatsApp support is prepared-message deep link only (not automatic send)
- SMS requires user to tap Send in their native SMS app (ACTION_SENDTO)
- Background WorkManager is subject to Android Doze/battery optimization
- Real Gemma model requires ~3.2 GB RAM and model file on device (no API key needed)
- LiteRT-LM 0.11.0 required for on-device inference
- V1 does not support emergency services dispatch
- Not a replacement for 911 or emergency medical services

---

## Hackathon

Built for **Gemma 4 Good** — using AI for positive societal impact.

- **Model:** Gemma 4 E2B IT (LiteRT-LM quantized, `.litertlm` format)
- **Inference:** On-device, local-first, no cloud required, **no API key needed**
- **Runtime:** LiteRT-LM 0.11.0 Kotlin API
- **Impact:** Safety automation for people living alone, travelers, caregivers
