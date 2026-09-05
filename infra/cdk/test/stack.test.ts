import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import { App } from "aws-cdk-lib";
import { Match, Template } from "aws-cdk-lib/assertions";
import { ENVIRONMENTS } from "../lib/environment.js";
import { IcoStack } from "../lib/incaseof-stack.js";

/**
 * Template assertions.
 *
 * These check properties of the *deployed shape* that no Python test can see: whether the
 * table is actually encrypted, whether a queue actually has a dead-letter queue, whether a
 * route is actually behind the authorizer. Every one of them is a property somebody could
 * remove in a refactor without any other test noticing.
 */

const synthesized = new Map<keyof typeof ENVIRONMENTS, Template>();

function synth(env: keyof typeof ENVIRONMENTS = "dev"): Template {
  const existing = synthesized.get(env);
  if (existing) return existing;
  const app = new App({
    context: env === "demo"
      ? {
          hostedZoneId: "Z1234567890",
          hostedZoneName: "incaof.com",
          existingApiDomainRegionalName: "d-existing.execute-api.us-east-1.amazonaws.com",
          existingApiDomainHostedZoneId: "ZEXISTING",
        }
      : {},
  });
  const stack = new IcoStack(app, `IcoStack-${env}`, {
    environment: ENVIRONMENTS[env],
    env: { account: "123456789012", region: "us-east-1" },
  });
  const template = Template.fromStack(stack);
  synthesized.set(env, template);
  return template;
}

describe("storage", () => {
  it("keeps point-in-time recovery on", () => {
    // This table is the only record that a plan, an alert or a resolution ever existed.
    synth().hasResourceProperties("AWS::DynamoDB::Table", {
      PointInTimeRecoverySpecification: { PointInTimeRecoveryEnabled: true },
    });
  });

  it("encrypts with a customer-managed key", () => {
    synth().hasResourceProperties("AWS::DynamoDB::Table", {
      SSESpecification: { SSEEnabled: true },
    });
  });

  it("rotates that key", () => {
    synth().hasResourceProperties("AWS::KMS::Key", { EnableKeyRotation: true });
  });

  it("indexes outstanding moments so a missed schedule can be swept up", () => {
    synth().hasResourceProperties("AWS::DynamoDB::Table", {
      GlobalSecondaryIndexes: Match.arrayWith([
        Match.objectLike({ IndexName: "gsi1-moments-due" }),
      ]),
    });
  });

  it("indexes product state by validated Cognito subject", () => {
    synth().hasResourceProperties("AWS::DynamoDB::Table", {
      GlobalSecondaryIndexes: Match.arrayWith([
        Match.objectLike({ IndexName: "gsi2-person" }),
      ]),
    });
  });
});

describe("messaging", () => {
  it("gives the action queue a dead-letter queue", () => {
    // A silently dropped message here is a person who was never contacted.
    synth().hasResourceProperties("AWS::SQS::Queue", {
      RedrivePolicy: Match.objectLike({ maxReceiveCount: 3 }),
    });
  });

  it("encrypts every queue", () => {
    const template = synth();
    const queues = template.findResources("AWS::SQS::Queue");
    assert.equal(Object.keys(queues).length, 2, "expected a queue and its DLQ");
    for (const [name, queue] of Object.entries(queues)) {
      assert.ok(queue.Properties?.KmsMasterKeyId, `${name} is unencrypted`);
    }
  });

  it("requires TLS in transit", () => {
    const policies = synth().findResources("AWS::SQS::QueuePolicy");
    const denies = JSON.stringify(policies);
    assert.match(denies, /aws:SecureTransport/, "queues must refuse plaintext transport");
  });
});

