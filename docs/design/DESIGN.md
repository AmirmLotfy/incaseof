# In Case of — Design System

> **In Case of does not decide whether someone is in danger. It notices unresolved
> expectations and works to close the loop.**

---

## 1. Direction: Contingency Utility

The visual metaphor is **not "AI."** It is:

> a beautifully designed emergency card, departure board, modern civic instruction system and
> personal notebook combined.

In Case of is a precise modern utility, not an AI-themed application. Urgency should **reduce**
interface complexity, never increase it.

**This is deliberately not beige + terracotta + sage.** The "calm editorial, cream and clay,
decorative serif" look has itself become AI-slop. We are an instruction system.

---

## 2. Anti-slop rules — never introduce

purple gradient · blue/purple gradient · mesh gradient · glowing orb · sparkles · robot ·
brain icon · magic wand · floating glass balls · generic neural network · "AI powered" badge ·
large collections of rounded cards · arbitrary bento grids · every section inside a card ·
giant pills everywhere · glassmorphism · decorative blur · random illustrated people

**Banned copy:** "revolutionize" · "reimagine" · "supercharge" · "unlock" · "seamless" ·
"next-generation" · "future of safety" · fake metrics · fake testimonials · fake company logos ·
fake download numbers.

> **If a design can be confused with a generic AI SaaS landing page, redesign it.**

`.claude/skills/visual-qa` checks this mechanically. It is not a matter of taste.

---

## 3. Light palette

| Role | Token | Hex |
|---|---|---|
| Background | Chalk | `#F6F5F0` |
| Main surface | Paper | `#FFFDF8` |
| Text | Ink | `#171A18` |
| Secondary text | Graphite | `#626660` |
| Divider | Stone | `#E4E4DE` |
| Primary | Bottle Green | `#205C47` |
| Attention | Signal Orange | `#E85B2A` |
| Warning | Amber | `#D99A29` |
| Critical | Brick | `#B44438` |
| Resolved | Moss | `#39705A` |

### Measured contrast (computed, not asserted)

| Pair | Ratio | Level |
|---|---:|---|
| Ink on Chalk | 16.07:1 | AAA |
| Ink on Paper | 17.25:1 | AAA |
| Graphite on Chalk | 5.36:1 | AA |
| Graphite on Paper | 5.76:1 | AA |
| White on Bottle Green | 7.83:1 | AAA |
| **Ink on Signal Orange** | **4.98:1** | **AA** |
| ~~White on Signal Orange~~ | ~~3.52:1~~ | **FAILS AA — forbidden** |
| Ink on Amber | 7.19:1 | AAA |
| White on Brick | 5.49:1 | AA |
| White on Moss | 5.77:1 | AA |
| Bottle Green on Chalk | 7.17:1 | AAA |
| Brick on Chalk | 5.03:1 | AA |
| Moss on Chalk | 5.29:1 | AA |

> ### Signal Orange takes **Ink** text, never white.
> This is a hard accessibility constraint, not a preference: white on Signal Orange measures
> 3.52:1 and fails AA for normal text. Ink passes at 4.98:1.

**Stone (`#E4E4DE`) is a decorative rule only** — 1.17:1 against Chalk. It must never carry state,
meaning, or a UI-component boundary that a user needs to perceive. Where a border conveys
something (focus, selection, error), use a token that meets 3:1.

---

## 4. Colour semantics

| Token | Means |
|---|---|
| **Bottle Green** | Primary calm actions · active Plan · resolved status |
| **Signal Orange** | Unresolved attention · timeline marker · *the one* brand marker |
| **Amber** | Degraded / attention state |
| **Brick** | Destructive action or genuine system error |

**A missed Moment is not red.** Missing means *unresolved*, not *emergency* (PRD §4.2). Turning the
interface red because someone hasn't tapped a button yet is the exact anxiety this product exists to
avoid. Brick is for destruction and errors; unresolved is Signal Orange.

Signal Orange is a **single marker**, used sparingly. Discipline here is what separates this from a
colourful startup dashboard.

---

## 5. Dark palette

| Role | Hex | Contrast on Bg |
|---|---|---:|
| Background | `#101310` | — |
| Surface | `#181C19` | — |
| Raised | `#212622` | — |
| Text | `#F2F1EB` | 16.53:1 AAA |
| Secondary | `#A9AEA9` | 8.30:1 AAA |
| Primary | `#8FC3AB` | 9.41:1 AAA |
| Signal | `#FF8055` | 7.55:1 AAA |
| Warning | `#E3B151` | 9.51:1 AAA |
| Critical | `#F29A90` | 8.73:1 AAA |
| Divider | `#343934` | 1.59:1 — decorative only |

**No pure black. No neon.**

---

## 6. Typography

### Android — use native platform typography
Do not bundle a trendy startup font.

| Role | Size / weight |
|---|---|
| Moment time | 42sp / medium |
| Status | 30sp / medium |
| Screen title | 26sp / semibold |
| Card title | 19sp / medium |
| Body | 16sp / regular |
| Action | 16sp / medium |
| Metadata | 13sp / medium |

Times use **tabular numerals** wherever supported — a clock that reflows as digits change reads as
unstable, and this product's core content is times.

### Web — Public Sans + IBM Plex Mono
Public Sans for headlines, body, navigation, buttons. IBM Plex Mono **sparingly**, for timestamps,
status labels, event sequences and technical explanation.

**No serif.** This deliberately avoids the now-ubiquitous "AI startup editorial serif on warm
beige" treatment.

---

## 7. Shape

Avoid 32px-radius-everything.

```
Hero status panel   20dp      Buttons           14dp
Normal surface      14dp      Bottom sheet top  24dp
Input               12dp      Status chips       8dp
```

**Some information sections have no surrounding card.** Use rules and dividers. Not every section
is a card — that habit is what produces bento-grid slop.

---

## 8. Spacing

```
4  8  12  16  24  32  48  64  96  128
```

No random 37px gaps. Web: max width 1440, content 1240, readable prose 680–760.

---

## 9. Motion

**Motion explains causality.** It is not decoration.

```
Plan activation:  timeline contracts slightly → status becomes ACTIVE → next Moment appears
Alert resolution: orange status line → short contraction → green resolved mark
```

No confetti. No bouncing red icons. Honour `prefers-reduced-motion` / Android reduced-motion.

---

## 10. Haptics

Confirmation → soft pulse. Plan activation → two subtle pulses. Attention required → one firmer
pulse.

**Never** ship anxiety-inducing repeating vibration patterns by default. The product's job is to
reduce background dread, and a phone that buzzes like an alarm undoes that in one interaction.

---

## 11. Accessibility floor

Non-negotiable, enforced in CI:

- WCAG 2.2 **AA** on web · Android TalkBack support · content descriptions
- **No state conveyed by colour alone** — always pair with text or shape
- Scalable text · 48dp minimum Android touch target
- Keyboard-navigable responder site · reduced-motion support · visible focus treatment
- Screen-reader-logical chronology in timelines
- Localisation-safe layouts (no fixed-width text containers)

---

## 12. Product-surface language rules

Never show the user: workflow · state machine · orchestration · LLM · agent loop · prompt ·
tool call. See PRD §3 for the full vocabulary mapping.

**Loading states name concrete system activity:**
- ✅ "Building your plan…" → "Checking timing and Circle permissions…"
- ❌ "AI is thinking..."

**No generic greeting** ("Good afternoon, Amir 👋") unless it is actually useful. This is a
utility, not a lifestyle dashboard.

**Voice UI uses a simple expanding audio level meter** — never an animated glowing sphere.
