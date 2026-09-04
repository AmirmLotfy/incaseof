import { CfnOutput, Stack, type StackProps, Tags } from "aws-cdk-lib";
import type { Construct } from "constructs";
import { Api } from "./constructs/api.js";
import { AgentCore } from "./constructs/agentcore.js";
import { Compute } from "./constructs/compute.js";
import { Identity } from "./constructs/identity.js";
import { Hosting } from "./constructs/hosting.js";
import { Messaging } from "./constructs/messaging.js";
import { Observability } from "./constructs/observability.js";
import { Secrets } from "./constructs/secrets.js";
import { Storage } from "./constructs/storage.js";
import { Workflow } from "./constructs/workflow.js";
import { assertBannerInvariant, type IcoEnvironment } from "./environment.js";

export interface IcoStackProps extends StackProps {
  readonly environment: IcoEnvironment;
}

/**
 * In Case of — application stack.
 *
 * One instance per environment, so demo data never mixes with real data. Everything is
 * defined here: the submission claims the environment can be reconstructed from the
 * repository, and a single console-created resource would make that claim false.
 */
export class IcoStack extends Stack {
  constructor(scope: Construct, id: string, props: IcoStackProps) {
    super(scope, id, props);

    assertBannerInvariant(props.environment);

    const storage = new Storage(this, "Storage", { environment: props.environment });
    const secrets = new Secrets(this, "Secrets", {
      environment: props.environment,
      key: storage.key,
    });
    const identity = new Identity(this, "Identity", { environment: props.environment });
    const agentCore = new AgentCore(this, "AgentCore", {
      environment: props.environment,
      key: storage.key,
    });
    const messaging = new Messaging(this, "Messaging", { key: storage.key });
    const pushPlatformArn = this.node.tryGetContext("pushPlatformArn") as string | undefined;

    const compute = new Compute(this, "Compute", {
      environment: props.environment,
      table: storage.table,
      key: storage.key,
      actionQueue: messaging.actionQueue,
      pushPlatformArn,
    });

    const workflow = new Workflow(this, "Workflow", {
      environment: props.environment,
      nextAction: compute.nextAction,
      dispatch: compute.dispatch,
      momentDue: compute.momentDue,
    });

    // The handler that opens an Alert is also the one that starts escalation, so it needs
    // both the state machine's ARN and permission to start it. Granted after the workflow
    // exists to avoid a cycle between the two constructs.
    compute.momentDue.addEnvironment("ICO_STATE_MACHINE_ARN", workflow.stateMachine.stateMachineArn);
    workflow.stateMachine.grantStartExecution(compute.momentDue);


    const api = new Api(this, "Api", {
      environment: props.environment,
      responderKeySecretArn: secrets.responderTokenSigningKey.secretArn,
      userPool: identity.userPool,
      userPoolClient: identity.client,
      webUserPoolClient: identity.webClient,
      table: storage.table,
      key: storage.key,
      pushPlatformArn,
      agentCoreRuntimeArn: agentCore.runtime.attrAgentRuntimeArn,
    });

    const skipEdgeHosting = this.node.tryGetContext("skipEdgeHosting") === "true";
    if ((props.environment.name === "demo" || props.environment.name === "prod") && !skipEdgeHosting) {
      new Hosting(this, "Hosting", {
        environment: props.environment,
        httpApi: api.httpApi,
        hostedZoneId: this.node.tryGetContext("hostedZoneId") as string | undefined,
        hostedZoneName: this.node.tryGetContext("hostedZoneName") as string | undefined,
        existingApiDomainRegionalName: this.node.tryGetContext(
          "existingApiDomainRegionalName",
        ) as string | undefined,
        existingApiDomainHostedZoneId: this.node.tryGetContext(
          "existingApiDomainHostedZoneId",
        ) as string | undefined,
      });
    }

    new CfnOutput(this, "EdgeHostingStatus", {
      value: skipEdgeHosting ? "BLOCKED_ACCOUNT_VERIFICATION" : "MANAGED_BY_STACK",
      description: "CloudFront is omitted only for a documented account-level verification block.",
    });

    // Creating a Moment's timer needs three things: the group to put it in, the function
    // it should wake, and the role Scheduler assumes to do the waking. Wiring only the
    // group — as this previously did — leaves the scheduler adapter returning null, so no
    // timers are created at all and nothing looks wrong until a check silently never fires.
    const scheduleGroup = workflow.scheduleGroup.name ?? "";

    new Observability(this, "Observability", {
      environment: props.environment,
      api: api.handler,
      functions: [
        api.handler,
        compute.momentDue,
        compute.nextAction,
        compute.dispatch,
        compute.actionWorker,
        agentCore.toolTarget,
      ],
      stateMachine: workflow.stateMachine,
      actionDlq: messaging.actionDlq,
      scheduleGroupName: scheduleGroup,
      agentCoreLogs: agentCore.runtimeLogs,
    });

    // The API handler schedules the first Moment when a plan is activated, and moves it
    // when somebody asks for more time.
    api.handler.addEnvironment("ICO_SCHEDULE_GROUP", scheduleGroup);
    api.handler.addEnvironment("ICO_MOMENT_DUE_ARN", compute.momentDue.functionArn);
    api.handler.addEnvironment("ICO_SCHEDULER_ROLE_ARN", workflow.schedulerRole.roleArn);
    workflow.grantManageSchedules(api.handler);

    // MomentDue queues the *next* occurrence of a recurring plan once one fires, so it
    // also creates schedules that target itself. It is deliberately not given its own ARN
    // here: a function referencing its own ARN is a CloudFormation dependency cycle and
    // the template will not deploy. It reads it from the Lambda invocation context instead.
    compute.momentDue.addEnvironment("ICO_SCHEDULE_GROUP", scheduleGroup);
    compute.momentDue.addEnvironment("ICO_SCHEDULER_ROLE_ARN", workflow.schedulerRole.roleArn);
    workflow.grantManageSchedules(compute.momentDue);

    secrets.responderTokenSigningKey.grantRead(api.handler);

    Tags.of(this).add("Project", "in-case-of");
    Tags.of(this).add("Environment", props.environment.name);
    Tags.of(this).add("ManagedBy", "cdk");

    new CfnOutput(this, "ApiUrl", { value: api.httpApi.apiEndpoint });
    new CfnOutput(this, "AgentCoreRuntimeArn", { value: agentCore.runtime.attrAgentRuntimeArn });
    new CfnOutput(this, "AgentCoreRuntimeQualifier", {
      value: "DEFAULT",
      description: "CreateAgentRuntime supplies DEFAULT; no redundant custom endpoint is created.",
    });
    new CfnOutput(this, "AgentCoreGatewayUrl", { value: agentCore.gateway.attrGatewayUrl });
    new CfnOutput(this, "AgentCorePolicyEngineArn", {
      value: agentCore.policyEngine.attrPolicyEngineArn,
    });
    new CfnOutput(this, "TableName", { value: storage.table.tableName });
    new CfnOutput(this, "UserPoolId", { value: identity.userPool.userPoolId });
    new CfnOutput(this, "UserPoolClientId", { value: identity.client.userPoolClientId });
    new CfnOutput(this, "WebUserPoolClientId", { value: identity.webClient.userPoolClientId });
    new CfnOutput(this, "CognitoManagedLoginUrl", {
      value: `https://${identity.domain.domainName}.auth.${this.region}.amazoncognito.com`,
    });
    new CfnOutput(this, "StateMachineArn", { value: workflow.stateMachine.stateMachineArn });
    new CfnOutput(this, "ScheduleGroup", { value: workflow.scheduleGroup.name ?? "" });
    new CfnOutput(this, "SchedulerRoleArn", { value: workflow.schedulerRole.roleArn });
    new CfnOutput(this, "DemoTimeScale", {
      value: String(props.environment.demoTimeScale),
      description: "1.0 is real time. Anything else must display the demo banner.",
    });
  }
}
