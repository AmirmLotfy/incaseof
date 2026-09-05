# Deployment and recovery

ICO does not decide whether someone is in danger. Deployment preserves the same product
boundary: deterministic software authorizes actions, and people make safety judgments.

The accepted path is GitHub Actions with OIDC and the protected `demo` environment. It builds
the exact Lambda, AgentCore, Android and static-web artifacts before deployment; no long-lived
AWS access key belongs in GitHub or this repository.

## Normal demo deployment

Use the `Deploy demo` workflow. A normal deployment targets Amazon Nova 2 Lite and configures
the AgentCore Runtime with a 60-second idle session timeout. It must not be run while the
account's applied `Versions per Agent` quota is zero because any Runtime property or artifact
change creates a new AgentCore version.

## Quota-blocked recovery rollout

The demo stack has one intentionally narrow recovery context:
`preserveDeployedAgentCoreRuntime=true`. It allows unrelated API, workflow or static-hosting
repairs while an external AgentCore version quota blocks Runtime updates.

Before using it:

1. Read the deployed CloudFormation template.
2. Copy the Runtime's current S3 artifact bucket template/key and model ID exactly. Preserve
   CloudFormation substitutions such as `${AWS::AccountId}` instead of resolving them locally.
3. Run `./scripts/build-lambda.sh`; the ignored staging directory is the deployable Lambda
   artifact, so synthesizing before this step can publish stale handler code.
4. Synthesize and run `cdk diff --no-change-set` with the preservation context.
5. Refuse the rollout if the diff changes `AWS::BedrockAgentCore::Runtime`.
6. Deploy only the `demo` environment and record the change-set ID and stack events.
7. Run `./scripts/configure-api-domain.sh`. The script updates the single existing
   empty-path mapping in place, fails if the mapping is ambiguous and verifies the public
   descriptor through `https://api.incaof.com/`.

The context is rejected for `dev` and `prod`, and it fails closed unless all three deployed
values are supplied. It is not part of the final accepted deployment. After AWS restores the
quota, omit every preservation value, deploy the checked-in Nova artifact, run the bounded
AgentCore canary, and record its invocation and trace IDs.

Never use `--hotswap` for acceptance. It bypasses CloudFormation and makes live state diverge
from the reproducible stack.
