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

function synth(env: keyof typeof ENVIRONMENTS = "dev"): Template {
  const app = new App();
  const stack = new IcoStack(app, `IcoStack-${env}`, {
    environment: ENVIRONMENTS[env],
    env: { account: "123456789012", region: "us-east-1" },
  });
  return Template.fromStack(stack);
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
});

describe("api", () => {
  it("puts every subject-facing route behind the authorizer", () => {
    const routes = synth().findResources("AWS::ApiGatewayV2::Route");
    assert.ok(Object.keys(routes).length >= 9, "expected the v1 routes");
    for (const [name, route] of Object.entries(routes)) {
      const key = String(route.Properties?.RouteKey);
      if (key.includes("/r/")) continue; // responder routes, checked below
      assert.equal(
        route.Properties?.AuthorizationType,
        "JWT",
        `${name} (${key}) is not behind the authorizer`,
      );
    }
  });

  it("leaves exactly the responder routes unauthenticated, and no others", () => {
    // The signed single-Alert token is the credential, validated in the handler where
    // consent and membership can be re-checked too. This asserts the exception stays an
    // exception: a new route cannot join the unauthenticated set by accident.
    const routes = synth().findResources("AWS::ApiGatewayV2::Route");
    const open = Object.values(routes)
      .filter((route) => route.Properties?.AuthorizationType !== "JWT")
      .map((route) => String(route.Properties?.RouteKey))
      .sort();

    assert.deepEqual(open, [
      "GET /r/{signedToken}",
      "POST /v1/r/{signedToken}/claim",
      "POST /v1/r/{signedToken}/extend",
      "POST /v1/r/{signedToken}/resolve",
      "POST /v1/r/{signedToken}/unable",
    ]);
  });

  it("scopes every unauthenticated route to a single token", () => {
    // An unauthenticated route whose path carries no token would be open to everyone.
    const routes = synth().findResources("AWS::ApiGatewayV2::Route");
    for (const route of Object.values(routes)) {
      if (route.Properties?.AuthorizationType === "JWT") continue;
      assert.match(
        String(route.Properties?.RouteKey),
        /\{signedToken\}/,
        "an unauthenticated route takes no token",
      );
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

    for (const call of called) {
      assert.ok(deployed.has(call), `client calls ${call}, which is not deployed`);
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
