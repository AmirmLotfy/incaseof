# In Case of — Design References

> **In Case of does not decide whether someone is in danger. It notices unresolved
> expectations and works to close the loop.**

---

## STATUS: PENDING RESEARCH

**This file is deliberately not filled in yet.** It requires the Refero MCP, which needs an
interactive OAuth sign-in that only the repository owner can complete:

```
/plugin marketplace add referodesign/refero_skill
/plugin install refero@refero
```

…then complete the browser sign-in.

**No significant user-facing surface may be designed until this file is populated.** That rule
exists because the alternative — "make this beautiful" with no locked references — is precisely how
a project drifts into generic AI-SaaS slop. Research first, then design.

`docs/design/DESIGN.md` (tokens, type, shape, motion, accessibility) is complete and binding
regardless; it does not depend on Refero. What is blocked here is *layout and interaction
reference*, not the design system.

---

## Required research before each major surface

Per the build contract, run this loop — never skip to implementation:

```
1. search styles                6. record references (this file)
2. lock visual references       7. design
3. search concrete screens      8. implement
4. inspect similar screens      9. screenshot
5. search flow if multi-step   10. compare → 11. fix
```

## Surfaces requiring locked references

| Surface | Status |
|---|---|
| Android Home (all-clear + active-alert states) | PENDING |
| Plan builder / natural-language compile preview | PENDING |
| Incident Room (responder web) | PENDING |
| Marketing hero + timeline device | PENDING |
| Privacy / context-tier explainer | PENDING |

## Research directions to search

1. Architectural ledger / utility-style layouts
2. High-trust product pages
3. Safety and status interfaces
4. Consumer mobile-product storytelling
5. Editorial product explanations

## Recording template — one block per locked reference

```markdown
### <reference name>
**Source:**
**What we borrow:**
**What we reject:**
**Specific screens:**
**Layout decisions:**
**Interaction decisions:**
```

---

## Known rejections (already decided, do not re-litigate)

| Rejected | Why |
|---|---|
| Generic "calm editorial" — cream, clay, decorative serif | Has itself become AI-slop |
| Indigo / violet defaults | Immediate AI-SaaS signal |
| Gratuitous gradients, glassmorphism | See DESIGN.md §2 |
| Generic landing-page section rhythm (hero → 3 cards → CTA) | Reads as template |
| Phone floating in a gradient cloud | The single most common AI-app hero cliché |
