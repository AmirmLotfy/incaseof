# In Case of — Domain Model

> **In Case of does not decide whether someone is in danger. It notices unresolved
> expectations and works to close the loop.**

The ERD below is the **logical** model. Section 3 defines the **physical** DynamoDB design. These
are deliberately different shapes — do not mechanically translate one into the other.

---

## 1. Entity relationship diagram

```mermaid
erDiagram
    PERSON {
        uuid person_id PK
        string display_name
        string locale
        string timezone
        datetime created_at
        datetime updated_at
    }
    ACCOUNT {
        uuid account_id PK
        uuid person_id FK
        string cognito_sub
        string status
        datetime created_at
    }
    DEVICE {
        uuid device_id PK
        uuid account_id FK
        string platform
        string app_version
        string os_version
        string push_token_ref
        datetime last_seen_at
    }
    CONTACT_ENDPOINT {
        uuid endpoint_id PK
        uuid person_id FK
        string type
        string encrypted_value
        datetime verified_at
        string status
    }
    CIRCLE {
        uuid circle_id PK
        uuid owner_person_id FK
        string name
        datetime created_at
    }
    CIRCLE_MEMBER {
        uuid membership_id PK
        uuid circle_id FK
        uuid person_id FK
        string role
        int priority
        string status
    }
    INVITATION {
        uuid invitation_id PK
        uuid circle_id FK
        uuid target_person_id FK
        string token_hash
        string status
        datetime expires_at
    }
    CONSENT_GRANT {
        uuid consent_id PK
        uuid subject_person_id FK
        uuid responder_person_id FK
        uuid plan_id FK
        json scopes
        string status
        datetime accepted_at
        datetime revoked_at
    }
    SAFETY_PLAN {
        uuid plan_id PK
        uuid subject_person_id FK
        uuid circle_id FK
        string type
        string status
        uuid active_version_id
        datetime created_at
    }
    PLAN_VERSION {
        uuid version_id PK
        uuid plan_id FK
        int version_number
        json trigger_spec
        json release_policy
        json stop_conditions
        datetime activated_at
    }
    ESCALATION_STEP {
        uuid step_id PK
        uuid version_id FK
        int sequence
        int offset_seconds
        string action_type
        string target_selector
        json constraints
    }
    PLAN_OVERRIDE {
        uuid override_id PK
        uuid plan_id FK
        string type
        datetime target_date
        json change
        string status
        datetime created_at
    }
    EXPECTED_MOMENT {
        uuid moment_id PK
        uuid version_id FK
        datetime due_at
        datetime grace_until
        string status
        datetime created_at
    }
    ALERT {
        uuid alert_id PK
        uuid moment_id FK
        uuid plan_version_id FK
        string state
        datetime opened_at
        datetime resolved_at
    }
    ALERT_OWNERSHIP {
        uuid ownership_id PK
        uuid alert_id FK
        uuid owner_person_id FK
        datetime claimed_at
        datetime expires_at
        string status
    }
    ACTION_ATTEMPT {
        uuid action_id PK
        uuid alert_id FK
        uuid step_id FK
        int attempt_number
        string channel
        string status
        string provider_reference
        string idempotency_key
        string error_code
        datetime created_at
    }
    ACKNOWLEDGEMENT {
        uuid acknowledgement_id PK
        uuid alert_id FK
        uuid person_id FK
        string type
        string source
        datetime created_at
    }
    RESOLUTION {
        uuid resolution_id PK
        uuid alert_id FK
        uuid resolved_by_person_id FK
        string method
        string reason_code
        datetime created_at
    }
    CONTEXT_SNAPSHOT {
        uuid snapshot_id PK
        uuid alert_id FK
        string type
        string encrypted_payload_ref
        datetime captured_at
        datetime released_at
    }
    AGENT_DECISION {
        uuid decision_id PK
        uuid alert_id FK
        string model_id
        string input_hash
        json structured_output
        string proposed_tool
        string policy_result
        datetime created_at
    }
    AUDIT_EVENT {
        uuid audit_id PK
        uuid alert_id FK
        string actor_type
        string actor_id
        string event_type
        json metadata
        datetime created_at
    }
    PERSON ||--o| ACCOUNT : owns
    ACCOUNT ||--o{ DEVICE : uses
    PERSON ||--o{ CONTACT_ENDPOINT : owns
    PERSON ||--o{ CIRCLE : creates
    CIRCLE ||--o{ CIRCLE_MEMBER : contains
    PERSON ||--o{ CIRCLE_MEMBER : participates
    CIRCLE ||--o{ INVITATION : sends
    PERSON ||--o{ SAFETY_PLAN : protects
    CIRCLE ||--o{ SAFETY_PLAN : supports
    SAFETY_PLAN ||--|{ PLAN_VERSION : versions
    PLAN_VERSION ||--|{ ESCALATION_STEP : defines
    SAFETY_PLAN ||--o{ PLAN_OVERRIDE : receives
    PLAN_VERSION ||--o{ EXPECTED_MOMENT : generates
    EXPECTED_MOMENT ||--o| ALERT : opens
    ALERT ||--o{ ALERT_OWNERSHIP : owns
    ALERT ||--o{ ACTION_ATTEMPT : performs
    ALERT ||--o{ ACKNOWLEDGEMENT : receives
    ALERT ||--o| RESOLUTION : closes
    ALERT ||--o{ CONTEXT_SNAPSHOT : contains
    ALERT ||--o{ AGENT_DECISION : records
    ALERT ||--o{ AUDIT_EVENT : logs
    SAFETY_PLAN ||--o{ CONSENT_GRANT : governed_by
```

