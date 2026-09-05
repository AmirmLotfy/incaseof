# ICO AgentCore Runtime

This artifact hosts only the side-effect-free natural-language plan compiler. It uses
Strands with `us.anthropic.claude-sonnet-4-6` through Amazon Bedrock and ambient IAM
credentials. It has no contact, scheduling or persistence tools.

Build the exact Linux ARM64 deployment artifact from the repository root:

```bash
scripts/build-agentcore-runtime.sh
```

The build emits `infra/cdk/assets/agentcore/` and performs an import/startup smoke test in
an ARM64 Linux Python 3.12 container when Docker is available.
