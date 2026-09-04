# In Case of — Security Design

> **In Case of does not decide whether someone is in danger. It notices unresolved
> expectations and works to close the loop.**

(For vulnerability reporting, see `/SECURITY.md` at the repository root.)

---

## 1. Threat model

This product holds: who is alone and when, who their trusted contacts are, verified phone numbers,
and optionally a location snapshot. A breach is a stalking and physical-safety risk, not merely a
privacy one. Design accordingly.

**Principal threats**
1. Attacker obtains a responder link and impersonates a trusted contact.
2. Attacker induces the agent to contact an arbitrary number (prompt injection).
3. Attacker enumerates Alerts or Circle membership belonging to another user.
4. Attacker triggers context release (location) they are not entitled to.
5. Insider or log-based leakage of phone numbers.

---

## 2. Signed responder tokens

Responders must act **without installing the app**, so the link itself is the credential. It is
therefore scoped as tightly as possible.

Payload: `alert_id · responder_id · permissions · expires_at · nonce`

Rules:
- Signed; shortest practical lifetime; single-use nonce with replay protection.
- **Scoped to exactly one Alert.** Never a broad authenticated session.
- Grants only the permissions the current escalation step allows.
- Revoked immediately when the Alert reaches a terminal state.
- Never contains the subject's phone number or location.

A leaked token must expose one Alert for a short window — nothing more, and nothing about any
other Alert, Plan, or Circle member.

---

## 3. Data protection

| Data | Protection |
|---|---|
| Phone endpoints | KMS-encrypted at rest; never returned to clients in plaintext; never given to the model |
| Context snapshots | KMS-encrypted; released only per the pinned Plan Version's policy |
| Location | **Off by default.** Not required for P0 |
| Model credentials | Temporary AWS execution-role credentials; no model API key in the repo, clients or APK |
| Signing secrets | Secrets Manager, rotatable |
| Logs | PII-redacted. Phone numbers never logged, even at DEBUG |

Audit events are append-only by application convention and carry actor type, actor id, event type
and metadata.

---

## 4. IAM posture

The coding agent does **not** get admin credentials. Development identity is scoped to:

- The project sandbox account only, resource prefixes, limited regions.
- **No** IAM privilege escalation, **no** Organizations, **no** billing mutation.
- No production secret reading unless strictly necessary.
- Deployment through a separate, scoped deployment role.

This matters specifically because the AWS MCP Server can execute authenticated operations — its
blast radius is exactly the developer identity's permissions.

---

## 5. Consent

Nobody becomes a safety contact accidentally. Invitation states plainly:

> **Amir would like you in their Circle.** In Case of may contact you when one of Amir's plans is
> unresolved. You will never receive continuous location access.

Acceptance records timestamp, source, permissions, relevant Plan and policy version. Consent is
checked at **contact time**, not only at invitation time — withdrawn or expired consent blocks
contact even mid-Alert.

---

## 6. Application security essentials

TLS everywhere · KMS at rest · no secrets in the APK · secret rotation · least-privilege IAM ·
signed provider callbacks · replay protection · PII redaction · explicit data-deletion workflow ·
account deletion · retention policy.

---

## 7. Pre-commit and CI gates

Enforced mechanically, not by good intentions (`.claude/settings.json`, `.github/workflows/`):

- Secret scanning on every commit and PR.
- **No hardcoded phone numbers** — a repo-wide pattern check.
- No committed `.env`.
- Dependency vulnerability audit.
- Contract consistency between schemas and generated types.
