import { Arn, RemovalPolicy, Stack } from "aws-cdk-lib";
import * as agentcore from "aws-cdk-lib/aws-bedrockagentcore";
import * as iam from "aws-cdk-lib/aws-iam";
import type * as kms from "aws-cdk-lib/aws-kms";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as logs from "aws-cdk-lib/aws-logs";
import * as s3assets from "aws-cdk-lib/aws-s3-assets";
import { Construct } from "constructs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import type { IcoEnvironment } from "../environment.js";

const here = path.dirname(fileURLToPath(import.meta.url));
/** Staged and ABI-checked by scripts/build-agentcore-runtime.sh. */
const RUNTIME_ASSET = path.join(here, "..", "..", "assets", "agentcore");
const LAMBDA_ASSET = path.join(here, "..", "..", "assets", "lambda");

export interface AgentCoreProps {
  readonly environment: IcoEnvironment;
  readonly key: kms.IKey;
}

/**
 * The side-effect-free natural-language compiler on AgentCore Runtime.
 *
 * IAM is the inbound authorizer when no custom JWT authorizer is configured. The runtime
 * role can invoke only the locked cross-region inference profile and its exact foundation
 * model family. It has no DynamoDB, Scheduler, SQS, SNS or contact permissions.
 */
export class AgentCore extends Construct {
  readonly runtime: agentcore.CfnRuntime;
  readonly gateway: agentcore.CfnGateway;
  readonly policyEngine: agentcore.CfnPolicyEngine;
  readonly toolTarget: lambda.Function;
  readonly runtimeRole: iam.Role;
  readonly runtimeLogs: logs.LogGroup;

