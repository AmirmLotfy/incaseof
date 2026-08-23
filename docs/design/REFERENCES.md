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

## Still requiring research before build

| Surface | Phase | Status |
|---|---|---|
| Marketing site — hero, timeline device, section rhythm | 6 | **PENDING** — no specification exists for layout beyond copy |
| Responder Incident Room | 6 | PARTIAL — §21 gives content, not layout |
| Privacy / context-tier explainer | 6 | **PENDING** |