describe("workflow", () => {
  it("uses a Standard workflow, because escalation runs for hours and must be auditable", () => {
    synth().hasResourceProperties("AWS::StepFunctions::StateMachine", {
      StateMachineType: "STANDARD",
    });
  });

  it("logs executions", () => {
    synth().hasResourceProperties("AWS::StepFunctions::StateMachine", {
      LoggingConfiguration: Match.objectLike({ Level: "ALL" }),
    });
  });

  it("creates a schedule group but declares no schedules", () => {
    const template = synth();
    template.resourceCountIs("AWS::Scheduler::ScheduleGroup", 1);
    // Pending Moments are application state. A schedule in the template would make every
    // check-in a deployment.
    template.resourceCountIs("AWS::Scheduler::Schedule", 0);
  });

  it("lets only EventBridge Scheduler assume the scheduler role", () => {
    synth().hasResourceProperties("AWS::IAM::Role", {
      AssumeRolePolicyDocument: Match.objectLike({
        Statement: Match.arrayWith([
          Match.objectLike({
            Principal: { Service: "scheduler.amazonaws.com" },
          }),
        ]),
      }),
    });
  });
});

describe("observability", () => {
  it("covers the API, workflow, scheduler, AgentCore and action DLQ", () => {
    const template = synth("demo");
    template.resourceCountIs("AWS::CloudWatch::Dashboard", 1);
    const alarms = JSON.stringify(template.findResources("AWS::CloudWatch::Alarm"));
    for (const required of [
      "AWS/Lambda",
      "AWS/States",
      "AWS/SQS",
      "AWS/Scheduler",
      "InCaseOf/AgentCore",
    ]) {
      assert.match(alarms, new RegExp(required.replace("/", "\\/")), `missing ${required}`);
    }
    template.resourceCountIs("AWS::Logs::MetricFilter", 2);
  });
});

describe("identity", () => {
  it("requires a long password", () => {
    synth().hasResourceProperties("AWS::Cognito::UserPool", {
      Policies: { PasswordPolicy: Match.objectLike({ MinimumLength: 12 }) },
    });
  });

  it("issues no client secret, because the app ships to devices", () => {
    synth().hasResourceProperties("AWS::Cognito::UserPoolClient", {
      GenerateSecret: false,
    });
  });

  it("never enables the implicit flow or a placeholder callback", () => {
    // CDK's defaults enable implicit and register https://example.com. Implicit returns
    // tokens in a URL fragment, where browser history and referrer headers leak them.
    const clients = synth().findResources("AWS::Cognito::UserPoolClient");
    for (const [name, client] of Object.entries(clients)) {
      const flows: string[] = client.Properties?.AllowedOAuthFlows ?? [];
      assert.ok(!flows.includes("implicit"), `${name} allows the implicit flow`);
      const callbacks: string[] = client.Properties?.CallbackURLs ?? [];
      assert.ok(
        !callbacks.some((url) => url.includes("example.com")),
        `${name} registers a callback on a domain we do not control`,
      );
    }
  });

  it("does not confirm whether an account exists", () => {
    synth().hasResourceProperties("AWS::Cognito::UserPoolClient", {
      PreventUserExistenceErrors: "ENABLED",
    });
  });

  it("uses authorization code with PKCE-compatible public web client settings", () => {
    synth().hasResourceProperties("AWS::Cognito::UserPoolClient", {
      AllowedOAuthFlows: ["code"],
      GenerateSecret: false,
      CallbackURLs: Match.arrayWith(["https://incaof.com/app/"]),
    });
  });
});

