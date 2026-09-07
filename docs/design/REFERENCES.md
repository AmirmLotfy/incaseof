# In Case of — Design References

> **In Case of does not decide whether someone is in danger. It notices unresolved
> expectations and works to close the loop.**

---

## STATUS: SPECIFIED (Refero research still outstanding)

The rule is that no significant surface gets built without locked references, because
"make it beautiful" with nothing to work from is how a product turns into generic AI slop.

Refero is not installed, so the **build contract itself is the reference of record** for
Phase 3. It specifies these screens concretely — layout, hierarchy, and copy — so nothing
below is invented. Each surface cites the section that governs it.

**What is still missing:** comparative research. The contract says *what* to build; Refero
would show how comparable products solve the same problems, and would likely sharpen
spacing, density and motion. That remains worth doing before the marketing site (Phase 6),
which has no equivalent specification and is the surface most at risk of drifting generic.

To add it later:
```
/plugin marketplace add referodesign/refero_skill
/plugin install refero@refero
```

---

## Locked references — Phase 3 (Android)

### Home — all clear
**Source:** build contract §60 · **Status:** LOCKED

**What we take:** Status word first (`ALL CLEAR`), then the next Moment with its time, then
the escalation ladder as a compact preview (`you → 10 min → call → 10 min → Maya`). Voice
control as a single wide action. Today's schedule below. Four-tab bottom navigation.

**What we reject:** A greeting header ("Good afternoon, Amir 👋"). This is a utility, not a
lifestyle dashboard, and a greeting is the first step toward a feed. No card wrapping the
whole screen — the status *is* the screen.

**Interaction:** Nothing to act on in the resting state. The screen's job is to be
answerable at a glance: *is anything expected of me?*

### Home — action needed
**Source:** build contract §61 · **Status:** LOCKED

**What we take:** `ACTION NEEDED` replaces `ALL CLEAR`. Expected time shown large. One
primary action, `I'M OKAY`. Two quieter secondary actions. A plain statement of what
happens next and when.

**What we reject:** Red. A missed Moment is Signal Orange — missing means unresolved, not
emergency (DESIGN.md §4). No countdown timer as the focal element; the point is what to do,
not how long is left.

### Active check
**Source:** build contract §16 · **Status:** LOCKED

**What we take:** Title, time, one question, one large primary action, two secondary
options. Nothing else on screen.

**What we reject:** Navigation chrome, marketing copy, anything decorative. **Urgency
reduces interface complexity.** Someone answering this at 2am should see one obvious thing.

### Plan detail
**Source:** build contract §65 · **Status:** LOCKED

**What we take:** Plan name, cadence, time. `WHAT HAPPENS` as a literal timeline of offsets
and actions. `SHARED IF NEEDED` listing each context signal and its release stage.
`CIRCLE` listing members and roles. `Test plan` as a real action.

**What we reject:** A health score. Plan Health is objective facts only (§26) — never
"Safety 92/100", which invents a number and implies a judgement the product does not make.

### Plan creation
**Source:** build contract §62 · **Status:** LOCKED

**What we take:** Four named templates as the primary choice, with natural language as an
alternative below — not the other way round. Plain question: "What should happen?"

**What we reject:** "What would you like your AI agent to automate?" and every variant.
Consumer UI never exposes AI jargon (PRD §3).

### Circle
**Source:** build contract §12 · **Status:** LOCKED

**What we take:** Each member as name, relationship, role, then verification facts. Roles
are explicit (`Primary`, `Backup`) because escalation order is something the subject chose
and should be able to see.

**What we reject:** Avatars and presence indicators. This is not a social surface, and a
green dot next to a person's name implies monitoring that does not happen.

### History
**Source:** build contract §24 · **Status:** LOCKED

**What we take:** Grouped by day, each entry showing what resolved it and who. Reassuring
rather than forensic — the full audit trail is one tap in, not the default view.

**What we reject:** Charts, streaks, adherence percentages. Gamifying a safety record
creates pressure to keep a streak, which is precisely the wrong incentive.

---

## Cross-cutting, from DESIGN.md

Binding regardless of the above: colour semantics and measured contrast (§3–5), the type
scale with tabular figures for times (§6), shape scale (§7), motion that explains causality
(§9), haptics that do not manufacture anxiety (§10), and the accessibility floor (§11).

---

## Known rejections (already decided, do not re-litigate)