  constructor(scope: Construct, id: string, props: AgentCoreProps) {
    super(scope, id);

    const stack = Stack.of(this);
    const modelResources = [
      Arn.format(
        {
          service: "bedrock",
          resource: "inference-profile",
          resourceName: "us.amazon.nova-2-lite-v1:0",
        },
        stack,
      ),
      `arn:${stack.partition}:bedrock:*::foundation-model/amazon.nova-2-lite-v1:0`,
    ];

    this.runtimeRole = new iam.Role(this, "RuntimeRole", {
      assumedBy: new iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
      description: "ICO AgentCore compiler; Bedrock inference only, no product state access",
    });
    this.runtimeRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
        resources: modelResources,
      }),
    );
    this.runtimeRole.addToPolicy(
      new iam.PolicyStatement({
        actions: [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "cloudwatch:PutMetricData",
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords",
        ],
        resources: ["*"],
      }),
    );

    const artifact = new s3assets.Asset(this, "RuntimeArtifact", { path: RUNTIME_ASSET });
    artifact.grantRead(this.runtimeRole);

    this.runtime = new agentcore.CfnRuntime(this, "Runtime", {
      agentRuntimeName: `ico_${props.environment.name}_compiler`,
      description: "ICO Strands compiler using Amazon Nova 2 Lite through Bedrock",
      roleArn: this.runtimeRole.roleArn,
      protocolConfiguration: "HTTP",
      networkConfiguration: { networkMode: "PUBLIC" },
      agentRuntimeArtifact: {
        codeConfiguration: {
          code: {
            s3: {
              bucket: artifact.s3BucketName,
              prefix: artifact.s3ObjectKey,
            },
          },
          entryPoint: ["main.py"],
          runtime: "PYTHON_3_12",
        },
      },
      environmentVariables: {
        AWS_BEDROCK_MODEL_ID: "us.amazon.nova-2-lite-v1:0",
        PYTHONUNBUFFERED: "1",
      },
      lifecycleConfiguration: {
        idleRuntimeSessionTimeout: 60,
        maxLifetime: 3600,
      },
      tags: {
        Project: "in-case-of",
        Environment: props.environment.name,
        ManagedBy: "cdk",
      },
    });

    this.runtimeLogs = new logs.LogGroup(this, "RuntimeLogs", {
      logGroupName: `/aws/bedrock-agentcore/runtimes/${this.runtime.attrAgentRuntimeId}-DEFAULT`,
      retention: logs.RetentionDays.ONE_MONTH,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    // Gateway tools are proposals only. This Lambda has no product-state grants and no
    // channel client, so even an allowed tool cannot contact anyone by itself.
    this.toolTarget = new lambda.Function(this, "ToolTarget", {
      runtime: lambda.Runtime.PYTHON_3_12,
      architecture: lambda.Architecture.X86_64,
      code: lambda.Code.fromAsset(LAMBDA_ASSET),
      handler: "services.handlers.agent_tool_target.handler",
      description: "ICO AgentCore role-only, no-side-effect tool target",
      tracing: lambda.Tracing.ACTIVE,
      environment: {
        ICO_ENV: props.environment.name,
        ICO_TIME_SCALE: String(props.environment.demoTimeScale),
        PYTHONUNBUFFERED: "1",
      },
      logGroup: new logs.LogGroup(this, "ToolTargetLogs", {
        retention: logs.RetentionDays.ONE_MONTH,
        removalPolicy: RemovalPolicy.DESTROY,
      }),
    });

    this.policyEngine = new agentcore.CfnPolicyEngine(this, "PolicyEngine", {
      name: `ico_${props.environment.name}_policy`,
      description: "Default-deny authorization for ICO AgentCore Gateway tools",
      encryptionKeyArn: props.key.keyArn,
      tags: [
        { key: "Project", value: "in-case-of" },
        { key: "Environment", value: props.environment.name },
      ],
    });

    const gatewayRole = new iam.Role(this, "GatewayRole", {
      assumedBy: new iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
      description: "Invokes only the ICO tool target and evaluates its policy engine",
      // These are inline deliberately: CreateGateway calls GetPolicyEngine immediately,
      // and a detached AWS::IAM::Policy can be reported complete before IAM propagation.
      inlinePolicies: {
        GatewayExecution: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              actions: ["lambda:InvokeFunction"],
              resources: [this.toolTarget.functionArn],
            }),
            new iam.PolicyStatement({
              actions: ["bedrock-agentcore:GetPolicyEngine"],
              resources: [this.policyEngine.attrPolicyEngineArn],
            }),
            new iam.PolicyStatement({
              actions: [
                "bedrock-agentcore:AuthorizeAction",
                "bedrock-agentcore:PartiallyAuthorizeActions",
              ],
              resources: [
                this.policyEngine.attrPolicyEngineArn,
                `arn:${stack.partition}:bedrock-agentcore:${stack.region}:${stack.account}:gateway/*`,
              ],
            }),
            // CreateGateway validates the attached policy engine as a short-lived assumed-role
            // session. CloudTrail shows that validation calls KMS without kms:ViaService, so a
            // ViaService condition makes the exact permission ineffective. The single CMK ARN
            // remains the permission boundary; this role cannot use any other account key.
            new iam.PolicyStatement({
              actions: ["kms:Decrypt", "kms:DescribeKey", "kms:GenerateDataKey"],
              resources: [props.key.keyArn],
            }),
            new iam.PolicyStatement({
              actions: ["kms:CreateGrant"],
              resources: [props.key.keyArn],
              conditions: { Bool: { "kms:GrantIsForAWSResource": "true" } },
            }),
          ],
        }),
      },
    });

    this.gateway = new agentcore.CfnGateway(this, "Gateway", {
      name: `ico-${props.environment.name}-gateway`,
      description: "ICO's abstract role-only agent tool boundary",
      authorizerType: "AWS_IAM",
      protocolType: "MCP",
      protocolConfiguration: {
        mcp: {
          instructions: "Tools propose abstract roles only. They never accept contact endpoints.",
          supportedVersions: ["2025-06-18"],
        },
      },
      roleArn: gatewayRole.roleArn,
      kmsKeyArn: props.key.keyArn,
      policyEngineConfiguration: {
        arn: this.policyEngine.attrPolicyEngineArn,
        mode: "ENFORCE",
      },
      tags: {
        Project: "in-case-of",
        Environment: props.environment.name,
        ManagedBy: "cdk",
      },
    });
    this.gateway.addResourceDependency(this.policyEngine);

    const targetName = "IcoSafetyTools";
    this.toolTarget.addPermission("GatewayInvoke", {
      principal: new iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
      sourceArn: this.gateway.attrGatewayArn,
    });
    const roleInput = {
      type: "object",
      description: "An abstract Circle role. Names and endpoints are not accepted.",
      properties: {
        role: {
          type: "string",
          description: "Exactly PRIMARY, BACKUP or TERTIARY",
        },
      },
      required: ["role"],
    };
    const target = new agentcore.CfnGatewayTarget(this, "ToolGatewayTarget", {
      gatewayIdentifier: this.gateway.attrGatewayIdentifier,
      name: targetName,
      description: "Role-only proposals and the public ICO safety contract",
      credentialProviderConfigurations: [{ credentialProviderType: "GATEWAY_IAM_ROLE" }],
      targetConfiguration: {
        mcp: {
          lambda: {
            lambdaArn: this.toolTarget.functionArn,
            toolSchema: {
              inlinePayload: [
                {
                  name: "propose_contact_role",
                  description: "Propose a Circle role for later deterministic authorization",
                  inputSchema: roleInput,
                  outputSchema: { type: "object" },
                },
                {
                  name: "read_safety_contract",
                  description: "Read ICO's non-negotiable safety contract",
                  inputSchema: { type: "object" },
                  outputSchema: { type: "object" },
                },
              ],
            },
          },
        },
      },
    });
    target.addResourceDependency(this.gateway);

    // An IAM caller must still be the ICO runtime role. Valid role values receive an
    // explicit permit; all other actions default-deny, and the matching forbid wins.
    const validRole =
      'context.input.role == "PRIMARY" || context.input.role == "BACKUP" || ' +
      'context.input.role == "TERTIARY"';
    const caller = `principal.id like "arn:aws:sts::*:assumed-role/${this.runtimeRole.roleName}"`;
    const gateway = `resource == AgentCore::Gateway::"${this.gateway.attrGatewayArn}"`;
    // AgentCore validates one Cedar statement per Policy resource. Keeping these separate
    // also makes the forbid independently auditable and preserves Cedar's forbid-wins rule.
    const policyStatements = [
      {
        id: "ReadSafetyContractPolicy",
        name: `IcoReadSafety_${props.environment.name}`,
        description: "Permit the ICO runtime to read the non-negotiable safety contract",
        validationMode: "FAIL_ON_ANY_FINDINGS",
        statement: `permit(principal is AgentCore::IamEntity, action == AgentCore::Action::"${targetName}___read_safety_contract", ${gateway}) when { ${caller} };`,
      },
      {
        id: "ProposeContactRolePolicy",
        name: `IcoProposeRole_${props.environment.name}`,
        description: "Permit the ICO runtime to propose only a valid abstract Circle role",
        validationMode: "FAIL_ON_ANY_FINDINGS",
        statement: `permit(principal is AgentCore::IamEntity, action == AgentCore::Action::"${targetName}___propose_contact_role", ${gateway}) when { ${caller} && (${validRole}) };`,
      },
      {
        id: "InvalidContactRoleForbidPolicy",
        name: `IcoForbidInvalidRole_${props.environment.name}`,
        description: "Forbid invalid Circle roles even if a broader permit is added later",
        // The analyzer reports this intentional total deny for invalid inputs as
        // OVERLY_RESTRICTIVE. IGNORE_ALL_FINDINGS still runs Cedar schema checks; only this
        // expected semantic finding is accepted. The two permits remain strict-validated.
        validationMode: "IGNORE_ALL_FINDINGS",
        statement: `forbid(principal is AgentCore::IamEntity, action == AgentCore::Action::"${targetName}___propose_contact_role", ${gateway}) when { ${caller} && !(${validRole}) };`,
      },
    ] as const;

    for (const definition of policyStatements) {
      const policy = new agentcore.CfnPolicy(this, definition.id, {
        name: definition.name,
        description: definition.description,
        policyEngineId: this.policyEngine.attrPolicyEngineId,
        enforcementMode: "ACTIVE",
        validationMode: definition.validationMode,
        definition: { cedar: { statement: definition.statement } },
      });
      policy.addResourceDependency(target);
    }

    this.runtimeRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["bedrock-agentcore:InvokeGateway"],
        resources: [this.gateway.attrGatewayArn],
      }),
    );
  }
}
