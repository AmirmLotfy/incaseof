# Contributing

## Setup

Requires `uv`, Node 22+, JDK 17, the Android SDK (platform 37), and the AWS CLI for deploys.

```bash
uv sync && npm install && git config core.hooksPath .githooks
```

## Agent tooling

The AWS skills and MCP server install from the AWS CLI — no `/plugin` needed:

```bash
aws configure agent-toolkit --yes
```

That installs 19 skills into `~/.claude/skills` (CDK, serverless, Cognito, Bedrock and
AgentCore, observability, boto3) and registers the AWS MCP server. It needs a default
region set first: `aws configure set region us-east-1`.

Design research uses the Refero skill, installed standalone:

```bash
npx skills add referodesign/refero_skill --skill refero-design
```

Its bundled craft references work offline. Live style and screen research additionally
needs the Refero MCP in `.mcp.json`, which prompts for a browser sign-in on first use.

## Before you push

```bash
./scripts/preflight.sh
```

This runs everything CI runs. It reports **all** failures rather than stopping at the first.

## The rules that matter most

Read [`CLAUDE.md`](CLAUDE.md) — it applies to humans too.

1. **The agent never receives a contact endpoint.** It names a role; the backend resolves the
   encrypted endpoint after authorization. Never add a tool parameter that accepts a phone number,
   email, or URL.
2. **Safety timers live in AWS**, never on a device.
3. **Acknowledged is not resolved.**
4. **Every Alert is pinned to an immutable Plan Version.**
5. **Never disable a failing test** to make CI green.
6. **Never commit a real phone number.** Use a reserved fictional range: `+1 202 555 01XX` or
   `+44 7700 900XXX`. The pre-commit hook enforces this.
7. **Design tokens are generated.** Edit `packages/design-tokens/tokens.json`, run `npm run tokens`,
   commit the generated files.
8. **Research before designing.** No significant new surface without locked references in
   `docs/design/REFERENCES.md`.

## Documentation is the contract

If code and `docs/` disagree, the documents win. Change a document deliberately, in its own commit,
and say why — do not let the code quietly redefine the product.

Every document in `docs/` opens with the product boundary statement. CI enforces this, because the
boundary is the thing that keeps the product honest:

> In Case of does not decide whether someone is in danger. It notices unresolved expectations and
> works to close the loop.
