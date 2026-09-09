# Agents for Humans: Building a Governed Strands Agent on Bedrock AgentCore

People describe ordinary expectations in many ways. One person says, “Check on me tonight.”
Another says, “If I do not answer after my appointment, contact my sister.” Natural language is
the right interface for that intent, but it is the wrong place to own safety state.

Our design rule for **In Case Of (ICO)** is:

> AI interprets humans. Policy authorizes actions. Deterministic software owns safety state.

That rule became a concrete AWS architecture rather than a prompt instruction.

## Give the agent a narrow job

The compiler is built with the **Strands Agents SDK** and targets **Amazon Bedrock AgentCore
Runtime**, using **Amazon Nova 2 Lite** through Amazon Bedrock. AWS execution-role credentials
replace model-provider API keys in the website, Lambda functions, and Android package.

The compiler receives four useful inputs:

1. The requested operation.
2. The person’s utterance.
3. Their time zone.
4. Abstract Circle roles.

It returns a typed candidate Plan and warnings. It does not save the Plan or start it. Compilation
is side-effect free, and activation is a separate authenticated request after review.

## Remove dangerous vocabulary

The most important safety property is what the agent cannot express. AgentCore Gateway exposes a
small role-based vocabulary. A tool may propose `PRIMARY`, `BACKUP`, or `TERTIARY`; no tool
parameter accepts a phone number, email address, or URL.

The runtime also has no permission to read or write DynamoDB, create EventBridge schedules, enqueue
SQS messages, invoke SNS, or resolve encrypted contact endpoints. Even if the model produces an
unexpected draft, it cannot turn that text directly into an external action.

The API facade performs deterministic checks after compilation:

- JSON Schema and enum validation
- time-zone and bounded-recurrence validation
- role and Circle-membership validation
- consent and channel-readiness checks
- simulation of the proposed escalation ladder

The user then sees the validated preview. Only a separate activation request can create the
versioned Plan and its first scheduled Moment.

## Put policy between interpretation and execution

An AgentCore Policy Engine evaluates Cedar policies in `ENFORCE` mode. The rules use default deny
and forbid-wins behavior. Policy evaluates abstract intent, but it is not the only guard.

The target Lambda repeats the authoritative checks at action time: authenticated tenant, active
consent, pinned Plan Version, current Alert state, allowed channel, and unexpired checking lease.
Authorization is checked close to the effect because permissions and state can change after a
message is queued.

This creates three independent boundaries:

1. The model can only return a typed proposal.
2. Cedar can deny the proposed abstract action.
3. Deterministic domain code verifies current state immediately before execution.

## Preserve privacy in observability

Debugging an agent should not require storing the private sentence that created a Plan. ICO records
the model identifier, schema version, input hash, latency, and decision identifiers. It redacts
contact endpoints, signed responder tokens, and message bodies.

CloudWatch covers runtime errors and compilation latency, while X-Ray traces the surrounding Lambda
path. The public developer trace uses the same redaction rules.

## Design the fallback as evidence

The deployment journey exposed the value of this separation. The AgentCore Runtime, Gateway, and
Policy Engine were provisioned, but AWS account verification and version quota blocked publishing
and invoking the corrected runtime during final submission work.

We did not hide that limitation or fabricate a successful model trace. The public demo labels the
condition and returns a disclosed, schema-validated deterministic template. The template must pass
the same server-side validation before it can be saved. The resulting Moment still runs through
the deployed Scheduler, Step Functions, DynamoDB, SQS, worker, responder authorization, and audit
path.

That fallback demonstrates the boundary we wanted from the beginning: model availability can
affect convenience, but it cannot take ownership of timers, authorization, or escalation state.

Malformed output is rejected. A timeout does not activate anything. Prompt injection cannot
broaden IAM permissions or invent a new tool shape. The deterministic workflow continues to behave
consistently because the agent’s authority is intentionally small.

## What we would carry into production

Before a public launch, we would restore live model access, rerun the English and Arabic evaluation
suites against the deployed runtime, and capture permitted and denied traces. We would keep the
same structural boundaries: no contact endpoint in model context, no model-owned timer, no
model-owned state transition, and no activation without human review.

An agent earns trust by doing useful work within a small, inspectable grant of authority. In ICO,
governance is part of the product, not a paragraph added after the agent is built.

## Explore the implementation

- [Run the synthetic live judge demo](https://incaof.com/demo/)
- [Read the architecture and source](https://github.com/AmirmLotfy/incaseof)
- [View the submitted project on Devpost](https://devpost.com/software/in-case-of-ygk5uj)

Built for the **Agents for Humans Hackathon**, Everyday Agents track.