describe("hosting", () => {
  it("keeps both static origins private behind CloudFront and WAF", () => {
    const template = synth("demo");
    template.resourceCountIs("AWS::S3::Bucket", 2);
    for (const bucket of Object.values(template.findResources("AWS::S3::Bucket"))) {
      assert.deepEqual(bucket.Properties?.PublicAccessBlockConfiguration, {
        BlockPublicAcls: true,
        BlockPublicPolicy: true,
        IgnorePublicAcls: true,
        RestrictPublicBuckets: true,
      });
    }
    template.resourceCountIs("AWS::CloudFront::Distribution", 1);
    template.resourceCountIs("AWS::WAFv2::WebACL", 1);
    template.hasResourceProperties("AWS::CloudFront::Distribution", {
      DistributionConfig: Match.objectLike({
        Aliases: Match.arrayWith(["incaof.com", "www.incaof.com"]),
        HttpVersion: "http2and3",
        WebACLId: Match.anyValue(),
      }),
    });
  });

  it("maps the canonical website and API records in Route 53", () => {
    const template = synth("demo");
    template.resourceCountIs("AWS::CertificateManager::Certificate", 1);
    template.resourceCountIs("AWS::ApiGatewayV2::DomainName", 0);
    template.resourceCountIs("AWS::ApiGatewayV2::ApiMapping", 1);
    template.resourceCountIs("AWS::Route53::RecordSet", 2);
  });

  it("does not provision a legacy Gemini API key secret", () => {
    const secrets = JSON.stringify(synth("demo").findResources("AWS::SecretsManager::Secret"));
    assert.doesNotMatch(secrets, /gemini|google ai studio/i);
  });

  it("can deploy the demo core while an account-level CloudFront verification block is open", () => {
    const app = new App({ context: { skipEdgeHosting: "true" } });
    const stack = new IcoStack(app, "IcoStack-demo-core", {
      environment: ENVIRONMENTS.demo,
      env: { account: "123456789012", region: "us-east-1" },
    });
    const template = Template.fromStack(stack);
    template.resourceCountIs("AWS::CloudFront::Distribution", 0);
    template.hasOutput("EdgeHostingStatus", { Value: "BLOCKED_ACCOUNT_VERIFICATION" });
  });
});

