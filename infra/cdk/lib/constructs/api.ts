import { Duration, RemovalPolicy } from "aws-cdk-lib";
import * as apigw from "aws-cdk-lib/aws-apigatewayv2";
import { HttpJwtAuthorizer } from "aws-cdk-lib/aws-apigatewayv2-authorizers";
import { HttpLambdaIntegration } from "aws-cdk-lib/aws-apigatewayv2-integrations";
import type * as cognito from "aws-cdk-lib/aws-cognito";
import type * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as iam from "aws-cdk-lib/aws-iam";
import type * as kms from "aws-cdk-lib/aws-kms";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as logs from "aws-cdk-lib/aws-logs";
import { Construct } from "constructs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import type { IcoEnvironment } from "../environment.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const ASSET = path.join(here, "..", "..", "assets", "lambda");

export interface ApiProps {
  readonly environment: IcoEnvironment;
  /** ARN of the responder-token signing secret. Read at cold start, cached per container. */
  readonly responderKeySecretArn: string;
  readonly userPool: cognito.IUserPool;
  readonly userPoolClient: cognito.IUserPoolClient;
  readonly webUserPoolClient: cognito.IUserPoolClient;
  readonly table: dynamodb.ITable;
  readonly key: kms.IKey;
  readonly pushPlatformArn?: string;
  readonly agentCoreRuntimeArn: string;
}

/**
 * The public surface.
 *
 * An HTTP API rather than REST: cheaper, faster, and this product needs none of what the
 * REST API adds. Not GraphQL either — the access patterns are few and fixed, and a query
 * language would mostly add ways to ask for things the policy layer must then refuse.
 *
 * Every /v1 route is behind the Cognito authorizer. Responder routes are deliberately
 * *not*, because a responder has no account; they carry a signed single-Alert token
 * instead, validated in the handler. Putting them behind the same authorizer would force
 * a friend to sign up before they could say "I've got her".
 */
export class Api extends Construct {
  readonly httpApi: apigw.HttpApi;
  readonly handler: lambda.Function;

