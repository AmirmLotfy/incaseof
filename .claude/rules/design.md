---
description: Visual and copy standards
globs: ["apps/**", "android/**", "docs/design/**"]
---

# Design rules

Read `docs/design/DESIGN.md` before any user-facing change. It is binding.

## Research first
**No significant new surface without locked references in `docs/design/REFERENCES.md`.** Search
styles → lock references → search screens → search flow → record → design → implement →
screenshot → compare → fix.

## Never introduce
purple/blue gradients · mesh gradients · glowing orbs · sparkles · robot or brain icons · magic
wands · glassmorphism · decorative blur · "AI powered" badges · bento grids · every-section-a-card ·
phone floating in a gradient cloud · random illustrated people.

> If it could be confused with a generic AI SaaS landing page, redesign it.

## Never write
revolutionize · reimagine · supercharge · unlock · seamless · next-generation · future of safety ·
"AI is thinking..." · any invented metric, testimonial, logo, or download count.

## Colour discipline
- Signal Orange takes **Ink**, never white (3.52:1 fails AA).
- A missed Moment is Signal Orange, **not** Brick. Missing ≠ emergency.
- Stone/Divider are decorative only — they must never carry state.
- Tokens are generated. Edit `packages/design-tokens/tokens.json`, run `npm run tokens`.

## Tone
Concrete over abstract. State what happened and what happens next. Never speculate about danger
unless a human said it. Always say what a change does **not** affect ("This only changes tonight").
