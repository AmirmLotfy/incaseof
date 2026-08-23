import { Duration, RemovalPolicy } from "aws-cdk-lib";
import type * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import type * as kms from "aws-cdk-lib/aws-kms";
import * as lambda from "aws-cdk-lib/aws-lambda";
import { SqsEventSource } from "aws-cdk-lib/aws-lambda-event-sources";
import * as logs from "aws-cdk-lib/aws-logs";
import type * as sqs from "aws-cdk-lib/aws-sqs";
import { Construct } from "constructs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import type { IcoEnvironment } from "../environment.js";

const here = path.dirname(fileURLToPath(import.meta.url));
/** Staged by scripts/build-lambda.sh. */
const ASSET = path.join(here, "..", "..", "assets", "lambda");

export interface ComputeProps {
  readonly environment: IcoEnvironment;
  readonly table: dynamodb.ITable;
  readonly key: kms.IKey;
  readonly actionQueue: sqs.IQueue;
}

/**
 * The functions.
 *
 * Every one of these is written to be safe to invoke twice, because every one of them can
 * be: EventBridge Scheduler delivers at least once, SQS delivers at least once, and Step
 * Functions retries. Idempotency lives in the handlers and in DynamoDB conditional writes,
 * not in a hope that delivery is exactly once.
 */
export class Compute extends Construct {
  readonly momentDue: lambda.Function;
  readonly nextAction: lambda.Function;
  readonly dispatch: lambda.Function;
  readonly actionWorker: lambda.Function;

  constructor(scope: Construct, id: string, props: ComputeProps) {
    super(scope, id);

    const shared = {
      runtime: lambda.Runtime.PYTHON_3_12,
      code: lambda.Code.fromAsset(ASSET),
      architecture: lambda.Architecture.X86_64,
      environment: {
        ICO_TABLE_NAME: props.table.tableName,
        ICO_ENV: props.environment.name,
        ICO_TIME_SCALE: String(props.environment.demoTimeScale),
        ICO_ACTION_QUEUE_URL: props.actionQueue.queueUrl,
        // Python buffers stdout by default, which loses the last log lines of a function
        // that times out — exactly the invocation whose logs you need.
        PYTHONUNBUFFERED: "1",
      },
      tracing: lambda.Tracing.ACTIVE,
    };

    // Explicit log groups rather than `logRetention`, which is deprecated and provisions a
    // Lambda-backed custom resource per function purely to call PutRetentionPolicy.
    const logGroup = (name: string) =>
      new logs.LogGroup(this, `${name}Logs`, {
        retention: logs.RetentionDays.ONE_MONTH,
        removalPolicy: RemovalPolicy.DESTROY,
      });

    this.momentDue = new lambda.Function(this, "MomentDue", {
      ...shared,
      logGroup: logGroup("MomentDue"),
      handler: "services.handlers.moment_due.handler",
      description: "A Moment came due. Opens exactly one Alert and starts escalation.",
      timeout: Duration.seconds(30),
    });

    this.nextAction = new lambda.Function(this, "NextAction", {
      ...shared,
      logGroup: logGroup("NextAction"),
      handler: "services.handlers.escalation.next_action",
      description: "Decides what happens next for an Alert, and when.",
      timeout: Duration.seconds(30),
    });

    this.dispatch = new lambda.Function(this, "Dispatch", {
      ...shared,
      logGroup: logGroup("Dispatch"),
      handler: "services.handlers.escalation.dispatch",
      description: "Turns due rungs into queued, idempotency-guarded action intents.",
      timeout: Duration.seconds(30),
    });

    this.actionWorker = new lambda.Function(this, "ActionWorker", {
      ...shared,
      logGroup: logGroup("ActionWorker"),
      handler: "services.handlers.action_worker.handler",
      description: "Performs one external action. The only function that resolves an endpoint.",
      timeout: Duration.seconds(60),
      // A contact is not something to parallelise for throughput. Where the account
      // quota allows it, this caps how many can go out at once; see IcoEnvironment.
      reservedConcurrentExecutions: props.environment.reservedWorkerConcurrency,
    });

    this.actionWorker.addEventSource(
      new SqsEventSource(props.actionQueue, {
        batchSize: 5,
        // Report per-message failures so a poison message does not replay its whole batch.
        reportBatchItemFailures: true,
      }),
    );

    for (const fn of [this.momentDue, this.nextAction, this.dispatch, this.actionWorker]) {
      props.table.grantReadWriteData(fn);
      props.key.grantEncryptDecrypt(fn);
    }
    props.actionQueue.grantSendMessages(this.dispatch);
  }
}