  constructor(scope: Construct, id: string, props: ApiProps) {
    super(scope, id);

    this.handler = new lambda.Function(this, "Handler", {
      runtime: lambda.Runtime.PYTHON_3_12,
      code: lambda.Code.fromAsset(ASSET),
      handler: "services.handlers.api.handler",
      architecture: lambda.Architecture.X86_64,
      timeout: Duration.seconds(15),
      environment: {
        ICO_TABLE_NAME: props.table.tableName,
        ICO_ENV: props.environment.name,
        ICO_TIME_SCALE: String(props.environment.demoTimeScale),
        ICO_RESPONDER_KEY_SECRET_ARN: props.responderKeySecretArn,
        ICO_KMS_KEY_ID: props.key.keyId,
        ICO_AGENTCORE_RUNTIME_ARN: props.agentCoreRuntimeArn,
        ICO_AGENTCORE_QUALIFIER: "live",
        ICO_ALLOWED_COUNTRIES: "EG,US",
        ICO_ADMISSIONS_OPEN: String(props.environment.admissionsOpen),
        ICO_MAX_ACTIVE_PLANS_PER_ACCOUNT: String(props.environment.maxActivePlansPerAccount),
        ...(props.pushPlatformArn ? { ICO_PUSH_PLATFORM_ARN: props.pushPlatformArn } : {}),
        PYTHONUNBUFFERED: "1",
      },
      logGroup: new logs.LogGroup(this, "HandlerLogs", {
        retention: logs.RetentionDays.ONE_MONTH,
        removalPolicy: RemovalPolicy.DESTROY,
      }),
      tracing: lambda.Tracing.ACTIVE,
    });
    props.table.grantReadWriteData(this.handler);
    props.key.grantEncryptDecrypt(this.handler);
    this.handler.addToRolePolicy(
      new iam.PolicyStatement({
        // runtimeUserId carries the already-validated Cognito/demo subject into the
        // AgentCore request. AWS requires the ForUser action in addition to invocation.
        actions: [
          "bedrock-agentcore:InvokeAgentRuntime",
          "bedrock-agentcore:InvokeAgentRuntimeForUser",
        ],
        resources: [props.agentCoreRuntimeArn, `${props.agentCoreRuntimeArn}/runtime-endpoint/*`],
      }),
    );

    if (props.pushPlatformArn) {
      this.handler.addToRolePolicy(
        new iam.PolicyStatement({
          actions: ["sns:CreatePlatformEndpoint"],
          resources: [props.pushPlatformArn],
        }),
      );
      this.handler.addToRolePolicy(
        new iam.PolicyStatement({
          actions: ["sns:DeleteEndpoint"],
          resources: [props.pushPlatformArn.replace(":app/", ":endpoint/") + "/*"],
        }),
      );
    }

    const authorizer = new HttpJwtAuthorizer(
      "CognitoAuthorizer",
      `https://cognito-idp.${process.env.CDK_DEFAULT_REGION ?? "us-east-1"}.amazonaws.com/${props.userPool.userPoolId}`,
      {
        jwtAudience: [
          props.userPoolClient.userPoolClientId,
          props.webUserPoolClient.userPoolClientId,
        ],
      },
    );

    this.httpApi = new apigw.HttpApi(this, "HttpApi", {
      description: "In Case of — someone notices.",
      defaultAuthorizer: authorizer,
      corsPreflight: {
        // The responder web app is the only browser origin that calls this.
        allowMethods: [
          apigw.CorsHttpMethod.GET,
        apigw.CorsHttpMethod.POST,
          apigw.CorsHttpMethod.PATCH,
          apigw.CorsHttpMethod.DELETE,
        ],
        allowHeaders: [
          "authorization",
          "content-type",
          "idempotency-key",
          "x-ico-source",
        ],
        allowOrigins:
          props.environment.name === "prod" || props.environment.name === "demo"
            ? ["https://incaof.com", "https://www.incaof.com"]
            : ["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"],
        maxAge: Duration.hours(1),
      },
    });

    // All explicit routes share one API-scoped invoke permission. CDK's route-scoped
    // default emits one Lambda policy statement per route; the demo surface is large
    // enough to exceed Lambda's 20 KiB resource-policy limit. The API ID remains the
    // trust boundary, while the route list below remains explicit and test-enforced.
    const integration = new HttpLambdaIntegration("ApiIntegration", this.handler, {
      scopePermissionToRoute: false,
    });

    // A stable public descriptor lets hosting and judges verify that the canonical API
    // is reachable without creating an account or touching tenant state.
    const service: Array<[string, apigw.HttpMethod]> = [["/", apigw.HttpMethod.GET]];
    for (const [routePath, method] of service) {
      this.httpApi.addRoutes({
        path: routePath,
        methods: [method],
        integration,
        authorizer: new apigw.HttpNoneAuthorizer(),
      });
    }

    // Routes are declared explicitly rather than as a proxy. A proxy route would let a
    // path reach the handler before anyone decided it should exist, and this is the
    // surface where "what can be asked for" is a security property.
    // Every route the Android client calls must appear here. A client calling a path
    // that was never deployed fails at the worst possible moment — when somebody is trying
    // to say they are okay — so test/stack.test.ts asserts this list covers IcoApi.kt.
    const authenticated: Array<[string, apigw.HttpMethod]> = [
      ["/v1/profile", apigw.HttpMethod.GET],
      ["/v1/profile", apigw.HttpMethod.PATCH],
      ["/v1/readiness", apigw.HttpMethod.GET],
      ["/v1/plans/compile", apigw.HttpMethod.POST],
      ["/v1/plans", apigw.HttpMethod.POST],
      ["/v1/moments/next", apigw.HttpMethod.GET],
      ["/v1/moments/{momentId}", apigw.HttpMethod.GET],
      ["/v1/moments/{momentId}/confirm", apigw.HttpMethod.POST],
      ["/v1/moments/{momentId}/extend", apigw.HttpMethod.POST],
      ["/v1/moments/{momentId}/cancel", apigw.HttpMethod.POST],
      ["/v1/plans", apigw.HttpMethod.GET],
      ["/v1/history", apigw.HttpMethod.GET],
      ["/v1/plans/{planId}", apigw.HttpMethod.GET],
      ["/v1/plans/{planId}/activate", apigw.HttpMethod.POST],
      ["/v1/plans/{planId}/pause", apigw.HttpMethod.POST],
      ["/v1/plans/{planId}/resume", apigw.HttpMethod.POST],
      ["/v1/plans/{planId}/test", apigw.HttpMethod.POST],
      ["/v1/circle", apigw.HttpMethod.GET],
      ["/v1/circle/invitations", apigw.HttpMethod.POST],
      ["/v1/circle/invitations/{invitationId}/resend", apigw.HttpMethod.POST],
      ["/v1/circle/members/{memberId}", apigw.HttpMethod.DELETE],
      ["/v1/devices", apigw.HttpMethod.POST],
      ["/v1/devices/{deviceId}", apigw.HttpMethod.DELETE],
      ["/v1/alerts/{alertId}", apigw.HttpMethod.GET],
      ["/v1/alerts/{alertId}/claim", apigw.HttpMethod.POST],
      ["/v1/alerts/{alertId}/release", apigw.HttpMethod.POST],
      ["/v1/alerts/{alertId}/resolve", apigw.HttpMethod.POST],
      ["/v1/alerts/{alertId}/timeline", apigw.HttpMethod.GET],
    ];

    for (const [routePath, method] of authenticated) {
      this.httpApi.addRoutes({ path: routePath, methods: [method], integration });
    }

    // Responder routes carry NO Cognito authorizer, deliberately.
    //
    // A responder has no account. They are somebody's sister, at 2am, holding a link that
    // arrived by SMS — and requiring her to sign up before she can say "I've got her"
    // would defeat the product. The signed single-Alert token *is* the credential, and it
    // is validated in the handler, where the check can also re-test consent, membership
    // and whether the Alert is still open. An authorizer could only verify a signature.
    //
    // test/stack.test.ts asserts this list is the complete set of unauthenticated routes,
    // so a future route cannot join it by accident.
    const responder: Array<[string, apigw.HttpMethod]> = [
      ["/r/{signedToken}", apigw.HttpMethod.GET],
      ["/v1/r/{signedToken}/claim", apigw.HttpMethod.POST],
      ["/v1/r/{signedToken}/extend", apigw.HttpMethod.POST],
      ["/v1/r/{signedToken}/unable", apigw.HttpMethod.POST],
      ["/v1/r/{signedToken}/resolve", apigw.HttpMethod.POST],
      ["/i/{signedToken}", apigw.HttpMethod.GET],
      ["/v1/i/{signedToken}/accept", apigw.HttpMethod.POST],
      ["/v1/i/{signedToken}/decline", apigw.HttpMethod.POST],
    ];

    for (const [routePath, method] of responder) {
      this.httpApi.addRoutes({
        path: routePath,
        methods: [method],
        integration,
        authorizer: new apigw.HttpNoneAuthorizer(),
      });
    }

    // A public demo realm exists only in the demo stack. The handler issues a short-lived,
    // signed synthetic-tenant credential and rejects these routes in every other
    // environment. API throttling caps abuse; there are no real contact endpoints behind
    // this realm.
    if (props.environment.name === "demo") {
      const demo: Array<[string, apigw.HttpMethod]> = [
        ["/v1/demo/session", apigw.HttpMethod.POST],
        ["/v1/demo/plans/compile", apigw.HttpMethod.POST],
        ["/v1/demo/plans", apigw.HttpMethod.POST],
        ["/v1/demo/plans", apigw.HttpMethod.GET],
        ["/v1/demo/plans/{planId}", apigw.HttpMethod.GET],
        ["/v1/demo/plans/{planId}/activate", apigw.HttpMethod.POST],
        ["/v1/demo/plans/{planId}/pause", apigw.HttpMethod.POST],
        ["/v1/demo/plans/{planId}/resume", apigw.HttpMethod.POST],
        ["/v1/demo/plans/{planId}/test", apigw.HttpMethod.POST],
        ["/v1/demo/moments/next", apigw.HttpMethod.GET],
        ["/v1/demo/moments/{momentId}/confirm", apigw.HttpMethod.POST],
        ["/v1/demo/moments/{momentId}/extend", apigw.HttpMethod.POST],
        ["/v1/demo/circle", apigw.HttpMethod.GET],
        ["/v1/demo/circle/invitations", apigw.HttpMethod.POST],
        ["/v1/demo/history", apigw.HttpMethod.GET],
        ["/v1/demo/alerts/{alertId}", apigw.HttpMethod.GET],
        ["/v1/demo/alerts/{alertId}/claim", apigw.HttpMethod.POST],
        ["/v1/demo/alerts/{alertId}/timeline", apigw.HttpMethod.GET],
        ["/v1/demo/alerts/{alertId}/responder-link", apigw.HttpMethod.GET],
      ];
      for (const [routePath, method] of demo) {
        this.httpApi.addRoutes({
          path: routePath,
          methods: [method],
          integration,
          authorizer: new apigw.HttpNoneAuthorizer(),
        });
      }
      const stage = this.httpApi.defaultStage?.node.defaultChild as apigw.CfnStage | undefined;
      if (stage) {
        stage.defaultRouteSettings = {
          throttlingBurstLimit: 20,
          throttlingRateLimit: 10,
        };
      }
    }
  }
}
