# Agents for Humans: Building a Governed Strands Agent on Bedrock AgentCore

Natural language is valuable in ICO because people describe ordinary expectations in many
ways. It is also the wrong place to own safety state. Our design rule is simple: **AI
interprets humans; policy authorizes actions; deterministic software owns safety state.**

The compiler is a Strands agent running in Amazon Bedrock AgentCore Runtime. It invokes
Amazon Nova 2 Lite through Amazon Bedrock using temporary AWS execution-role credentials.
There is no model-provider API key in Lambda, the website or the Android package.

The runtime receives an operation, an utterance, a time zone and abstract Circle roles. It
returns a typed draft and warnings. It cannot access DynamoDB, EventBridge Scheduler, SQS,
SNS or stored contact endpoints. The API facade then repeats deterministic schema,
time-zone, role, consent and simulation checks before presenting the preview. Compilation
is side-effect free; activation is a separate explicit request.

For tools, AgentCore Gateway exposes a deliberately narrow vocabulary. A tool can propose
`PRIMARY`, `BACKUP` or `TERTIARY`; no parameter accepts a phone number, email or URL. An
AgentCore Policy Engine evaluates Cedar in ENFORCE mode with default deny and forbid-wins
rules. The target Lambda still verifies the authenticated tenant, active consent, pinned
plan version and Alert state. Policy is defense in depth, never the only check.

Observability follows the same privacy rule. Runtime records include the model ID, schema
version, hash of the input, latency and decision identifiers, but not the private utterance
or message body. CloudWatch alarms cover AgentCore failures and p99 compile latency while
X-Ray traces the surrounding Lambda path.

This separation makes model failure unsurprising. Malformed output is rejected. A timeout
returns a safe error. Prompt injection cannot broaden IAM permissions or invent a new tool
shape. The model remains useful because its authority is intentionally small.

_Before publication: insert one permitted and one denied live trace from the accepted demo,
with account IDs, tokens and contact endpoints redacted._
