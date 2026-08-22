---
name: visual-qa
description: Check a rendered UI against the design system and the anti-slop rules, including contrast, spacing, tokens and copy. Use after implementing any user-facing surface, before calling it done.
---

# Visual QA

## 0. Were references locked first?
If `docs/design/REFERENCES.md` has no entry for this surface, the work started in the wrong order.
Say so.

## 1. Anti-slop scan
Run the mechanical check:
```bash
./scripts/check-antislop.sh
```
Then look, because a grep cannot see a layout:
- Gradient, glow, blur, glassmorphism, sparkle, robot, brain, magic wand?
- Every section wrapped in a rounded card? Bento grid?
- Phone floating in a gradient cloud?
- Could this be any AI SaaS landing page? → redesign.

## 2. Tokens
```bash
npm run tokens:check
```
No hardcoded hex anywhere in UI code. Web uses `var(--ico-*)`; Android uses `LocalIcoColors`.

## 3. Contrast and colour semantics
- Text pairs meet **AA**. Verify measured, not assumed.
- Signal Orange has **Ink** text, never white.
- Unresolved is Signal Orange; Brick is only for destruction and errors.
- Nothing conveys state by colour alone.

## 4. Copy
Check against `docs/design/COPY.md`: no banned words, no invented numbers, no speculation about
danger, and every confirmation states what it does **not** change.

## 5. Responsive and motion
Test 375 / 768 / 1280. No horizontal body scroll. Wide content scrolls inside its own container.
Motion explains causality; `prefers-reduced-motion` honoured.
