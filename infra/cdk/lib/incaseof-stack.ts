import { CfnOutput, Stack, type StackProps, Tags } from "aws-cdk-lib";
import type { Construct } from "constructs";
import { Api } from "./constructs/api.js";
import { Compute } from "./constructs/compute.js";
import { Identity } from "./constructs/identity.js";
import { Messaging } from "./constructs/messaging.js";
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
    const messaging = new Messaging(this, "Messaging", { key: storage.key });

    const compute = new Compute(this, "Compute", {
      environment: props.environment,
      table: storage.table,
      key: storage.key,
      actionQueue: messaging.actionQueue,
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

    // Only the function that opens Alerts may create and cancel Moment schedules, and only
    // within this environment's group.
    compute.momentDue.addEnvironment("ICO_SCHEDULE_GROUP", workflow.scheduleGroup.name ?? "");

    const api = new Api(this, "Api", {
      environment: props.environment,
      responderKeySecretArn: secrets.responderTokenSigningKey.secretArn,
      userPool: identity.userPool,
      userPoolClient: identity.client,
      table: storage.table,
      key: storage.key,
    });

    secrets.responderTokenSigningKey.grantRead(api.handler);
    secrets.geminiApiKey.grantRead(api.handler);

    Tags.of(this).add("Project", "in-case-of");
    Tags.of(this).add("Environment", props.environment.name);
    Tags.of(this).add("ManagedBy", "cdk");

    new CfnOutput(this, "ApiUrl", { value: api.httpApi.apiEndpoint });
    new CfnOutput(this, "TableName", { value: storage.table.tableName });
    new CfnOutput(this, "UserPoolId", { value: identity.userPool.userPoolId });
    new CfnOutput(this, "UserPoolClientId", { value: identity.client.userPoolClientId });
    new CfnOutput(this, "StateMachineArn", { value: workflow.stateMachine.stateMachineArn });
    new CfnOutput(this, "ScheduleGroup", { value: workflow.scheduleGroup.name ?? "" });
    new CfnOutput(this, "SchedulerRoleArn", { value: workflow.schedulerRole.roleArn });
    new CfnOutput(this, "DemoTimeScale", {
      value: String(props.environment.demoTimeScale),
      description: "1.0 is real time. Anything else must display the demo banner.",
    });
  }
}