| Rejected | Why |
|---|---|
| Generic "calm editorial" — cream, clay, decorative serif | Has itself become AI-slop |
| Indigo / violet defaults | Immediate AI-SaaS signal |
| Gratuitous gradients, glassmorphism | See DESIGN.md §2 |
| Generic landing-page rhythm (hero → 3 cards → CTA) | Reads as template |
| Phone floating in a gradient cloud | The most common AI-app hero cliché |
| Dynamic colour on Android | "Orange means unresolved" cannot depend on wallpaper |

---

## Locked references — Phase 6 (web)

### Incident Room — responder
**Source:** build contract §21, §14, §20 · **Status:** LOCKED

**What we take:** Person first, then the fact, then what was already tried, then one
action. `WHAT'S HAPPENED` as a literal timeline of times and events. `WHAT'S NEXT` naming
who is contacted and when. Once claimed, the screen changes entirely: who is checking, how
long is left, and the explicit statement that backup contact is paused.

**What we reject:** Any speculation about what is wrong. The page says somebody has not
responded — never that they may be hurt. No map, no location, no photograph of the subject.
No account, no sign-up, no cookie banner: this has to work at 2am, on a lock screen, from a
link in an SMS.

**Interaction:** One primary action. `I'M CHECKING` is deliberately not the same colour as
a resolution — acknowledging is not resolving, and the interface should not let those two
feel like the same act.

### Marketing site
**Source:** build contract §69–§85 · **Status:** LOCKED

**What we take:** The **timeline is the brand device** (§69) — the product's own mechanism
is the identity, which is stronger than any abstract imagery. Hero is a 55/45 split, type
left, live product timeline right (§74). Sections are full-width alternating editorial rows
(§78). The beta CTA is a Signal Orange **rule**, never an orange background (§83). Public
Sans and IBM Plex Mono, no serif (§71). Max width 1440, content 1240, prose 680–760 (§72).

**What we reject:** A phone floating in a gradient cloud (§74 says so outright). A four-card
scenario grid (§78 says so outright). Serif-on-beige editorial, which has itself become the
AI-startup house style. Any invented metric, testimonial, logo or download count (§87).

**Interaction:** The hero teaches the product by running it — "miss the check" advances the
timeline through the real escalation ladder (§75). No video, no animated typing.

### Privacy / context tiers
**Source:** build contract §80 · **Status:** LOCKED

**What we take:** Four tiers shown as state, from NORMAL (nothing shared) through to
LOCATION (off). Pre-authorisation explained by showing it rather than describing it.

**What we reject:** A shield illustration, a padlock, and the word "privacy-first" standing
on its own. Privacy is shown by what the product does not collect.

---

## Production References (Mobbin Research)

### 1. Incident Room Timeline & Activity Trace
- **[incident.io Incident Timeline](https://mobbin.com/screens/590e4229-15d9-4d12-808b-2e5479a1d804)** & **[incident.io Activity Log](https://mobbin.com/screens/9a03356b-daf2-4c06-95a6-facc978430ae)**
  - **What we take:** Pure vertical chronological trace, explicit state transitions (`Investigating → Fixing`), assigned owner indicator, clean metadata side panel.
  - **What we reject:** Complex SaaS sub-navigation, comment threads, and multi-tab overhead. The responder Incident Room must remain single-action.
- **[Better Stack Incident Timeline](https://mobbin.com/screens/df22e3d7-456f-4669-a06f-2ef144dd38d1)**
  - **What we take:** High-contrast dot-and-line tree with explicit attribution ("Acknowledged by [name]", "Resolved by [name]"). Validates our core invariant: *Acknowledged does not equal resolved*.

### 2. Contingency Utility & Status Cards
- **[Flighty Flight Status Card](https://mobbin.com/screens/a315a3cc-6234-4d7c-a3ce-9271f5a10092)**
  - **What we take:** Departure board aesthetic, tabular figures for countdowns, single amber/orange accent token against dark background, instant readability at a glance.
- **[American Airlines Lockscreen Status](https://mobbin.com/screens/ac125762-9da7-4dda-b694-8304e323c2bb)**
  - **What we take:** Compact urgency representation (`Boards in 17 minutes`) paired with a single status tag (`DELAYED`).
- **[Base Security Cooldown](https://mobbin.com/screens/4a620c15-cd48-4970-b9c7-97b77074462f)**
  - **What we take:** Cooldown timing before critical action confirmation, ensuring deliberate interaction rather than accidental dismissal.

---

## Still requiring research before build

Nothing blocking remains for the surfaces in P0. What Refero and Mobbin add to future iterations:

| Surface | Research focus |
|---|---|
| Marketing section rhythm | Comparative editorial layout density and vertical pacing |
| Hero timeline motion | Easing and cadence of the real escalation ladder progression |
| Small mobile viewports | Responsive 320px lockscreen card degradation |
