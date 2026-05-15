# In Case Of — Local-First Safety Automation Powered by Gemma 4

**On-device AI that watches over you when no one else can.**

---

## The Problem

Every year, thousands of people living alone, traveling solo, or managing chronic conditions face emergencies where no one knows something is wrong. A solo hiker falls and can't call for help. An elderly person living alone doesn't wake up. A night-shift worker never checks in after their shift.

Current solutions require expensive subscription services, constant internet connectivity, or rely on the user being conscious enough to press a panic button. None of them work when the emergency is that you *can't* respond.

**In Case Of** flips the model: instead of requiring you to signal distress, it acts when you fail to signal that you're safe.

## How It Works

The user describes a safety scenario in plain language:

> *"In case of: I don't check in for 4 hours during my solo hike"*
> *"The app should: Send my last known location to my sister and call my emergency contact"*

Gemma 4 E2B, running entirely on-device via LiteRT-LM, converts this natural language into a structured safety workflow — a JSON plan specifying triggers, verification steps, and actions. The user reviews and approves every detail before activation. If the user misses their check-in, the app verifies with a notification ("Are you okay?"), waits a configurable window, and then prepares the approved actions for the user's final confirmation.

No silent execution. No cloud dependency. No API key.

## Architecture

**In Case Of** is a native Android application built with Kotlin, Jetpack Compose, and a clean MVVM architecture using Hilt for dependency injection.

### Gemma 4 Integration

The core intelligence layer uses **Gemma 4 E2B IT** in the `.litertlm` format via **LiteRT-LM 0.11.0** — Google's on-device LLM runtime. The integration follows a structured pipeline:

1. **Prompt Construction** — A system prompt constrains Gemma to output only valid JSON matching a strict schema. The schema defines triggers (`missed_checkin`, `scheduled_time`), verification parameters, actions (`send_sms`, `send_email`, `call_contact`, `open_whatsapp`), permissions, and risk assessment. The model is explicitly instructed to never execute actions, never create surveillance workflows, and to flag ambiguous requests with clarifying questions.

2. **On-Device Inference** — The `GemmaEngineProvider` initializes LiteRT-LM's `Engine` with an `EngineConfig` pointing to the local model file and uses `Conversation` sessions with `ConversationConfig` for system instructions and sampler settings. The `sendMessageAsync` API returns a Kotlin `Flow<Message>` for streaming responses. No network call is made. No API key is required. All processing happens on the user's device.

3. **JSON Extraction** — A `JsonExtractor` handles the reality that LLMs sometimes wrap JSON in markdown code blocks or add explanatory text. It parses the first valid JSON object from the response using a bracket-depth parser that correctly handles escaped strings.

4. **Deterministic Safety Validation** — This is the critical layer. A `WorkflowSafetyValidator` with 13 validation rules and a `ForbiddenContentChecker` scanning for 14 prohibited phrases (including "spy," "stalk," "surveillance," "record audio," "without consent") acts as the final authority. The model's output is never trusted — every workflow must pass deterministic Kotlin validation before the user can even see it. This validator cannot be bypassed by prompt injection.

### Background Processing

The app uses Android's `WorkManager` for reliable background execution:

- **InactivityCheckWorker** — A periodic worker (every 15 minutes) that checks all active cases for missed check-ins. When a check-in window expires, it triggers a high-priority notification asking the user to confirm they're safe.
- **VerificationTimeoutWorker** — A one-shot delayed worker that fires after the verification window expires (configurable, 1–60 minutes). If the user hasn't responded, it transitions the case to `TRIGGERED` status and prepares the approved actions.
- **MarkSafeReceiver** — A `BroadcastReceiver` that handles the "I'm safe" action directly from the notification, canceling the verification timer without needing to open the app.

### Data Layer

- **Room** persists cases (`CaseEntity`) and a full event timeline (`CaseEventEntity`) locally.
- **DataStore** manages onboarding state and user preferences.
- **kotlinx.serialization** handles all JSON encoding/decoding with type-safe sealed classes for `ActionSpec` and `TriggerSpec`.

### Safety-First Action Execution

When actions are triggered, the `ActionExecutor` uses Android's intent system — not silent background execution:

- SMS opens the user's messaging app with a pre-filled message via `ACTION_SENDTO`
- Email opens the mail client via `ACTION_SENDTO` with `mailto:`
- Phone opens the dialer via `ACTION_DIAL` (not `ACTION_CALL` — the user must press the call button)
- WhatsApp opens a deep link with a prepared message

The user always has the final tap. The app never sends a message, makes a call, or shares a location without explicit human confirmation on that specific action.

## Challenges and Technical Decisions

**Why on-device instead of cloud?** Safety scenarios involve sensitive personal information — locations, medical conditions, emergency contacts. Sending this to a cloud API would be a privacy violation. Gemma 4's ability to run locally via LiteRT-LM makes private, offline safety automation possible for the first time.

**Why deterministic validation over model guardrails?** Prompt-based guardrails can be circumvented. Our `WorkflowSafetyValidator` is Kotlin code with explicit rules that run *after* model inference. If Gemma outputs a workflow requesting surveillance, the validator rejects it with a specific error — regardless of how the prompt was crafted. This is defense-in-depth: the model is constrained by its system prompt, and the output is validated by deterministic code.

**Why not auto-send SMS?** Android's `SEND_SMS` permission allows background SMS sending. We deliberately chose `ACTION_SENDTO` (which opens the SMS app) because safety automation must never become a tool for harassment. Every message requires the user to physically tap "Send" in their SMS app. This design decision prioritizes safety over convenience.

**Handling model output variability.** LLMs don't always produce perfectly formatted JSON. Our `JsonExtractor` uses a bracket-depth parser (not regex) to handle markdown-wrapped responses, and `kotlinx.serialization` with `ignoreUnknownKeys = true` and `isLenient = true` gracefully handles minor formatting variations.

## Impact

**In Case Of** serves three underserved populations:

1. **People living alone** — 37% of U.S. households are single-person. A daily check-in case ensures someone is notified if they become unresponsive.
2. **Solo travelers and outdoor enthusiasts** — A hiker or solo traveler can set a location-sharing case that activates only if they miss their check-in, preserving privacy during normal operation.
3. **Caregivers and families** — Adult children can set up medication reminder cases for elderly parents, where the app escalates to the caregiver only after the parent fails to confirm.

The local-first architecture means this works without cell coverage for the AI processing — the model runs entirely on-device. Only the final action (sending an SMS or email) requires connectivity, and by that point, the user is in a potential emergency where alerting contacts is the priority.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Kotlin |
| UI | Jetpack Compose, Material 3 |
| AI | Gemma 4 E2B IT via LiteRT-LM 0.11.0 |
| Architecture | MVVM + Hilt + Clean Architecture |
| Background | WorkManager (periodic + one-shot workers) |
| Persistence | Room + DataStore |
| Serialization | kotlinx.serialization |
| Location | Google Play Services FusedLocationProvider |
| Build | Gradle 8.11.1, Android SDK 35, Java 17 |

## Links

- **Code Repository:** [GitHub — In Case Of](https://github.com/AmirmLotfy/incaseof)
- **Demo Video:** [YouTube — In Case Of Demo](https://youtube.com/watch?v=XXXXX) *(update with your actual URL)*
- **Model:** [Gemma 4 E2B IT on HuggingFace](https://huggingface.co/litert-community/gemma-4-E2B-it-litert-lm)
- **LiteRT-LM Docs:** [ai.google.dev/edge/litert-lm/android](https://ai.google.dev/edge/litert-lm/android)