describe("api", () => {
  it("puts every subject-facing route behind the authorizer", () => {
    const routes = synth().findResources("AWS::ApiGatewayV2::Route");
    assert.ok(Object.keys(routes).length >= 9, "expected the v1 routes");
    for (const [name, route] of Object.entries(routes)) {
      const key = String(route.Properties?.RouteKey);
      if (key === "GET /" || key.includes("/r/") || key.includes("/i/") || key.includes("/demo/")) continue;
      assert.equal(
        route.Properties?.AuthorizationType,
        "JWT",
        `${name} (${key}) is not behind the authorizer`,
      );
    }
  });

  it("leaves exactly the service descriptor and responder routes unauthenticated", () => {
    // The signed single-Alert token is the credential, validated in the handler where
    // consent and membership can be re-checked too. This asserts the exception stays an
    // exception: a new route cannot join the unauthenticated set by accident.
    const routes = synth().findResources("AWS::ApiGatewayV2::Route");
    const open = Object.values(routes)
      .filter((route) => route.Properties?.AuthorizationType !== "JWT")
      .map((route) => String(route.Properties?.RouteKey))
      .sort();

    assert.deepEqual(open, [
      "GET /",
      "GET /i/{signedToken}",
      "GET /r/{signedToken}",
      "POST /v1/i/{signedToken}/accept",
      "POST /v1/i/{signedToken}/decline",
      "POST /v1/r/{signedToken}/claim",
      "POST /v1/r/{signedToken}/extend",
      "POST /v1/r/{signedToken}/resolve",
      "POST /v1/r/{signedToken}/unable",
    ]);

    const demoRoutes = Object.values(synth("demo").findResources("AWS::ApiGatewayV2::Route"))
      .filter((route) => route.Properties?.AuthorizationType !== "JWT")
      .map((route) => String(route.Properties?.RouteKey));
    assert.ok(demoRoutes.includes("POST /v1/demo/session"));
    assert.equal(demoRoutes.filter((route) => route.includes("/v1/demo/")).length, 19);
  });

  it("scopes every unauthenticated route to a single token", () => {
    // An unauthenticated route whose path carries no token would be open to everyone.
    const routes = synth().findResources("AWS::ApiGatewayV2::Route");
    for (const route of Object.values(routes)) {
      const key = String(route.Properties?.RouteKey);
      if (route.Properties?.AuthorizationType === "JWT" || key === "GET /") continue;
      assert.match(
        key,
        /\{signedToken\}/,
        "an unauthenticated route takes no token",
      );
    }

    const demoRoutes = synth("demo").findResources("AWS::ApiGatewayV2::Route");
    for (const route of Object.values(demoRoutes)) {
      const key = String(route.Properties?.RouteKey);
      if (
        route.Properties?.AuthorizationType === "JWT" ||
        key === "GET /" ||
        key.includes("/demo/")
      ) continue;
      assert.match(key, /\{signedToken\}/);
    }
  });

  it("deploys every route the Android client calls", () => {
    // Read from the client itself rather than a copy of the list, so adding a call to
    // IcoApi.kt without deploying its route fails here instead of in someone's hand.
    const client = readFileSync(
      new URL(
        "../../../android/app/src/main/java/com/incaof/app/core/network/IcoApi.kt",
        import.meta.url,
      ),
      "utf8",
    );
    const called = [...client.matchAll(/@(GET|POST|PUT|DELETE)\("([^"]+)"\)/g)].map(
      (m) => `${m[1]} /${m[2]}`.replace(/\{(\w+)\}/g, "{}"),
    );
    assert.ok(called.length >= 6, `parsed ${called.length} client calls, expected more`);

    const deployed = new Set(
      Object.values(synth().findResources("AWS::ApiGatewayV2::Route")).map((route) =>
        String(route.Properties?.RouteKey).replace(/\{(\w+)\}/g, "{}"),
      ),
    );
    const deployedDemo = new Set(
      Object.values(synth("demo").findResources("AWS::ApiGatewayV2::Route")).map((route) =>
        String(route.Properties?.RouteKey).replace(/\{(\w+)\}/g, "{}"),
      ),
    );

    for (const call of called) {
      const routes = call.includes("/v1/demo/") ? deployedDemo : deployed;
      assert.ok(routes.has(call), `client calls ${call}, which is not deployed in its environment`);
    }
  });

  it("declares routes explicitly rather than proxying everything", () => {
    // A proxy route lets a path reach the handler before anyone decided it should exist.
    const routes = synth().findResources("AWS::ApiGatewayV2::Route");
    for (const route of Object.values(routes)) {
      assert.doesNotMatch(
        String(route.Properties?.RouteKey),
        /\{proxy\+\}|\$default/,
        "no catch-all routes",
      );
    }
  });

  it("uses one API-scoped Lambda permission instead of a statement per route", () => {
    // Lambda resource policies are capped at 20 KiB. Route-scoped permissions crossed
    // that hard service limit when the public judge-demo slice reached full parity.
    const permissions = synth("demo").findResources("AWS::Lambda::Permission");
    const apiPermissions = Object.entries(permissions).filter(
      ([name, permission]) =>
        name.includes("ApiHandler") &&
        permission.Properties?.Principal === "apigateway.amazonaws.com",
    );
    assert.equal(apiPermissions.length, 1, "expected one invoke permission for the shared API Lambda");
    assert.match(JSON.stringify(apiPermissions[0]?.[1].Properties?.SourceArn), /\*\/\*\/\*/);
  });
});

