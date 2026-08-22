---
description: AWS architecture and CDK
globs: ["infra/**", "services/**"]
---

# AWS rules

## Use the AWS Agent Toolkit
When AWS architecture, services, permissions, deployment, SDKs or current service capabilities are
involved, use the `aws-core` / `aws-agents` skills and the AWS MCP Server rather than reasoning
from training data. Service behaviour changes faster than any model's cutoff.

## Ownership of time
**EventBridge Scheduler owns every safety timer.** Not the phone, not WorkManager, not a Lambda
sleeping, not a Step Functions Wait inside an already-killed execution.

## Step Functions
Standard workflows (not Express) for escalation: they run for hours, need durable history, and
need human-callback patterns. Every step must be safe to retry.

## Infrastructure
- Everything in CDK. **Nothing created by hand in the console** — the submission claims the
  environment can be reconstructed from the repository, and a console-made resource makes that
  claim false.
- One stack instance per environment. Demo data never mixes with real data.
- Create a GSI only from a demonstrated query, and record the access pattern in `docs/ERD.md`.

## IAM
Least privilege, project-prefixed, sandbox account only. No privilege escalation, no Organizations,
no billing mutation. Deployment uses a separate scoped role. This matters more than usual because
the AWS MCP Server can execute authenticated operations with the developer identity's permissions.

## Secrets
Secrets Manager only. Never in the repo, never in the APK, never in a log, never in a CDK context
value.