---

## 2. Design notes

**`PLAN_VERSION` is immutable once activated.** An `EXPECTED_MOMENT` references a version, not a
plan, and an `ALERT` carries `plan_version_id` for its whole life. Editing a plan creates a new
version; live Alerts keep the old one. See `docs/ARCHITECTURE.md` §4.

**`PLAN_OVERRIDE` exists so a one-day exception never mutates a recurring plan.** "Skip tomorrow"
creates an override, not a new version of the schedule.

**`ACTION_ATTEMPT.idempotency_key`** is `alert_id + step_id + attempt_number` and is uniquely
constrained. This is what makes duplicate external actions structurally impossible.

**`AGENT_DECISION` records every model proposal**, including denied ones, with `policy_result`.
This table is what the developer trace view renders and what makes §4.6 (explainability) true.

**`CONSENT_GRANT` is checked at contact time**, not only at invitation time.

---

## 3. Physical design — DynamoDB single table

Access-pattern oriented. **Do not create 18 tables.**

```
PK PERSON#<id>       SK PROFILE
PK PERSON#<id>       SK DEVICE#<id>
PK PERSON#<id>       SK ENDPOINT#<id>
PK CIRCLE#<id>       SK META
PK CIRCLE#<id>       SK MEMBER#<id>
PK PLAN#<id>         SK META
PK PLAN#<id>         SK VERSION#0004
PK PLAN#<id>         SK VERSION#0004#STEP#001
PK PLAN#<id>         SK OVERRIDE#<date>
PK MOMENT#<id>       SK META
PK ALERT#<id>        SK META
PK ALERT#<id>        SK OWNERSHIP#<timestamp>
PK ALERT#<id>        SK ACTION#<timestamp>#<id>
PK ALERT#<id>        SK DECISION#<timestamp>#<id>
PK ALERT#<id>        SK AUDIT#<timestamp>#<id>
```

Zero-padded version and step numbers (`0004`, `001`) keep lexicographic order correct.

An Alert's entire timeline — ownership, actions, agent decisions, audit — lives under one partition
key, so rendering the Incident Room and the audit trail is a single query.

### Index rule

**Create a GSI only from a demonstrated query.** Abstract future scalability is not a reason.
Every GSI added must be justified in this file with the access pattern that required it.

Current GSIs: *none yet.* Expected first: due-Moment lookup by time window, and Alerts-by-responder
for the responder web surface — both added in Phase 1/2 when the query actually exists.

### Conditional writes

- Alert creation from a Moment: conditional on no existing Alert → enforces "one Moment, one Alert."
- Action dispatch: conditional on absent idempotency key → enforces zero duplicate external actions.
- Lease claim: conditional on current owner being absent or expired → prevents two responders both
  believing they own the Alert.