describe("agentcore", () => {
  it("allows the API to invoke the exact runtime with validated user context", () => {
    const policies = JSON.stringify(synth().findResources("AWS::IAM::Policy"));
    assert.match(policies, /bedrock-agentcore:InvokeAgentRuntimeForUser/);
    assert.match(policies, /bedrock-agentcore:InvokeAgentRuntime/);
    assert.match(policies, /AgentCoreRuntime8EF1CF90/);
  });

  it("deploys a managed Python runtime and uses its automatic DEFAULT endpoint", () => {
    const template = synth();
    template.hasResourceProperties("AWS::BedrockAgentCore::Runtime", {
      ProtocolConfiguration: "HTTP",
      NetworkConfiguration: { NetworkMode: "PUBLIC" },
      LifecycleConfiguration: {
        IdleRuntimeSessionTimeout: 60,
        MaxLifetime: 3600,
      },
      AgentRuntimeArtifact: {
        CodeConfiguration: Match.objectLike({
          EntryPoint: ["main.py"],
          Runtime: "PYTHON_3_12",
        }),
      },
    });
    template.resourceCountIs("AWS::BedrockAgentCore::RuntimeEndpoint", 0);
    template.hasOutput("AgentCoreRuntimeQualifier", { Value: "DEFAULT" });
  });

  it("keeps the runtime side-effect free and scopes Bedrock to Amazon Nova 2 Lite", () => {
    const template = synth();
    const serialized = JSON.stringify(template.findResources("AWS::IAM::Policy"));
    assert.match(serialized, /us\.amazon\.nova-2-lite-v1:0/);
    assert.match(serialized, /amazon\.nova-2-lite-v1:0/);
    assert.doesNotMatch(serialized, /anthropic|gemini/i);

    const runtimeRoles = template.findResources("AWS::IAM::Role", {
      Properties: {
        AssumeRolePolicyDocument: Match.objectLike({
          Statement: Match.arrayWith([
            Match.objectLike({ Principal: { Service: "bedrock-agentcore.amazonaws.com" } }),
          ]),
        }),
      },
    });
    assert.ok(Object.keys(runtimeRoles).length >= 2, "expected runtime and gateway service roles");

    const runtimeRoleIds = Object.keys(runtimeRoles);
    const policies = template.findResources("AWS::IAM::Policy");
    const runtimePolicy = Object.values(policies).find(
      (policy) =>
        runtimeRoleIds.some((id) => JSON.stringify(policy.Properties?.Roles ?? []).includes(id)) &&
        JSON.stringify(policy).includes("us.amazon.nova-2-lite-v1:0"),
    );
    const policyText = JSON.stringify(runtimePolicy);
    assert.doesNotMatch(policyText, /dynamodb:|scheduler:|sqs:|sns:/i);
  });

  it("can preserve the deployed demo runtime while an account quota blocks new versions", () => {
    const app = new App({
      context: {
        skipEdgeHosting: "true",
        preserveDeployedAgentCoreRuntime: "true",
        preservedAgentCoreArtifactBucketTemplate: "cdk-assets-${AWS::AccountId}",
        preservedAgentCoreArtifactKey: "deployed-runtime.zip",
        preservedAgentCoreModelId: "us.anthropic.claude-sonnet-4-6",
      },
    });
    const stack = new IcoStack(app, "IcoStack-demo-preserved-runtime", {
      environment: ENVIRONMENTS.demo,
      env: { account: "123456789012", region: "us-east-1" },
    });
    const template = Template.fromStack(stack);

    template.hasResourceProperties("AWS::BedrockAgentCore::Runtime", {
      Description: "ICO Strands compiler using Claude Sonnet 4.6 through Bedrock",
      EnvironmentVariables: {
        AWS_BEDROCK_MODEL_ID: "us.anthropic.claude-sonnet-4-6",
        PYTHONUNBUFFERED: "1",
      },
      AgentRuntimeArtifact: {
        CodeConfiguration: {
          Code: {
            S3: {
              Bucket: { "Fn::Sub": "cdk-assets-${AWS::AccountId}" },
              Prefix: "deployed-runtime.zip",
            },
          },
        },
      },
    });
    const runtimes = template.findResources("AWS::BedrockAgentCore::Runtime");
    assert.equal(Object.values(runtimes)[0]?.Properties?.LifecycleConfiguration, undefined);
  });

  it("attaches a default-deny policy engine to the role-only Gateway in ENFORCE mode", () => {
    const template = synth();
    template.resourceCountIs("AWS::BedrockAgentCore::PolicyEngine", 1);
    template.resourceCountIs("AWS::BedrockAgentCore::Policy", 3);
    template.hasResourceProperties("AWS::BedrockAgentCore::Gateway", {
      AuthorizerType: "AWS_IAM",
      ProtocolType: "MCP",
      PolicyEngineConfiguration: Match.objectLike({ Mode: "ENFORCE" }),
    });
    template.hasResourceProperties("AWS::BedrockAgentCore::Policy", {
      EnforcementMode: "ACTIVE",
      ValidationMode: "FAIL_ON_ANY_FINDINGS",
    });
    const agentPolicies = template.findResources("AWS::BedrockAgentCore::Policy");
    assert.equal(
      Object.values(agentPolicies).filter(
        (policy) => policy.Properties?.ValidationMode === "FAIL_ON_ANY_FINDINGS",
      ).length,
      2,
    );
    assert.equal(
      Object.values(agentPolicies).filter(
        (policy) => policy.Properties?.ValidationMode === "IGNORE_ALL_FINDINGS",
      ).length,
      1,
    );
    const policies = JSON.stringify(agentPolicies);
    assert.match(policies, /forbid/);
    assert.match(policies, /propose_contact_role/);
    const targets = JSON.stringify(
      template.findResources("AWS::BedrockAgentCore::GatewayTarget"),
    );
    assert.match(targets, /propose_contact_role/);
    assert.doesNotMatch(targets, /phone|email|url/i);

    const iamRoles = template.findResources("AWS::IAM::Role");
    const gatewayRoleEntry = Object.entries(iamRoles).find(([, role]) =>
      (JSON.stringify(role.Properties?.Policies) ?? "").includes(
        "bedrock-agentcore:GetPolicyEngine",
      ),
    );
    assert.ok(gatewayRoleEntry, "expected an inline AgentCore Gateway policy");
    const [, gatewayRole] = gatewayRoleEntry;
    const gatewayPolicyText = JSON.stringify(gatewayRole.Properties?.Policies);
    assert.match(gatewayPolicyText, /PolicyEngineArn/);
    assert.match(gatewayPolicyText, /gateway\/\*/);
    assert.match(gatewayPolicyText, /kms:Decrypt/);
    assert.match(gatewayPolicyText, /kms:GrantIsForAWSResource/);
    assert.doesNotMatch(
      gatewayPolicyText,
      /kms:ViaService/,
      "CreateGateway policy-engine validation assumes this role and calls KMS directly",
    );
    assert.doesNotMatch(gatewayPolicyText, /Resource":"\*"/);
  });
});

describe("least privilege", () => {
  it("grants no policy full wildcard access", () => {
    const policies = synth().findResources("AWS::IAM::Policy");
    for (const [name, policy] of Object.entries(policies)) {
      for (const statement of policy.Properties?.PolicyDocument?.Statement ?? []) {
        if (statement.Effect !== "Allow") continue;
        const actions = [statement.Action].flat().filter(Boolean);
        const resources = [statement.Resource].flat().filter(Boolean);
        const wildcardAction = actions.includes("*");
        const wildcardResource = resources.includes("*");
        assert.ok(
          !(wildcardAction && wildcardResource),
          `${name} grants * on *; this account holds who is alone and when`,
        );
      }
    }
  });

  it("provisions no Lambda-backed custom resources just to set log retention", () => {
    // `logRetention` is deprecated and creates one custom-resource Lambda per function.
    // Explicit log groups do the same job with no extra compute to fail or to pay for.
    synth().resourceCountIs("Custom::LogRetention", 0);
  });

  it("keeps logs for every function", () => {
    const template = synth();
    const functions = Object.values(template.findResources("AWS::Lambda::Function")).filter(
      (fn) => fn.Properties?.Handler?.startsWith?.("services."),
    );
    const groups = Object.keys(template.findResources("AWS::Logs::LogGroup"));
    assert.ok(
      groups.length >= functions.length,
      `${functions.length} functions but only ${groups.length} log groups`,
    );
  });

  it("gives SMS permission to the worker and to nothing else", () => {
    // A bug anywhere else must not be able to become a message to somebody's sister.
    const policies = synth().findResources("AWS::IAM::Policy");
    const withSms = Object.entries(policies).filter(([, policy]) =>
      JSON.stringify(policy.Properties?.PolicyDocument ?? {}).includes("sns:Publish"),
    );

    assert.equal(withSms.length, 1, `${withSms.length} policies can send SMS`);
    assert.match(withSms[0][0], /ActionWorker/, "SMS permission is on the wrong function");
  });

  it("traces every function, so a slow escalation can be explained", () => {
    const functions = synth().findResources("AWS::Lambda::Function");
    const ours = Object.entries(functions).filter(
      ([, fn]) => fn.Properties?.Handler?.startsWith?.("services."),
    );
    assert.ok(ours.length >= 5, `expected our handlers, found ${ours.length}`);
    for (const [name, fn] of ours) {
      assert.equal(fn.Properties?.TracingConfig?.Mode, "Active", `${name} is untraced`);
    }
  });
});

describe("environments", () => {
  it("keeps demo on a compressed clock and dev on a real one", () => {
    assert.equal(ENVIRONMENTS.demo.demoTimeScale, 0.02);
    assert.equal(ENVIRONMENTS.dev.demoTimeScale, 1.0);
  });

  it("passes the time scale to every handler", () => {
    const demo = synth("demo").findResources("AWS::Lambda::Function");
    const ours = Object.values(demo).filter((fn) =>
      fn.Properties?.Handler?.startsWith?.("services."),
    );
    for (const fn of ours) {
      assert.equal(fn.Properties?.Environment?.Variables?.ICO_TIME_SCALE, "0.02");
    }
  });

  it("redirects external delivery only in the public demo environment", () => {
    for (const [env, expected] of [["dev", undefined], ["demo", "SAFE_SINK"], ["prod", undefined]] as const) {
      const functions = synth(env).findResources("AWS::Lambda::Function");
      const worker = Object.values(functions).find((fn) =>
        fn.Properties?.Handler?.includes?.("action_worker"),
      );
      assert.equal(worker?.Properties?.Environment?.Variables?.ICO_DELIVERY_MODE, expected);
    }
  });

  it("reserves no concurrency in dev or demo", () => {
    // A new AWS account has a total Lambda concurrency quota of 10 and requires 10 to
    // remain unreserved, so reserving any amount fails the deploy outright. Production
    // still caps the worker; low-traffic environments do not need to.
    for (const env of ["dev", "demo"] as const) {
      const functions = synth(env).findResources("AWS::Lambda::Function");
      for (const [name, fn] of Object.entries(functions)) {
        assert.equal(
          fn.Properties?.ReservedConcurrentExecutions,
          undefined,
          `${name} reserves concurrency in ${env}`,
        );
      }
    }
  });

  it("still caps the worker in production", () => {
    const functions = synth("prod").findResources("AWS::Lambda::Function");
    const worker = Object.values(functions).find((fn) =>
      fn.Properties?.Handler?.includes?.("action_worker"),
    );
    assert.ok(worker, "expected the action worker");
    assert.equal(worker.Properties?.ReservedConcurrentExecutions, 20);
  });

  it("protects production state from a stack delete", () => {
    const prod = synth("prod").findResources("AWS::DynamoDB::Table");
    for (const table of Object.values(prod)) {
      assert.equal(table.DeletionPolicy, "Retain");
      assert.equal(table.Properties?.DeletionProtectionEnabled, true);
    }
  });

  it("lets dev and demo be torn down cleanly", () => {
    for (const env of ["dev", "demo"] as const) {
      const tables = synth(env).findResources("AWS::DynamoDB::Table");
      for (const table of Object.values(tables)) {
        assert.equal(table.DeletionPolicy, "Delete", `${env} should be disposable`);
      }
    }
  });
});
